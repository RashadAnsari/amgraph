"""Check actual tile access bits on the cycle edges selected from each input."""

from __future__ import annotations

import json
from pathlib import Path

from amgraph_rules.countries import modelled_countries
from amgraph_rules.profiles import costing_for, costing_options_for


def verify(client, work: Path):
    selected = json.loads((work / "access-probes.json").read_text())
    combined = json.loads((work / "combined.json").read_text())
    if set(selected) != {country.code for country in modelled_countries()}:
        raise ValueError("access probes must cover every supported country")
    report = {}
    for country in modelled_countries():
        source = selected[country.code]
        if (
            source["rules_version"] != country.rules_version
            or source["enriched_sha256"] != combined["countries"][country.code]["enriched_sha256"]
        ):
            raise ValueError("access probes do not describe the built input")
        report[country.code] = {}
        for name, probe in source["probes"].items():
            allowed = country.vehicle(probe["allowed"])
            barred = country.vehicle(probe["barred"])
            proved = []
            for candidate in probe["ways"]:
                way_id = candidate["way_id"]
                located = {}
                for label, vehicle in (("allowed", allowed), ("barred", barred)):
                    response = client.post(
                        "/locate",
                        json={
                            "locations": [{**candidate["points"][1], "minimum_reachability": 0}],
                            "costing": costing_for(vehicle.carrier),
                            "verbose": False,
                            "costing_options": costing_options_for(
                                vehicle.carrier, vehicle.speeds.roadway
                            ),
                        },
                    )
                    response.raise_for_status()
                    located[label] = {
                        edge["way_id"] for edge in response.json()[0].get("edges", [])
                    }
                if way_id in located["barred"]:
                    raise ValueError(
                        f"{country.code} {name}: barred class reaches OSM way {way_id}"
                    )
                if way_id not in located["allowed"]:
                    continue
                # Map matching uses the same access mask, and proves the open
                # cycle edge can actually be traversed. Its options deliberately
                # omit the hierarchy flag that crashes Valhalla 3.8.3 here.
                matched = False
                for points in (candidate["points"], list(reversed(candidate["points"]))):
                    response = client.post(
                        "/trace_attributes",
                        json={
                            "shape": points,
                            "shape_match": "map_snap",
                            "costing": costing_for(allowed.carrier),
                            "costing_options": costing_options_for(
                                allowed.carrier, allowed.speeds.roadway, for_map_matching=True
                            ),
                            "filters": {"action": "include", "attributes": ["edge.way_id"]},
                        },
                    )
                    if response.status_code >= 500:
                        response.raise_for_status()
                    if response.status_code == 200:
                        ids = {edge.get("way_id") for edge in response.json().get("edges", [])}
                        matched = way_id in ids
                    if matched:
                        break
                if matched:
                    proved.append(way_id)
                if len(proved) >= 3:
                    break
            if not proved:
                raise ValueError(f"{country.code} {name}: no cycle-edge traversal could be proved")
            report[country.code][name] = {"passed": True, "way_ids": proved}
            print(f"{country.code} {name}: proved {len(proved)} actual cycle edges", flush=True)
    return report
