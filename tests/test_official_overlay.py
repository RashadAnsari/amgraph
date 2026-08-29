"""The road authority's overlay must actually change what the graph allows.

Every other test here asks whether a rule is *correct*. This one asks whether
it is *doing anything*, which is a different question and the one that nearly
got past us.

The overlay writes three values and they carry very different risk. `no` is a
closure and safe by construction: WKD's own documentation warns that signs are
sometimes coupled to the wrong NWB section, and the geometric NWB-to-OSM join
adds another mismatch risk, but a false closure is only a detour.

The other two open something, so each is bounded to a case where the law leaves
no discretion, and the bounds are asserted here rather than trusted:
`on_roadway` may only appear on a carriageway, where RVV art. 5 lid 2 and art.
6 lid 2 make the rijbaan mandatory once no usable path exists; `yes` may only
appear on cycle infrastructure, and only for the snorfiets, whose art. 5 lid 1
answer is the same for a G11 and a G12a.

So these assert the overlay's *effect*, in bounds wide enough that ordinary
monthly drift in the source data passes and a filter regression does not.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ACCESS_LUA = ROOT / "valhalla" / "lua" / "access.lua"
WORK = ROOT / "infra" / "work"

lupa = pytest.importorskip("lupa.lua54", reason="lupa provides the Lua runtime")

#: Floors, not targets. The Netherlands has roughly 200,000 ways the authority
#: closes; this sits far enough below the measured figures that the monthly
#: refresh cannot trip it, and far enough above zero that a filter which guts
#: the overlay cannot pass.
MIN_CLOSED = 100_000
#: A closure that changes nothing is not a closure. Most of the ways the
#: authority shuts are ones our tag rules would have allowed, so the overlay
#: has to be the reason they are shut.
MIN_DECISIVE = 20_000

#: The two keys the overlay writes.
OVERLAY = ("amgraph:snorfiets", "amgraph:bromfiets")
COUNTRY = "amgraph:country"

#: Every value access.lua reads from those keys. A typo in the writer would be
#: silent: an unknown value parses, injects, builds and routes as though the
#: overlay had never been written.
KNOWN_VALUES = {"no", "on_roadway", "roadway_only", "yes"}

#: OSM highway values that are cycle infrastructure, per access.lua's
#: is_cycle_infrastructure. `path` needs a further tag and is checked in place.
CYCLE_HIGHWAYS = {"cycleway", "path"}


def _extract() -> Path:
    override = os.environ.get("AMGRAPH_EXTRACT")
    if override:
        return Path(override)
    enriched = sorted(WORK.glob("*-official.osm.pbf"))
    return enriched[0] if enriched else WORK / "netherlands-official.osm.pbf"


@pytest.fixture(scope="module")
def rules():
    """`access.lua`, with and without the overlay tags, for the Netherlands."""
    runtime = lupa.LuaRuntime()
    access = runtime.eval(f'dofile("{ACCESS_LUA}")')
    netherlands = access.COUNTRIES.NL

    def classes(tags: dict[str, str]) -> tuple[bool, bool, bool]:
        flags = dict(access.carrier_flags(runtime.table_from(tags), netherlands))
        return (
            flags["moped_forward"] == "true",
            flags["motorcycle_forward"] == "true",
            flags["truck_forward"] == "true",
        )

    return classes


@pytest.mark.graph
def test_the_overlay_reaches_the_extract_and_changes_the_answer(rules) -> None:
    """Counts the tags, and how many of them actually move a class.

    Reading the extract rather than the intermediate TSV on purpose: the
    question is whether the verdict survived injection into the file the graph
    is built from, which is the step that would silently drop it.
    """
    osmium = pytest.importorskip("osmium", reason="reads the extract")
    extract = _extract()
    if not extract.exists():
        pytest.skip(f"no enriched extract at {extract}")

    tags_seen: Counter[str] = Counter()
    decisive: Counter[str] = Counter()

    class Collect(osmium.SimpleHandler):
        def way(self, w) -> None:
            present = {k: w.tags.get(k) for k in OVERLAY if w.tags.get(k)}
            if not present:
                return
            for value in present.values():
                tags_seen[value] += 1

            # Did it change anything? Compare the way as tagged against the
            # same way with the overlay stripped out.
            tags = dict(w.tags)
            without = {k: v for k, v in tags.items() if k not in OVERLAY}
            if rules(tags) != rules(without):
                for value in present.values():
                    decisive[value] += 1

    Collect().apply_file(str(extract))

    assert tags_seen["no"] >= MIN_CLOSED, (
        f"only {tags_seen['no']:,} ways carry a closure, expected at least "
        f"{MIN_CLOSED:,}. The overlay is missing or was gutted."
    )
    assert set(tags_seen) <= KNOWN_VALUES, (
        f"the authority overlay contains a value the rules do not read: "
        f"{dict(tags_seen)}. Expected some of {sorted(KNOWN_VALUES)}."
    )

    moved = sum(decisive.values())
    assert moved >= MIN_DECISIVE, (
        f"the overlay is on {sum(tags_seen.values()):,} ways but changes the "
        f"answer on only {moved:,} of them, expected at least {MIN_DECISIVE:,}. "
        "Tags that decide nothing are a mechanism that is present and inert."
    )


@pytest.mark.graph
def test_every_overlay_value_is_one_the_rules_understand() -> None:
    """A typo in the writer would be silent: unknown values simply do nothing.

    `access.lua` compares against exact strings, so `amgraph:bromfiets=No`
    or `=onpath` would parse, inject, build and route as though the overlay had
    never been written.
    """
    osmium = pytest.importorskip("osmium", reason="reads the extract")
    extract = _extract()
    if not extract.exists():
        pytest.skip(f"no enriched extract at {extract}")

    seen: Counter[str] = Counter()

    class Collect(osmium.SimpleHandler):
        def way(self, w) -> None:
            for key in OVERLAY:
                value = w.tags.get(key)
                if value is not None:
                    seen[value] += 1

    Collect().apply_file(str(extract))
    unknown = {v: n for v, n in seen.items() if v not in KNOWN_VALUES}
    assert not unknown, (
        f"the extract carries overlay values access.lua does not read: {unknown}. "
        "These are silently ignored, so the rule they encode is not applied."
    )


@pytest.mark.graph
def test_the_two_permissive_values_stay_inside_their_bounds() -> None:
    """Neither opening may appear where its legal justification does not reach.

    `on_roadway` rests on art. 5 lid 2 and art. 6 lid 2, which are about the
    rijbaan, so on anything but a carriageway it would be lifting a closure no
    statute lifts. `yes` rests on art. 5 lid 1 admitting a snorfiets to a G11
    and a G12a alike, which is an argument about cycle paths and about that one
    class, so on a roadway or on the bromfiets key it would be unfounded.

    Both are written by a geometric match, and a match can land anywhere. This
    is the test that a misplaced one cannot become permission.
    """
    osmium = pytest.importorskip("osmium", reason="reads the extract")
    extract = _extract()
    if not extract.exists():
        pytest.skip(f"no enriched extract at {extract}")

    stray: Counter[str] = Counter()

    class Collect(osmium.SimpleHandler):
        def way(self, w) -> None:
            highway = w.tags.get("highway")
            cycle = highway == "cycleway" or (
                highway == "path"
                and (w.tags.get("bicycle") == "designated" or w.tags.get("traffic_sign"))
            )
            for key in OVERLAY:
                value = w.tags.get(key)
                if value == "roadway_only" and not cycle:
                    stray[f"roadway_only on highway={highway}"] += 1
                elif value == "roadway_only" and key.endswith("bromfiets"):
                    stray["roadway_only on the bromfiets key"] += 1
                elif value == "on_roadway" and cycle:
                    stray[f"on_roadway on highway={highway}"] += 1
                elif value == "yes":
                    if not cycle:
                        stray[f"yes on highway={highway}"] += 1
                    if key.endswith("bromfiets"):
                        stray["yes on the bromfiets key"] += 1

    Collect().apply_file(str(extract))
    assert not stray, (
        f"the overlay opens something outside the bounds its rule reaches: {dict(stray)}"
    )


@pytest.mark.graph
def test_every_routable_way_has_supported_country_attribution() -> None:
    """The extract polygon is not a legal border; the BRK boundary is.

    In particular, this catches the Belgian enclaves inside Baarle-Nassau and
    complete ways that cross an ordinary border. Neither may receive an amgraph
    carrier bit merely because Geofabrik included it in its Netherlands file.
    """
    osmium = pytest.importorskip("osmium", reason="reads the extract")
    extract = _extract()
    if not extract.exists():
        pytest.skip(f"no enriched extract at {extract}")

    runtime = lupa.LuaRuntime()
    access = runtime.eval(f'dofile("{ACCESS_LUA}")')
    missing: list[int] = []
    leaked: list[int] = []
    counts: Counter[str] = Counter()

    class Collect(osmium.SimpleHandler):
        def way(self, w) -> None:
            if w.tags.get("highway") is None and w.tags.get("route") != "ferry":
                return
            country = w.tags.get(COUNTRY)
            counts[country or "missing"] += 1
            if country not in {"NL", "unsupported"}:
                missing.append(w.id)
                return
            if country == "unsupported":
                flags = dict(access.carrier_flags(runtime.table_from(dict(w.tags))))
                if any(value == "true" for value in flags.values()):
                    leaked.append(w.id)

    Collect().apply_file(str(extract))

    assert not missing, f"{len(missing):,} route ways have no BRK attribution: {missing[:10]}"
    assert counts["unsupported"] > 0, (
        "the extract contains no foreign or border-crossing ways; the BRK boundary "
        "overlay is probably missing"
    )
    assert not leaked, f"unsupported ways retained amgraph access: {leaked[:10]}"


@pytest.mark.graph
def test_turn_restrictions_cannot_escape_through_a_borrowed_carrier_mode() -> None:
    """Valhalla's vehicle names do not mean the Dutch classes we put on them.

    The enriched PBF therefore removes exceptions and turns class-specific or
    conditional restrictions into a general, unconditional restriction before
    Valhalla parses relations. Checking the final extract makes this an
    end-to-end assertion rather than a unit test of the normaliser alone.
    """
    osmium = pytest.importorskip("osmium", reason="reads the extract")
    extract = _extract()
    if not extract.exists():
        pytest.skip(f"no enriched extract at {extract}")

    seen = 0
    unsafe: list[tuple[int, dict[str, str]]] = []

    class Collect(osmium.SimpleHandler):
        def relation(self, relation) -> None:
            nonlocal seen
            tags = dict(relation.tags)
            if tags.get("type") != "restriction":
                return
            seen += 1
            restriction_keys = [key for key in tags if key.startswith("restriction")]
            if restriction_keys != ["restriction"] or "except" in tags:
                unsafe.append((relation.id, tags))

    Collect().apply_file(str(extract))

    assert seen > 0, "the enriched extract contains no turn restrictions"
    assert not unsafe, (
        f"{len(unsafe)} turn restrictions can be misread through borrowed carrier modes: "
        f"{unsafe[:5]}"
    )
