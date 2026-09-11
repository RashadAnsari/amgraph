"""Build a country-attributed extract and its boundary artefacts.

Country modules own the law and data identifiers. This file owns geometry,
atomic writes, provenance and the requirement that a sidepath actually exists.
The Dutch WKD pipeline remains in official_access.py.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import urllib.request
import zipfile
from collections import Counter
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import osmium
import shapefile
import shapely
from lupa.lua54 import LuaRuntime
from pyproj import Transformer
from shapely.geometry import LineString, MultiPolygon, mapping, shape
from shapely.strtree import STRtree

from amgraph_rules.countries import rules_for
from artifacts import replace_atomically
from restrictions import conservative_restriction_tags

ROOT = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


class Access:
    def __init__(self, code: str):
        self.runtime = LuaRuntime(unpack_returned_tuples=True)
        self.lua = self.runtime.eval("function(p) return assert(loadfile(p))() end")(
            str(ROOT / "valhalla/lua/access.lua")
        )
        self.country = self.lua.COUNTRIES[code]
        if self.country is None:
            raise ValueError(f"no graph rules for {code}")
        self.classes = tuple((c.code, c.carrier) for c in self.country.classes.values())
        expected = {v.code: v.carrier.value for v in rules_for(code).classes}
        if any(expected.get(code) != carrier for code, carrier in self.classes) or set(
            expected.values()
        ) != {carrier for _, carrier in self.classes}:
            raise ValueError("Lua and Python carrier assignments disagree")

    def flags(self, tags: dict[str, str]) -> dict[str, str]:
        return dict(self.lua.carrier_flags(self.runtime.table_from(tags), self.country))

    def cycle(self, tags: dict[str, str]) -> bool:
        return self.lua.is_cycle_infrastructure(self.runtime.table_from(tags), self.country)


def require_current(country) -> None:
    today = datetime.now(UTC).date()
    if country.valid_until is not None and today >= country.valid_until:
        raise ValueError(
            f"{country.code} legal regime expired on {country.valid_until}; re-research"
        )
    verified = datetime.strptime(country.rules_version[3:13], "%Y-%m-%d").date()
    if not 0 <= (today - verified).days <= 90:
        raise ValueError(f"{country.code} rules are outside the 90-day legal review window")


def read_layer(archive: Path, layer: str) -> list[dict]:
    with zipfile.ZipFile(archive) as source:
        projection = source.read(layer + ".prj").decode()
        if "WGS_1984" not in projection and "WGS 84" not in projection:
            raise ValueError("expected the authority's WGS84 export")
        reader = shapefile.Reader(
            **{ext: BytesIO(source.read(f"{layer}.{ext}")) for ext in ("shp", "shx", "dbf")}
        )
        return [
            {
                "type": "Feature",
                "properties": record.record.as_dict(),
                "geometry": record.shape.__geo_interface__,
            }
            for record in reader.shapeRecords()
        ]


def checked_geometry(feature):
    geometry = shape(feature["geometry"])
    if geometry.geom_type == "Polygon":
        geometry = MultiPolygon([geometry])
    if geometry.geom_type != "MultiPolygon" or geometry.is_empty or not geometry.is_valid:
        raise ValueError("authority boundary must be a valid nonempty MultiPolygon")
    return geometry


def write_boundaries(module, country, archive: Path, work: Path):
    features = read_layer(archive, module.BOUNDARY_LAYER)
    matching = [
        f
        for f in features
        if all(
            f["properties"].get(key) == value for key, value in country.boundary.properties.items()
        )
    ]
    if len(matching) != 1:
        raise ValueError("authority export does not contain the expected unique country")
    area = checked_geometry(matching[0])
    matching[0]["geometry"] = mapping(area)
    boundary = {"type": "FeatureCollection", "features": matching}
    directory = work / "boundaries"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / module.BOUNDARY_FILENAME).write_text(json.dumps(boundary))

    regions = read_layer(archive, module.ZONE_LAYER)
    zones = []
    for name, zone in country.municipal_zones.items():
        matching = [
            f for f in regions if f["properties"].get(module.ZONE_ID_KEY) == zone.municipality_id
        ]
        if len(matching) != 1:
            raise ValueError(f"missing or ambiguous legal-zone boundary: {name}")
        geometry = checked_geometry(matching[0])
        zones.append(
            {
                "type": "Feature",
                "geometry": mapping(geometry),
                "properties": {
                    "name": name,
                    "municipality_id": zone.municipality_id,
                    "profiles": sorted(zone.powertrain_classes),
                    "allowed_powertrains": sorted(p.value for p in zone.allowed_powertrains),
                    "blocked_profiles": sorted(zone.blocked_classes),
                    "valid_from": zone.valid_from.isoformat() if zone.valid_from else None,
                    "valid_to": zone.valid_to.isoformat() if zone.valid_to else None,
                    "scope": "whole_administrative_area_conservative",
                    "source": module.BOUNDARY_URL,
                },
            }
        )
    (directory / "legal-zones.geojson").write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": zones,
            }
        )
    )
    shapely.prepare(area)
    return area


def coordinates(way):
    try:
        points = [(node.lon, node.lat) for node in way.nodes]
    except osmium.InvalidLocationError:
        return None
    return points if len(points) >= 2 else None


class Sidepaths(osmium.SimpleHandler):
    def __init__(self, access, module, area):
        super().__init__()
        self.access, self.module, self.boundary = access, module, area
        self.project = Transformer.from_crs(4326, 3035, always_xy=True).transform
        self.lines, self.permissions, self.ids = [], [], []
        self.excluded = set()
        self.counts = Counter()

    def way(self, way):
        if way.id in self.excluded or way.tags.get("highway") not in {"cycleway", "path"}:
            return
        tags = dict(way.tags)
        if not self.access.cycle(tags):
            return
        points = coordinates(way)
        if points is None or not shapely.contains_properly(self.boundary, LineString(points)):
            return
        flags = self.access.flags(self.module.enrich_way(tags, {}))
        permissions = {
            code: self.module.sidepath_obligation(tags, code)
            for code, carrier in self.access.classes
            if flags[carrier + "_forward"] == "true" or flags[carrier + "_backward"] == "true"
        }
        self.counts["paths"] += 1
        if not permissions:
            self.counts["closed_paths"] += 1
            return
        line = LineString([self.project(*point) for point in points])
        if line.length < 5:
            return
        self.lines.append(line)
        self.permissions.append(permissions)
        self.ids.append(way.id)
        self.counts.update(permissions.keys())

    def finish(self):
        self.tree = STRtree(self.lines)

    def adjacent(self, points):
        """A nearby crossing is not a parallel path.

        Require parallel tangents and at least 15 metres of overlap within
        20 metres. Only already-usable paths enter this index. A false match
        can close a roadway, but can never open an otherwise forbidden path.
        """
        line = LineString([self.project(*point) for point in points])
        if line.length < 15:
            return {}, []
        answer, evidence = {}, []
        for index in self.tree.query(line, predicate="dwithin", distance=20):
            path = self.lines[index]
            overlap = line.intersection(path.buffer(20)).length
            if overlap < min(30, max(15, line.length * 0.5)):
                continue
            midpoint = line.interpolate(0.5, normalized=True)
            on_path = path.project(midpoint)
            a, b = (
                path.interpolate(max(0, on_path - 10)),
                path.interpolate(min(path.length, on_path + 10)),
            )
            on_road = line.project(path.interpolate(on_path))
            c, d = (
                line.interpolate(max(0, on_road - 10)),
                line.interpolate(min(line.length, on_road + 10)),
            )
            ab, cd = (b.x - a.x, b.y - a.y), (d.x - c.x, d.y - c.y)
            denominator = math.hypot(*ab) * math.hypot(*cd)
            if not denominator or abs(ab[0] * cd[0] + ab[1] * cd[1]) / denominator < 0.9:
                continue
            evidence.append(self.ids[index])
            for code, obligation in self.permissions[index].items():
                if answer.get(code) != "mandatory":
                    answer[code] = obligation
        return answer, evidence


class RestrictionClosures(osmium.SimpleHandler):
    """Uninterpretable turns cannot leave their incident ways accessible."""

    def __init__(self):
        super().__init__()
        self.ways = set()
        self.relations = {}

    def relation(self, relation):
        try:
            conservative_restriction_tags(dict(relation.tags))
        except ValueError as exc:
            incident = {m.ref for m in relation.members if m.type == "w"}
            if not incident:
                raise ValueError(f"cannot contain unknown restriction {relation.id}") from exc
            self.ways.update(incident)
            self.relations[relation.id] = str(exc)


class Enrich(osmium.SimpleHandler):
    def __init__(self, writer, module, country, area, paths, restrictions):
        super().__init__()
        self.writer, self.module, self.country = writer, module, country
        self.boundary, self.paths = area, paths
        self.restrictions = restrictions
        self.counts = Counter()

    def node(self, node):
        # Source-supplied amgraph tags are never trusted as build evidence.
        tags = {k: v for k, v in node.tags if not k.startswith("amgraph:")}
        self.writer.add_node(node.replace(tags=tags))

    def way(self, way):
        source = dict(way.tags)
        if way.id in self.restrictions.ways:
            source["access:conditional"] = "no"
        if not source.get("highway"):
            self.writer.add_way(way)
            return
        points = coordinates(way)
        inside = points is not None and shapely.contains_properly(self.boundary, LineString(points))
        adjacent, evidence = ({}, [])
        # A crossing road still has obligations beside its Belgian section.
        # The path index contains only verified usable domestic paths; final
        # country attribution decides which source's evidence applies.
        if points is not None and not self.paths.access.cycle(source):
            adjacent, evidence = self.paths.adjacent(points)
        tags = self.module.enrich_way(source, adjacent)
        tags["amgraph:country"] = self.country.code if inside else "unsupported"
        if evidence:
            tags["amgraph:sidepaths"] = ",".join(str(identifier) for identifier in sorted(evidence))
        self.counts["inside" if inside else "outside"] += 1
        self.counts.update(k for k, v in tags.items() if k.startswith("amgraph:") and v == "no")
        self.writer.add_way(way.replace(tags=tags))

    def relation(self, relation):
        if relation.id in self.restrictions.relations:
            tags = dict(relation.tags)
            tags["type"] = "amgraph:closed_restriction"
            self.writer.add_relation(relation.replace(tags=tags))
            return
        try:
            tags = conservative_restriction_tags(dict(relation.tags))
        except ValueError as exc:
            raise ValueError(f"restriction relation {relation.id}: {exc}") from exc
        self.writer.add_relation(relation.replace(tags=tags))


def enrich_extract(extract, writer, handler):
    # Final merging attributes every node and removes untrusted amgraph tags.
    # Passing other objects through natively avoids Python work on buildings
    # and millions of nodes that cannot supply country access evidence.
    processor = (
        osmium.FileProcessor(extract)
        .with_locations()
        .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY | osmium.osm.RELATION))
        .with_filter(osmium.filter.KeyFilter("highway", "type"))
        .handler_for_filtered(writer)
    )
    for obj in processor:
        if obj.is_way():
            handler.way(obj)
        else:
            handler.relation(obj)


def prepare(code: str, work: Path):
    country = rules_for(code)
    require_current(country)
    module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
    extract = work / Path(module.EXTRACT_URL).name
    archive = work / "adminvector.zip"
    if not extract.is_file() or not archive.is_file():
        raise ValueError("missing country extract or official boundary archive; use --download")
    area = write_boundaries(module, country, archive, work)
    access = Access(country.code)
    restrictions = RestrictionClosures()
    restrictions.apply_file(str(extract))
    print("Unmodelled turns contained:", len(restrictions.relations), flush=True)
    paths = Sidepaths(access, module, area)
    paths.excluded = restrictions.ways
    paths.apply_file(str(extract), locations=True)
    paths.finish()
    print("Sidepath inventory:", dict(paths.counts), flush=True)
    output = work / (extract.name.removesuffix(".osm.pbf") + "-official.osm.pbf")
    counts = {}

    def write(candidate):
        with osmium.SimpleWriter(str(candidate)) as writer:
            handler = Enrich(writer, module, country, area, paths, restrictions)
            enrich_extract(extract, writer, handler)
            counts.update(handler.counts)

    replace_atomically(output, write)
    provenance = {
        "country": country.code,
        "rules_version": country.rules_version,
        "extract_url": module.EXTRACT_URL,
        "extract_sha256": digest(extract),
        "boundary_url": module.BOUNDARY_URL,
        "boundary_sha256": digest(archive),
        "enriched_sha256": digest(output),
        "counts": counts,
        "paths": dict(paths.counts),
        "closed_turns": restrictions.relations,
        "closed_turn_ways": sorted(restrictions.ways),
        "prepared_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (work / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps(provenance, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", required=True)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    country = rules_for(args.country)
    require_current(country)
    work = args.work or ROOT / "infra/work" / country.code.lower()
    work.mkdir(parents=True, exist_ok=True)
    if args.download:
        module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
        for url, name in (
            (module.EXTRACT_URL, Path(module.EXTRACT_URL).name),
            (module.BOUNDARY_URL, "adminvector.zip"),
        ):
            replace_atomically(work / name, lambda p, url=url: urllib.request.urlretrieve(url, p))
    prepare(country.code, work)
