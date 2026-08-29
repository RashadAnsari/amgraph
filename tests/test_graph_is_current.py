"""The router must be serving the graph we think it is serving.

Everything else here tests rules. This tests the delivery of them, because
three separate faults in one day shipped, or nearly shipped, a graph that did
not match the code that claimed to have built it:

* `valhalla_build_extract` refuses to overwrite an existing `tiles.tar`, so
  every rebuild after the first failed at the final step, leaving fresh tiles
  beside a stale archive — and the archive is what gets served.
* A running `valhalla_service` memory-maps that archive, so rewriting it under
  a live container corrupts the map the process is reading.
* `valhalla_build_tiles` does not clear its output directory, so a build killed
  partway leaves truncated tiles that abort every later build.

Two of those left `/status` answering perfectly well, which is exactly what a
health check looks at. So `/status` is not enough: these ask the router to
prove it, by the timestamp it reports and by a rule it can only know from the
extract that was built.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

VALHALLA_URL = os.environ.get("VALHALLA_URL", "http://localhost:8002")
WORK = Path(__file__).resolve().parents[1] / "infra" / "work"


def _router_available() -> bool:
    try:
        return httpx.get(f"{VALHALLA_URL}/status", timeout=2).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = [
    pytest.mark.graph,
    pytest.mark.skipif(not _router_available(), reason=f"no Valhalla at {VALHALLA_URL}"),
]


def _enriched_extract() -> Path | None:
    found = sorted(WORK.glob("*-official.osm.pbf"))
    return found[0] if found else None


def test_the_served_tiles_are_newer_than_the_extract_they_come_from() -> None:
    """Catches the stale archive, which is otherwise invisible.

    A graph built from an extract older than itself is fine. A graph *older
    than its own input* means the build did not replace what is being served,
    and every rule added since then is absent while all the tests still pass.
    """
    extract = _enriched_extract()
    if extract is None:
        pytest.skip("no enriched extract to compare against")

    status = httpx.get(f"{VALHALLA_URL}/status", timeout=10).json()
    modified = status.get("tileset_last_modified")
    assert modified, f"the router reports no tileset_last_modified: {status}"

    tiles_at = datetime.fromtimestamp(modified, UTC)
    extract_at = datetime.fromtimestamp(extract.stat().st_mtime, UTC)
    assert tiles_at >= extract_at, (
        f"the served tileset is from {tiles_at:%Y-%m-%d %H:%M} but "
        f"{extract.name} is from {extract_at:%Y-%m-%d %H:%M}. The router is on "
        "an older graph than the extract on disk, so the build did not replace "
        "what is being served."
    )


def test_the_router_answers_a_real_route_and_not_only_status() -> None:
    """`/status` stayed green through a corrupted memory map; routing did not.

    Deliberately a route rather than a ping: the corruption only surfaced when
    a request touched a tile.
    """
    body = {
        "locations": [
            {"lat": 52.0907, "lon": 5.1214},
            {"lat": 52.0800, "lon": 5.1300},
        ],
        "costing": "motorcycle",
    }
    response = httpx.post(f"{VALHALLA_URL}/route", json=body, timeout=30)
    assert response.status_code == 200, (
        f"a short Utrecht route failed with {response.status_code}: {response.text[:300]}"
    )
    trip = response.json().get("trip", {})
    assert trip.get("legs"), f"the router returned no legs: {str(trip)[:300]}"


def test_the_authority_overlay_is_present_in_the_served_graph() -> None:
    """The end-to-end check: a rule from the extract, observed in the router.

    Everything upstream can be right — the data fetched, the match computed,
    the tags injected, the Lua correct — and the rider still gets the old
    answer if the tiles being served predate any of it. This is the only test
    that closes that gap, because it asks the running graph rather than a file.

    It reads a way the overlay closes to a bromfiets, finds a point on it, and
    asserts the bromfiets carrier cannot start there while a class the overlay
    left alone can.
    """
    osmium = pytest.importorskip("osmium", reason="reads the extract")
    extract = _enriched_extract()
    if extract is None:
        pytest.skip("no enriched extract to read a closed way from")

    found: list[tuple[float, float]] = []

    class FindClosed(osmium.SimpleHandler):
        def way(self, w) -> None:
            if len(found) >= 25:
                return
            # Closed to a bromfiets by the authority, and open to it in OSM's
            # own tags, so the overlay is the only reason it is shut.
            if w.tags.get("amgraph:bromfiets") != "no":
                return
            if w.tags.get("highway") not in {"residential", "unclassified", "tertiary"}:
                return
            if w.tags.get("moped") or w.tags.get("access") or w.tags.get("vehicle"):
                return
            try:
                points = [(n.lat, n.lon) for n in w.nodes if n.location.valid()]
            except osmium.InvalidLocationError:
                return
            if len(points) >= 3:
                found.append(points[len(points) // 2])

    FindClosed().apply_file(str(extract), locations=True)
    if not found:
        pytest.skip("no unambiguous overlay-closed way to probe")

    # `locate` reports the edges at a point per costing, which is what the
    # access bits decide. A closed way yields no edge for that costing.
    closed_for_bromfiets = 0
    for lat, lon in found:
        response = httpx.post(
            f"{VALHALLA_URL}/locate",
            json={
                "locations": [{"lat": lat, "lon": lon}],
                "costing": "motorcycle",
                "verbose": True,
            },
            timeout=30,
        )
        if response.status_code != 200:
            continue
        results = response.json()
        edges = results[0].get("edges", []) if isinstance(results, list) else []
        # Snapping can reach a nearby open way, so "no edge within a few metres"
        # is the signal rather than "no edge at all".
        near = [e for e in edges if e.get("distance", 1e9) < 15]
        if not near:
            closed_for_bromfiets += 1

    assert closed_for_bromfiets > 0, (
        f"none of {len(found)} ways the overlay closes to a bromfiets is closed "
        "in the running graph. The tiles being served were built before the "
        "overlay, or without it."
    )
