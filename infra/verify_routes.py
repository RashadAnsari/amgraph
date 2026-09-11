"""Measure every country's reachability against the one running graph."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

import httpx

from amgraph_rules.countries import modelled_countries, rules_for
from amgraph_rules.profiles import costing_for, costing_options_for
from prepare_country import ROOT, digest
from verify_access_probes import verify as verify_access_probes


def verify(url: str, output: Path, work: Path):
    report = {"countries": {}, "borders": {}, "tiles_sha256": digest(work / "valhalla/tiles.tar")}
    failures = []
    with httpx.Client(base_url=url.rstrip("/"), timeout=60) as client:
        client.get("/status").raise_for_status()

        def route(pair, vehicle):
            body = {
                "locations": [{"lat": lat, "lon": lon, "radius": 250} for lat, lon in pair],
                "costing": costing_for(vehicle.carrier),
                "costing_options": costing_options_for(vehicle.carrier, vehicle.speeds.roadway),
            }
            response = client.post("/route", json=body)
            if response.status_code != 200:
                return {"ok": False, "error": response.text[:300]}
            trip = response.json().get("trip", {})
            return {"ok": bool(trip.get("legs")), "summary": trip.get("summary")}

        for country in modelled_countries():
            module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
            pairs = module.ROUTE_CHECKS
            if len(pairs) < 10:
                raise ValueError(f"{country.code} needs at least ten distributed route fixtures")
            report["countries"][country.code] = {}
            for vehicle in country.classes:
                results = [route(pair, vehicle) for pair in pairs]
                successes = sum(result["ok"] for result in results)
                report["countries"][country.code][vehicle.code] = {
                    "successful": successes,
                    "attempted": len(results),
                    "routes": results,
                }
                print(f"{country.code} {vehicle.code}: {successes}/{len(results)}", flush=True)
                if successes / len(results) < 0.8:
                    failures.append(f"{country.code}/{vehicle.code} reachability below 80%")
            for neighbour, border_pairs in getattr(module, "BORDER_ROUTE_CHECKS", {}).items():
                target = rules_for(neighbour)
                for vehicle in country.classes:
                    if vehicle.carrier not in {v.carrier for v in target.classes}:
                        raise ValueError(
                            "border fixture requires a carrier supported on both sides"
                        )
                    results = [route(pair, vehicle) for pair in border_pairs]
                    key = f"{country.code}-{neighbour}/{vehicle.carrier}"
                    report["borders"][key] = results
                    if not results or not all(result["ok"] for result in results):
                        failures.append(f"{key} border route failed")
        report["access_probes"] = verify_access_probes(client, work)
    report["passed"] = not failures
    output.write_text(json.dumps(report, indent=2) + "\n")
    if failures:
        raise ValueError("; ".join(failures))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8002")
    parser.add_argument("--work", type=Path, default=ROOT / "infra/work")
    parser.add_argument("--output", type=Path, default=Path("infra/work/routes.json"))
    args = parser.parse_args()
    verify(args.url, args.output, args.work)
