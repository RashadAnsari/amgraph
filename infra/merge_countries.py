"""Merge audited country inputs into one graph without an input-order preference.

OSM IDs retain their identity across extracts. Conflicting source versions abort
rather than combining a junction from one snapshot with a way from another.
Country ownership comes from official geometry, never from the file's position.
"""

from __future__ import annotations

import importlib
import json
from collections import Counter
from pathlib import Path

import osmium
import shapely
from shapely.geometry import LineString, shape

from amgraph_rules.countries import modelled_countries
from artifacts import replace_atomically
from compact_source import compact
from prepare_country import digest, require_current


class Territories:
    def __init__(self, boundaries):
        self.boundaries = dict(sorted(boundaries.items()))
        self.union = shapely.union_all(list(self.boundaries.values()))
        for geometry in (*self.boundaries.values(), self.union):
            if geometry.is_empty or not geometry.is_valid:
                raise ValueError("invalid official territory")
            shapely.prepare(geometry)

    def countries(self, geometry):
        if not shapely.contains_properly(self.union, geometry):
            return ()
        return tuple(
            code for code, boundary in self.boundaries.items() if boundary.intersects(geometry)
        )

    def points(self, coordinates):
        if not coordinates:
            return []
        xs, ys = zip(*coordinates, strict=True)
        inside = shapely.contains_xy(self.union, xs, ys)
        masks = {
            code: shapely.intersects_xy(boundary, xs, ys)
            for code, boundary in self.boundaries.items()
        }
        return [
            tuple(code for code, mask in masks.items() if mask[index]) if inside[index] else ()
            for index in range(len(coordinates))
        ]


def source_paths(work: Path):
    result = {}
    for country in modelled_countries():
        module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
        directory = work / "countries" / country.code.lower()
        name = Path(module.EXTRACT_URL).name.removesuffix(".osm.pbf") + "-official.osm.pbf"
        result[country.code] = (directory, directory / name, module)
    return result


def merge(work: Path):
    sources = source_paths(work)
    boundaries = {}
    inputs = {}
    boundary_documents = {}
    zones = []
    for country in modelled_countries():
        require_current(country)
        directory, extract, module = sources[country.code]
        audit = json.loads((directory / "audit.json").read_text())
        actual = digest(extract)
        if (
            audit.get("country") != country.code
            or audit.get("rules_version") != country.rules_version
            or audit.get("enriched_sha256") != actual
            or audit.get("ways", 0) <= 0
        ):
            raise ValueError(f"{country.code} has no matching nonempty access audit")
        document = json.loads((directory / "boundaries" / module.BOUNDARY_FILENAME).read_text())
        boundaries[country.code] = shapely.union_all(
            [shape(f["geometry"]) for f in document["features"]]
        )
        boundary_documents[country.code] = document
        country_zones = json.loads((directory / "boundaries/legal-zones.geojson").read_text())
        for feature in country_zones["features"]:
            feature["properties"]["country"] = country.code
            zones.append(feature)
        inputs[country.code] = {
            "rules_version": country.rules_version,
            "extract_url": module.EXTRACT_URL,
            "enriched_sha256": actual,
            "audit": audit,
        }
    territories = Territories(boundaries)
    counts = Counter()
    missing_evidence = Counter()
    output = work / "all-countries-official.osm.pbf"
    compact_directory = work / "merge-inputs"
    compact_directory.mkdir(exist_ok=True)
    compacted = [
        compact(
            extract, compact_directory / f"{code.lower()}.osm.pbf", inputs[code]["audit"]["ways"]
        )
        for code, (_, extract, _) in sources.items()
    ]

    def write(candidate):
        processors = [osmium.FileProcessor(extract).with_locations() for extract in compacted]
        with osmium.SimpleWriter(str(candidate)) as writer:
            pending = []
            processed_nodes = 0

            def flush_nodes():
                nonlocal processed_nodes
                if not pending:
                    return
                owners = territories.points([(n.location.lon, n.location.lat) for n in pending])
                for node, countries in zip(pending, owners, strict=True):
                    node.tags["amgraph:country"] = ";".join(countries) or "unsupported"
                    writer.add_node(node)
                processed_nodes += len(pending)
                pending.clear()
                if processed_nodes % 1_000_000 == 0:
                    print(f"Merged and attributed {processed_nodes:,} nodes", flush=True)

            for copies in osmium.zip_processors(*processors):
                available = {
                    code: obj for code, obj in zip(sources, copies, strict=True) if obj is not None
                }
                objects = list(available.values())
                if len({obj.version for obj in objects}) != 1:
                    raise ValueError(
                        f"source snapshot conflict for OSM object {objects[0].id}; "
                        "refresh every input"
                    )
                # The lowest serialized tag set chooses descriptive metadata only;
                # legal metadata below comes exclusively from geometry ownership.
                obj = (
                    objects[0]
                    if len(objects) == 1
                    else min(objects, key=lambda item: sorted(dict(item.tags).items()))
                )
                if not obj.is_node():
                    flush_nodes()
                tags = {k: v for k, v in obj.tags if not k.startswith("amgraph:")}
                if obj.is_node():
                    controls = {
                        (
                            copy.location.lon,
                            copy.location.lat,
                            tuple(
                                sorted((k, v) for k, v in copy.tags if not k.startswith("amgraph:"))
                            ),
                        )
                        for copy in objects
                    }
                    if len(controls) != 1:
                        raise ValueError(f"conflicting junction evidence for node {obj.id}")
                    pending.append(obj.replace(tags=tags))
                    if len(pending) >= 50_000:
                        flush_nodes()
                elif obj.is_way() and (tags.get("highway") or tags.get("route") == "ferry"):
                    refs = {tuple(n.ref for n in copy.nodes) for copy in objects}
                    if len(refs) != 1:
                        raise ValueError(f"conflicting node order on way {obj.id}")
                    points = [(n.lon, n.lat) for n in obj.nodes if n.location.valid()]
                    owners = (
                        territories.countries(LineString(points))
                        if len(points) == len(obj.nodes) and len(points) >= 2
                        else ()
                    )
                    if any(code not in available for code in owners):
                        # Extract clipping and official boundaries need not agree.
                        # A neighbour's enrichment cannot replace missing evidence.
                        missing_evidence[";".join(owners)] += 1
                        owners = ()
                    if len(owners) == 1:
                        tags = dict(available[owners[0]].tags)
                    elif owners:
                        for code in owners:
                            for key, value in available[code].tags:
                                if key != "amgraph:country":
                                    tags[f"amgraph:{code}:{key}"] = value
                        # The physical edge has one speed. Pick the slowest
                        # numeric value; each country's Lua still checks its own
                        # unresolved speed evidence before granting access.
                        for key in ("maxspeed", "maxspeed:forward", "maxspeed:backward"):
                            values = [dict(available[code].tags).get(key) for code in owners]
                            numeric = [
                                float(v)
                                for v in values
                                if v is not None and v.replace(".", "", 1).isdigit()
                            ]
                            if numeric:
                                tags[key] = f"{min(numeric):g}"
                    tags["amgraph:country"] = ";".join(owners) or "unsupported"
                    counts[tags["amgraph:country"]] += 1
                    writer.add_way(obj.replace(tags=tags))
                elif obj.is_relation():
                    if len({tuple(sorted(dict(copy.tags).items())) for copy in objects}) != 1:
                        raise ValueError(f"conflicting normalized relation {obj.id}")
                    if (
                        len(
                            {
                                tuple((m.type, m.ref, m.role) for m in copy.members)
                                for copy in objects
                            }
                        )
                        != 1
                    ):
                        raise ValueError(f"conflicting relation members {obj.id}")
                    writer.add_relation(obj)
                else:
                    writer.add(obj)

    replace_atomically(output, write)
    directory = work / "boundaries"
    directory.mkdir(exist_ok=True)
    for code, document in boundary_documents.items():
        (directory / f"{code.lower()}.geojson").write_text(json.dumps(document) + "\n")
    (directory / "legal-zones.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": zones}) + "\n"
    )
    report = {
        "countries": inputs,
        "enriched_sha256": digest(output),
        "ways": dict(counts),
        "ways_closed_missing_country_evidence": dict(missing_evidence),
    }
    (work / "combined.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    return output
