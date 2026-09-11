"""Select real cycle edges whose country law distinguishes two vehicle classes."""

from __future__ import annotations

import argparse
import json
from contextlib import suppress
from pathlib import Path

import osmium
from shapely.geometry import LineString

from amgraph_rules.countries import modelled_countries
from merge_countries import source_paths
from prepare_country import ROOT, Access, digest


class Select(osmium.SimpleHandler):
    def __init__(self, country, access, probes):
        super().__init__()
        self.country, self.access, self.probes = country, access, probes

    def way(self, way):
        if way.tags.get("amgraph:country") != self.country.code:
            return
        if way.tags.get("highway") not in {"cycleway", "path"}:
            return
        tags = dict(way.tags)
        if not self.access.cycle(tags):
            return
        flags = self.access.flags(tags)
        for probe in self.probes.values():
            if len(probe["ways"]) >= 25:
                continue
            allowed = self.country.vehicle(probe["allowed"]).carrier.value
            barred = self.country.vehicle(probe["barred"]).carrier.value
            if not any(flags[f"{allowed}_{d}"] == "true" for d in ("forward", "backward")):
                continue
            if any(flags[f"{barred}_{d}"] == "true" for d in ("forward", "backward")):
                continue
            if len(way.nodes) < 2 or not all(n.location.valid() for n in way.nodes):
                continue
            line = LineString([(n.lon, n.lat) for n in way.nodes])
            if line.length < 0.0003:
                continue
            points = [line.interpolate(f, normalized=True) for f in (0.35, 0.5, 0.65)]
            probe["ways"].append(
                {"way_id": way.id, "points": [{"lat": p.y, "lon": p.x} for p in points]}
            )
        if all(len(probe["ways"]) >= 25 for probe in self.probes.values()):
            raise StopIteration


def collect(work: Path):
    report = {}
    for country in modelled_countries():
        _, extract, module = source_paths(work)[country.code]
        access = Access(country.code)
        probes = {
            f"{allowed}/{barred}": {"allowed": allowed, "barred": barred, "ways": []}
            for allowed, barred in module.ACCESS_PROBES
        }

        with suppress(StopIteration):
            Select(country, access, probes).apply_file(str(extract), locations=True)
        if not probes or any(not probe["ways"] for probe in probes.values()):
            raise ValueError(f"{country.code} lacks distinguishable real cycle edges")
        report[country.code] = {
            "rules_version": country.rules_version,
            "enriched_sha256": digest(extract),
            "probes": probes,
        }
        print(f"Selected {country.code} cycle probes", flush=True)
    (work / "access-probes.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, default=ROOT / "infra/work")
    args = parser.parse_args()
    collect(args.work)
