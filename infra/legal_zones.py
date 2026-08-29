"""Build conservative municipal vehicle-rule polygons from official BRK data.

The request carries powertrain but not first-registration date, engine cycle or
an exemption. The municipalities' current rules depend on those missing facts.
For a combustion two-wheeler the only claim the API can prove is outside an
affected emission-zone municipality.

`snorfiets_roadway` marks the municipalities that have used RVV art. 5 lid 8 to
move snorfietsen onto the rijbaan. That is not an API gate: it is read by
infra/official_access.py, which takes the class off every verplicht fietspad
inside the polygon at graph build time. Expressing it per edge is what keeps it
from refusing whole routes through Amsterdam and Utrecht, which is what an API
gate on these polygons would do. See docs/rules.md §5 NL-ACC-04.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

#: The municipal rules, taken from the country module rather than restated
#: here. Two copies of the same by-law drift, and the API validates the file
#: this script writes against that module — so a second list would only ever be
#: a way to fail that check later instead of now.
from amgraph_rules.countries.nl import MUNICIPAL_ZONES

#: BRK writes the official name, which is not always the one riders use.
OFFICIAL_NAMES = {"Den Haag": "'s-Gravenhage"}


def _official(name: str) -> str:
    return OFFICIAL_NAMES.get(name, name)


TARGETS = {_official(name): (name, zone.municipality_id) for name, zone in MUNICIPAL_ZONES.items()}


def build(inputs: list[Path], output: Path) -> None:
    found: dict[str, dict] = {}
    for path in inputs:
        document = json.loads(path.read_text())
        for feature in document.get("features", []):
            official_name = (feature.get("properties") or {}).get("naam")
            if official_name in TARGETS:
                if official_name in found and found[official_name] != feature:
                    raise ValueError(f"duplicate municipality {official_name}")
                found[official_name] = feature

    missing = set(TARGETS) - set(found)
    if missing:
        raise ValueError(f"official municipality data lacks {sorted(missing)}")

    features = []
    for official_name, (public_name, municipality_id) in TARGETS.items():
        zone = MUNICIPAL_ZONES[public_name]
        source = found[official_name]
        if source["properties"].get("identificatie") != municipality_id:
            raise ValueError(f"{official_name} has an unexpected municipality id")
        geometry = source.get("geometry") or {}
        if geometry.get("type") != "MultiPolygon" or not geometry.get("coordinates"):
            raise ValueError(f"{official_name} is not a non-empty MultiPolygon")
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "name": public_name,
                    "municipality_id": municipality_id,
                    "profiles": sorted(zone.powertrain_classes),
                    "allowed_powertrains": sorted(p.value for p in zone.allowed_powertrains),
                    "blocked_profiles": sorted(zone.blocked_classes),
                    "snorfiets_roadway": "snorfiets" in zone.roadway_only_classes,
                    "valid_from": zone.valid_from.isoformat() if zone.valid_from else None,
                    "valid_to": zone.valid_to.isoformat() if zone.valid_to else None,
                    "scope": "whole_municipality_conservative",
                    "source": (
                        "https://api.pdok.nl/kadaster/brk-bestuurlijke-gebieden/"
                        "ogc/v1/collections/gemeentegebied/items"
                    ),
                },
                "geometry": geometry,
            }
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, separators=(",", ":"))
    )
    print(f"wrote {output} ({len(features)} conservative legal zones)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.inputs, args.output)
