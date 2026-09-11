"""Exhaustively audit the enriched extract; missing data is a failure.

The country module supplies assertions against the statutory invariants.
Every distinct combination of every consulted access tag is evaluated.
Counts and input hashes travel with the build instead of a skip-prone test log.
"""

from __future__ import annotations

import argparse
import importlib
import json
from collections import Counter
from pathlib import Path

import osmium

from amgraph_rules.countries import rules_for
from prepare_country import Access, digest, require_current
from restrictions import conservative_restriction_tags


def audit(code: str, work: Path):
    country = rules_for(code)
    require_current(country)
    module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
    provenance = json.loads((work / "provenance.json").read_text())
    extract = work / (Path(module.EXTRACT_URL).name.removesuffix(".osm.pbf") + "-official.osm.pbf")
    if (
        provenance["country"] != country.code
        or provenance["rules_version"] != country.rules_version
    ):
        raise ValueError("enrichment provenance disagrees with the current country rules")
    enriched_hash = digest(extract)
    if enriched_hash != provenance["enriched_sha256"]:
        raise ValueError("enriched extract changed after provenance was written")
    access = Access(code)
    keys = sorted(access.lua.consulted_keys(access.country).values())
    combos = Counter()
    relations = Counter()

    class Collect(osmium.SimpleHandler):
        def way(self, way):
            if way.tags.get("highway"):
                tags = dict(way.tags)
                combos[tuple(tags.get(key) for key in keys)] += 1

        def relation(self, relation):
            tags = dict(relation.tags)
            if tags.get("type") == "restriction":
                assert conservative_restriction_tags(tags) == tags, (
                    f"un-normalized turn {relation.id}"
                )
                relations["restrictions"] += 1

    Collect().apply_file(str(extract))
    assert combos, "an empty extract is not a passing audit"
    counts = Counter()
    for combo, count in combos.items():
        tags = {key: value for key, value in zip(keys, combo, strict=True) if value is not None}
        # No explicit country argument: exercise the production attribution gate.
        flags = dict(access.lua.carrier_flags(access.runtime.table_from(tags)))
        module.audit_access(tags, flags)
        for class_code, carrier in access.classes:
            if flags[carrier + "_forward"] == "true" or flags[carrier + "_backward"] == "true":
                counts[class_code] += count
    assert all(counts[code] > 1000 for code, _ in access.classes), dict(counts)
    report = {
        "country": code,
        "rules_version": country.rules_version,
        "enriched_sha256": enriched_hash,
        "combinations": len(combos),
        "ways": sum(combos.values()),
        "accessible_ways": dict(counts),
        "relations": dict(relations),
    }
    (work / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", required=True)
    parser.add_argument("--work", required=True, type=Path)
    args = parser.parse_args()
    audit(args.country, args.work)
