"""One shape for a municipal legal-zone feature, whichever country wrote it.

Two writers produce `legal-zones.geojson`: the Dutch authority pipeline in
legal_zones.py and the generic country preparation in prepare_country.py.
merge_countries.py concatenates their output into the single file a release
carries, so a property one of them forgets is a by-law that silently leaves the
graph. Building the feature in one place is what stops that.
"""

from __future__ import annotations

from amgraph_rules.rules import MunicipalZone


def zone_feature(name: str, zone: MunicipalZone, geometry: dict, source: str) -> dict:
    """One municipal rule, as the release publishes it.

    `geometry` is the official administrative area, unbuffered and unsimplified.
    The zone is stated for the whole of it because the facts the by-law turns on
    — a date of first registration, an engine cycle, an exemption — are not in a
    routing request, so the only claim that can be proved is being outside it.
    """
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "name": name,
            "municipality_id": zone.municipality_id,
            "profiles": sorted(zone.powertrain_classes),
            "allowed_powertrains": sorted(p.value for p in zone.allowed_powertrains),
            "blocked_profiles": sorted(zone.blocked_classes),
            "roadway_only_profiles": sorted(zone.roadway_only_classes),
            "valid_from": zone.valid_from.isoformat() if zone.valid_from else None,
            "valid_to": zone.valid_to.isoformat() if zone.valid_to else None,
            "scope": "whole_administrative_area_conservative",
            "source": source,
        },
    }
