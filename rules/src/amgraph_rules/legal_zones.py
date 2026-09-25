"""Whether a route may be ridden, given the municipal rules the graph cannot hold.

The graph carries one access bit per carrier, and a combustion and an electric
bromfiets ride the same one, so an emission zone cannot be closed in the tiles
without closing it to the vehicles it admits. It is decided per route instead,
against ``boundaries/legal-zones.geojson`` from the same release. A route from
this graph is lawful only once this check has passed it, which is why the check
ships here beside the rules rather than being left for every consumer to
rewrite.

This is the one piece of logic in a package that is otherwise types and data.
It needs nothing but the standard library, so it costs a consumer no
dependencies.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from pathlib import Path
from typing import TypeAlias

from amgraph_rules.countries import modelled_countries
from amgraph_rules.profiles import Powertrain
from amgraph_rules.rules import MunicipalZone

__all__ = ["LegalZoneFileError", "LegalZoneRule", "LegalZones", "Point"]


class LegalZoneFileError(ValueError):
    """The zone file is missing, malformed or disagrees with the verified rules.

    A consumer must stop routing on this, not route without the zones: a file
    that no longer matches the rules is a by-law that would silently stop
    applying.
    """


#: (lon, lat), the order GeoJSON uses.
Point: TypeAlias = tuple[float, float]
Ring: TypeAlias = tuple[Point, ...]
Polygon: TypeAlias = tuple[Ring, ...]


@dataclass(frozen=True)
class LegalZoneRule:
    powertrain_classes: frozenset[str]
    allowed_powertrains: frozenset[Powertrain]
    blocked_classes: frozenset[str]

    #: When the rule starts and stops binding. A municipality may announce a
    #: measure years ahead — Utrecht's runs from 2028-01-01 — and writing the
    #: date down is the difference between a rule that starts on time and one
    #: somebody has to remember.
    valid_from: date | None = None
    valid_to: date | None = None

    def in_force(self, on: date) -> bool:
        if self.valid_from is not None and on < self.valid_from:
            return False
        return not (self.valid_to is not None and on >= self.valid_to)


#: Municipal rules live in the country modules, with every other fact about
#: that country's law. This module keeps the geometry engine, which is the same
#: wherever the rider is, and reads the rules from every modelled country.
#:
#: Municipality names are the key, so two countries with a municipality of the
#: same name would collide. That is caught here rather than discovered later,
#: because the failure would be a Belgian by-law silently gating a Dutch trip.
def _country_zones() -> Mapping[str, MunicipalZone]:
    zones: dict[str, MunicipalZone] = {}
    for country in modelled_countries():
        for name, zone in country.municipal_zones.items():
            if name in zones:
                raise ValueError(
                    f"two modelled countries both have a municipality called {name!r}; "
                    "the zone file cannot tell them apart"
                )
            zones[name] = zone
    return zones


EXPECTED_ZONE_NAMES = frozenset(_country_zones())
EXPECTED_ZONE_IDS: Mapping[str, str] = {
    name: zone.municipality_id for name, zone in _country_zones().items()
}
EXPECTED_ZONE_RULES: Mapping[str, LegalZoneRule] = {
    name: LegalZoneRule(
        powertrain_classes=zone.powertrain_classes,
        allowed_powertrains=zone.allowed_powertrains,
        blocked_classes=zone.blocked_classes,
        valid_from=zone.valid_from,
        valid_to=zone.valid_to,
    )
    for name, zone in _country_zones().items()
}


#: min lon, min lat, max lon, max lat.
Bounds: TypeAlias = tuple[float, float, float, float]
Cell: TypeAlias = tuple[int, int]
Edge: TypeAlias = tuple[Point, Point]

#: Cells along the longer side of a boundary's bounding box. Amsterdam's 8,380
#: edges then share cells of roughly 200 m, a handful to a cell, and a route
#: segment of a few dozen metres looks up one or two of them.
_GRID_CELLS = 128


@dataclass(frozen=True)
class Boundary:
    """One polygon, with its edges bucketed on a grid.

    The index only chooses which edges are worth testing. Every answer still
    comes from the exact tests below, so it can make a check faster and never
    make it weaker.
    """

    polygon: Polygon
    bounds: Bounds
    cell_size: float
    columns: int
    rows: int
    grid: Mapping[Cell, list[Edge]]

    @classmethod
    def of(cls, polygon: Polygon) -> Boundary:
        bounds = _bounds(point for ring in polygon for point in ring)
        extent = max(bounds[2] - bounds[0], bounds[3] - bounds[1])
        cell_size = extent / _GRID_CELLS if extent > 0 else 1.0
        columns = int((bounds[2] - bounds[0]) / cell_size) + 1
        rows = int((bounds[3] - bounds[1]) / cell_size) + 1
        grid: dict[Cell, list[Edge]] = {}
        boundary = cls(polygon, bounds, cell_size, columns, rows, grid)
        for ring in polygon:
            for edge in pairwise(ring):
                for cell in boundary._cells(_bounds(edge)):
                    grid.setdefault(cell, []).append(edge)
        return boundary

    def meets(self, points: tuple[Point, ...], route: Bounds) -> bool:
        if not _overlap(self.bounds, route):
            return False
        # A line that never touches the boundary stays on one side of it, so
        # its first point answers for all of them. Testing every point instead
        # walks every edge once per point, which is what made a single route
        # take minutes.
        if _polygon_covers(points[0], self.polygon):
            return True
        return any(self._segment_meets(start, end) for start, end in pairwise(points))

    def _segment_meets(self, start: Point, end: Point) -> bool:
        segment = (start, end)
        if not _overlap(self.bounds, _bounds(segment)):
            return False
        return any(
            _segments_intersect(start, end, edge_start, edge_end)
            for cell in self._cells(_bounds(segment))
            for edge_start, edge_end in self.grid.get(cell, ())
        )

    def _cells(self, bounds: Bounds) -> Iterator[Cell]:
        """Every cell a bounding box touches, clamped to the grid.

        Two boxes that share a point share the cell that point falls in, because
        the same rounding places it from either side. That is what keeps an
        intersection from slipping between cells.
        """
        first_column, first_row = self._cell_of(bounds[0], bounds[1])
        last_column, last_row = self._cell_of(bounds[2], bounds[3])
        for column in range(first_column, last_column + 1):
            for row in range(first_row, last_row + 1):
                yield column, row

    def _cell_of(self, lon: float, lat: float) -> Cell:
        column = math.floor((lon - self.bounds[0]) / self.cell_size)
        row = math.floor((lat - self.bounds[1]) / self.cell_size)
        return min(max(column, 0), self.columns - 1), min(max(row, 0), self.rows - 1)


@dataclass(frozen=True)
class LegalZone:
    name: str
    rule: LegalZoneRule
    boundaries: tuple[Boundary, ...]


@dataclass(frozen=True)
class LegalZones:
    """Areas where vehicle facts the graph cannot see decide access.

    A powertrain explicitly allowed by an emission rule may pass; anything else
    the rule reaches is refused for the whole municipality, because a class and
    a powertrain are all a route is asked with: there is no date of first
    registration or engine cycle to test a transition rule against.

    This is the heaviest gate on a route from this graph and it refuses whole
    trips, so it is for rules that genuinely cannot be expressed on an edge. A rule about
    *which road* a rider belongs on is not one of those: it belongs in the
    graph, where it costs a detour rather than a route.
    """

    zones: tuple[LegalZone, ...]

    @classmethod
    def from_geojson(
        cls,
        path: Path,
        *,
        expected_names: set[str] | frozenset[str] = EXPECTED_ZONE_NAMES,
        expected_ids: Mapping[str, str] = EXPECTED_ZONE_IDS,
        expected_rules: Mapping[str, LegalZoneRule] = EXPECTED_ZONE_RULES,
    ) -> LegalZones:
        try:
            document = json.loads(path.read_text())
            if document.get("type") != "FeatureCollection":
                raise ValueError("expected a FeatureCollection")
            features = document["features"]
            zones: list[LegalZone] = []
            for feature in features:
                properties = feature["properties"]
                geometry = feature["geometry"]
                if geometry.get("type") != "MultiPolygon":
                    raise ValueError("every legal zone must be a MultiPolygon")
                polygons = tuple(
                    tuple(
                        tuple((float(lon), float(lat)) for lon, lat, *_ in ring) for ring in polygon
                    )
                    for polygon in geometry["coordinates"]
                )
                _validate_polygons(polygons)
                name = str(properties["name"])
                rule = LegalZoneRule(
                    powertrain_classes=frozenset(str(value) for value in properties["profiles"]),
                    allowed_powertrains=frozenset(
                        Powertrain(value) for value in properties["allowed_powertrains"]
                    ),
                    blocked_classes=frozenset(
                        str(value) for value in properties["blocked_profiles"]
                    ),
                    valid_from=_date_or_none(properties.get("valid_from")),
                    valid_to=_date_or_none(properties.get("valid_to")),
                )
                if rule != expected_rules.get(name):
                    raise ValueError(f"legal-zone rules do not match the verified rules for {name}")
                if properties.get("scope") != "whole_administrative_area_conservative":
                    raise ValueError("legal-zone scope is not conservative")
                if properties.get("municipality_id") != expected_ids.get(name):
                    raise ValueError(f"legal-zone municipality id does not match {name}")
                zones.append(
                    LegalZone(
                        name=name,
                        rule=rule,
                        boundaries=tuple(Boundary.of(polygon) for polygon in polygons),
                    )
                )
            if not zones:
                raise ValueError("no legal zones")
            names = [zone.name for zone in zones]
            if len(names) != len(set(names)) or set(names) != set(expected_names):
                raise ValueError("legal-zone municipalities are incomplete or unexpected")
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LegalZoneFileError(f"legal-zone file is invalid: {exc}") from exc
        return cls(zones=tuple(zones))

    def blocks(
        self,
        vehicle_code: str,
        powertrain: Powertrain,
        shape: Sequence[Point],
        *,
        on: date,
    ) -> bool:
        """Whether a municipal rule refuses this route on the given day.

        ``shape`` is the whole route as (lon, lat) points, not its waypoints: a
        route between two points outside a zone can still pass through it.

        ``on`` has no default because the day is the caller's to know. A rule
        announced for a future date refuses nothing until that date arrives,
        which is what lets a measure be written down when it is published
        rather than when it starts to bite.
        """
        if not shape:
            return False
        points = tuple((float(lon), float(lat)) for lon, lat in shape)
        route = _bounds(points)
        for zone in self.zones:
            rule = zone.rule
            if not rule.in_force(on):
                continue
            class_is_blocked = vehicle_code in rule.blocked_classes
            powertrain_is_blocked = (
                vehicle_code in rule.powertrain_classes
                and powertrain not in rule.allowed_powertrains
            )
            if not class_is_blocked and not powertrain_is_blocked:
                continue
            if any(boundary.meets(points, route) for boundary in zone.boundaries):
                return True
        return False


def _bounds(points: Iterable[Point]) -> Bounds:
    lons, lats = zip(*points, strict=True)
    return min(lons), min(lats), max(lons), max(lats)


def _overlap(a: Bounds, b: Bounds) -> bool:
    return a[0] <= b[2] and b[0] <= a[2] and a[1] <= b[3] and b[1] <= a[3]


def _validate_polygons(polygons: tuple[Polygon, ...]) -> None:
    if not polygons:
        raise ValueError("legal-zone geometry is empty")
    for polygon in polygons:
        if not polygon:
            raise ValueError("legal-zone polygon has no rings")
        for ring in polygon:
            if len(ring) < 4 or ring[0] != ring[-1]:
                raise ValueError("legal-zone ring is not closed")
            for lon, lat in ring:
                if not math.isfinite(lon) or not math.isfinite(lat):
                    raise ValueError("legal-zone coordinate is not finite")
                if not -180 <= lon <= 180 or not -90 <= lat <= 90:
                    raise ValueError("legal-zone coordinate is out of range")


def _polygon_covers(point: Point, polygon: Polygon) -> bool:
    outer = _ring_location(point, polygon[0])
    if outer < 0:
        return False
    if outer == 0:
        return True
    return not any(_ring_location(point, hole) > 0 for hole in polygon[1:])


def _ring_location(point: Point, ring: Ring) -> int:
    x, y = point
    inside = False
    for a, b in pairwise(ring):
        ax, ay = a
        bx, by = b
        cross = _orientation(a, b, point)
        tolerance = 1e-12 * max(1.0, abs(bx - ax), abs(by - ay))
        if (
            abs(cross) <= tolerance
            and min(ax, bx) <= x <= max(ax, bx)
            and min(ay, by) <= y <= max(ay, by)
        ):
            return 0
        if (ay > y) != (by > y):
            intersection = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < intersection:
                inside = not inside
    return 1 if inside else -1


def _orientation(a: Point, b: Point, c: Point) -> float:
    return (c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    def side(one: Point, two: Point, point: Point) -> int:
        value = _orientation(one, two, point)
        if abs(value) <= 1e-12:
            return 0
        return 1 if value > 0 else -1

    ab_c, ab_d = side(a, b, c), side(a, b, d)
    cd_a, cd_b = side(c, d, a), side(c, d, b)
    if ab_c * ab_d < 0 and cd_a * cd_b < 0:
        return True

    def on_segment(one: Point, point: Point, two: Point) -> bool:
        return min(one[0], two[0]) <= point[0] <= max(one[0], two[0]) and min(
            one[1], two[1]
        ) <= point[1] <= max(one[1], two[1])

    return (
        (ab_c == 0 and on_segment(a, c, b))
        or (ab_d == 0 and on_segment(a, d, b))
        or (cd_a == 0 and on_segment(c, a, d))
        or (cd_b == 0 and on_segment(c, b, d))
    )


def _date_or_none(raw: object) -> date | None:
    """An ISO date from the zone file, or None.

    A malformed date is a hard error rather than an ignored field: dropping it
    silently would make a dated rule bind immediately, or never at all.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise ValueError("legal-zone validity date must be a string")
    return date.fromisoformat(raw)
