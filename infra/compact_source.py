"""Omit standalone building outlines that the routing engine never imports.

Every other way and every relation is retained. Reference completion restores
any omitted building used by a relation, and preserves all referenced nodes
with their original access tags. Country attribution therefore spends its time
on the network and administrative geometry instead of cadastral buildings.
"""

from pathlib import Path

import osmium

from artifacts import replace_atomically


def compact(source: Path, destination: Path, expected_highways: int):
    counts = {"highways": 0, "building_candidates": 0, "relations": 0}

    def write(candidate):
        with osmium.BackReferenceWriter(candidate, source, remove_tags=False) as writer:
            processor = osmium.FileProcessor(source).with_filter(
                osmium.filter.EntityFilter(osmium.osm.WAY | osmium.osm.RELATION)
            )
            for obj in processor:
                if obj.is_way():
                    counts["highways"] += bool(obj.tags.get("highway"))
                    if obj.tags.get("building") and all(
                        obj.tags.get(key) is None for key in ("highway", "route", "railway")
                    ):
                        counts["building_candidates"] += 1
                        continue
                else:
                    counts["relations"] += 1
                writer.add(obj)
            if counts["highways"] != expected_highways:
                raise ValueError("routing input lost audited highway ways")

    replace_atomically(destination, write)
    print(f"Compacted {source.name}: {counts}", flush=True)
    return destination
