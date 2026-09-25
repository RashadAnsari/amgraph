"""Bind one released graph to the exact rules of every country it contains."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

from amgraph_rules.countries import modelled_countries
from check_build import check
from prepare_country import ROOT, digest, require_current


def _valhalla_version() -> str:
    for line in (ROOT / "valhalla/build.sh").read_text().splitlines():
        if line.startswith("VALHALLA_VERSION="):
            return line.split("=", 1)[1].strip().strip('"')
    raise ValueError("build.sh no longer declares VALHALLA_VERSION")


def build_stamp(work: Path, extract: Path):
    combined = check(work, extract)
    # Authority releases are discovered while preparing a country. Keep their
    # names alongside its input hash so a release still identifies that data
    # after the large authority download has been discarded.
    for country in modelled_countries():
        module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
        for field, filename in getattr(module, "SOURCE_RELEASE_FILES", {}).items():
            value = (work / "countries" / country.code.lower() / filename).read_text().strip()
            if not value:
                raise ValueError(f"{country.code} has an empty authority release stamp")
            combined["countries"][country.code][field] = value
    names = [
        "access.lua",
        "amgraph.lua",
        *[f"countries/{c.code.lower()}.lua" for c in modelled_countries()],
    ]
    return {
        "countries": combined["countries"],
        "rules_package_version": version("amgraph-rules"),
        "enriched_sha256": combined["enriched_sha256"],
        "lua_sha256": {name: digest(work / "lua" / name) for name in names},
        "tiles_sha256": digest(work / "valhalla/tiles.tar"),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def published_route_checks(routes: dict) -> dict:
    """The gate's verdicts, without the geometry that produced them.

    Every fixture comes back with the bounding box of the route it found, and
    the release notes carry this file verbatim. Publishing each result whole
    buries the only thing a reader needs, which is whether the gate passed and
    over how many attempts. The full report stays in routes.json, which the
    release does not carry.
    """
    return {
        "passed": routes["passed"],
        "countries": {
            code: {
                vehicle: {
                    "attempted": result["attempted"],
                    "successful": result["successful"],
                    "required": {
                        "attempted": len(result.get("required", ())),
                        "passed": sum(bool(r["ok"]) for r in result.get("required", ())),
                    },
                }
                for vehicle, result in measured.items()
            }
            for code, measured in routes["countries"].items()
        },
        "borders": {
            key: {"attempted": len(results), "passed": sum(bool(r["ok"]) for r in results)}
            for key, results in routes["borders"].items()
        },
        "access_probes": {
            code: {name: probe["way_ids"] for name, probe in probes.items()}
            for code, probes in routes["access_probes"].items()
        },
    }


def build(release: int, commit: str, work: Path) -> dict:
    stamp = json.loads((work / "build.json").read_text())
    countries = modelled_countries()
    if set(stamp["countries"]) != {c.code for c in countries}:
        raise ValueError("built graph does not cover exactly the supported country set")
    for name, expected in stamp["lua_sha256"].items():
        if (
            digest(work / "lua" / name) != expected
            or digest(ROOT / "valhalla/lua" / name) != expected
        ):
            raise ValueError("graph rules changed after the build")
    if stamp["tiles_sha256"] != digest(work / "valhalla/tiles.tar"):
        raise ValueError("graph archive changed after the build")
    routes = json.loads((work / "routes.json").read_text())
    if (
        routes.get("passed") is not True
        or routes.get("tiles_sha256") != stamp["tiles_sha256"]
        or set(routes.get("countries", {})) != {c.code for c in countries}
    ):
        raise ValueError("release lacks passing multi-country routes for this tile archive")
    for country in countries:
        measured = routes["countries"][country.code]
        if set(measured) != country.class_codes:
            raise ValueError("route gate did not test every vehicle class")
        if any(
            r["attempted"] < 10 or r["successful"] / r["attempted"] < 0.8 for r in measured.values()
        ):
            raise ValueError("route gate failed its reachability floor")
        # Re-checked here rather than trusted from `passed`, like the borders:
        # the floor above is a ratio, and a ratio is what let a class ship
        # unable to reach two city centres.
        module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
        required = len(getattr(module, "REQUIRED_ROUTE_CHECKS", ()))
        for vehicle, result in measured.items():
            answers = result.get("required", ())
            if len(answers) != required or not all(r.get("ok") is True for r in answers):
                raise ValueError(f"required route gate failed: {country.code}/{vehicle}")
    required_borders = {}
    for country in countries:
        module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
        for neighbour, pairs in getattr(module, "BORDER_ROUTE_CHECKS", {}).items():
            for vehicle in country.classes:
                required_borders[f"{country.code}-{neighbour}/{vehicle.carrier}"] = len(pairs)
    if set(routes.get("borders", {})) != set(required_borders):
        raise ValueError("route gate did not test every declared border crossing")
    for key, count in required_borders.items():
        results = routes["borders"][key]
        if len(results) != count or not all(result.get("ok") is True for result in results):
            raise ValueError(f"border route gate failed: {key}")
    for country in countries:
        module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
        expected_probes = {f"{a}/{b}" for a, b in module.ACCESS_PROBES}
        probes = routes.get("access_probes", {}).get(country.code, {})
        if set(probes) != expected_probes or any(
            p.get("passed") is not True or not p.get("way_ids") for p in probes.values()
        ):
            raise ValueError("release lacks actual cycle-edge access proofs")
    if stamp["rules_package_version"] != version("amgraph-rules"):
        raise ValueError("built graph and installed rules package disagree")
    entries = {}
    for country in countries:
        require_current(country)
        source = stamp["countries"][country.code]
        if source["rules_version"] != country.rules_version:
            raise ValueError(f"{country.code} build and runtime rules disagree")
        boundary = f"boundaries/{country.code.lower()}.geojson"
        entries[country.code] = {
            **source,
            "boundary": boundary,
            "boundary_sha256": digest(work / boundary),
            "rules_valid_until": country.valid_until.isoformat() if country.valid_until else None,
            "classes": {
                vehicle.code: {"carrier": vehicle.carrier.value} for vehicle in country.classes
            },
        }
    return {
        "schema_version": 2,
        "rules_package_version": stamp["rules_package_version"],
        "route_checks": published_route_checks(routes),
        "release": release,
        "countries": entries,
        "graph_commit": commit,
        "valhalla_version": _valhalla_version(),
        "build": stamp,
        "legal_zones": "boundaries/legal-zones.geojson",
        "legal_zones_sha256": digest(work / "boundaries/legal-zones.geojson"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=int)
    parser.add_argument("--work", type=Path, default=ROOT / "infra/work")
    parser.add_argument("--build-stamp", action="store_true")
    parser.add_argument("--extract", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.build_stamp:
        if args.extract is None:
            parser.error("--build-stamp requires --extract")
        manifest = build_stamp(args.work, args.extract)
    else:
        if args.release is None:
            parser.error("release manifests require --release")
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        manifest = build(args.release, commit, args.work)
    manifest["working_tree_dirty"] = bool(
        subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
    )
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
