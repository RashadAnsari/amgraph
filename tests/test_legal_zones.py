"""The per-route check for municipal rules the graph cannot hold."""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "infra"))

from amgraph_rules.countries.nl import MUNICIPAL_ZONES
from amgraph_rules.legal_zones import LegalZoneFileError, LegalZoneRule, LegalZones, Point
from amgraph_rules.profiles import Powertrain
from zones import zone_feature

TODAY = date(2026, 9, 25)
SQUARE = [[[[2, 2], [4, 2], [4, 4], [2, 4], [2, 2]]]]


def _feature(coordinates, **properties) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "name": "test zone",
            "municipality_id": "test-id",
            "profiles": ["bromfiets"],
            "allowed_powertrains": ["electric"],
            "blocked_profiles": [],
            "scope": "whole_administrative_area_conservative",
            **properties,
        },
        "geometry": {"type": "MultiPolygon", "coordinates": coordinates},
    }


def _load(tmp_path: Path, features: list[dict], **expected) -> LegalZones:
    path = tmp_path / "legal-zones.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    return LegalZones.from_geojson(path, **expected)


def _test_zone(
    tmp_path: Path,
    coordinates=SQUARE,
    *,
    profiles: tuple[str, ...] = ("bromfiets",),
    blocked: tuple[str, ...] = (),
    valid_from: str | None = None,
) -> LegalZones:
    """One zone called "test zone", checked against a rule written to match it."""
    return _load(
        tmp_path,
        [
            _feature(
                coordinates,
                profiles=list(profiles),
                blocked_profiles=list(blocked),
                valid_from=valid_from,
            )
        ],
        expected_names={"test zone"},
        expected_ids={"test zone": "test-id"},
        expected_rules={
            "test zone": LegalZoneRule(
                powertrain_classes=frozenset(profiles),
                allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
                blocked_classes=frozenset(blocked),
                valid_from=date.fromisoformat(valid_from) if valid_from else None,
            )
        },
    )


def test_a_combustion_route_inside_a_zone_is_blocked(tmp_path: Path) -> None:
    assert _test_zone(tmp_path).blocks(
        "bromfiets", Powertrain.COMBUSTION, [(3, 3), (3.5, 3.5)], on=TODAY
    )


def test_a_segment_cannot_cross_a_zone_between_outside_shape_points(tmp_path: Path) -> None:
    assert _test_zone(tmp_path).blocks(
        "bromfiets", Powertrain.COMBUSTION, [(1, 3), (5, 3)], on=TODAY
    )


def test_a_segment_between_two_holes_cannot_cross_the_restricted_area(tmp_path: Path) -> None:
    zones = _test_zone(
        tmp_path,
        [
            [
                [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
                [[1, 4], [3, 4], [3, 6], [1, 6], [1, 4]],
                [[7, 4], [9, 4], [9, 6], [7, 6], [7, 4]],
            ]
        ],
    )
    assert zones.blocks("bromfiets", Powertrain.COMBUSTION, [(2, 5), (8, 5)], on=TODAY)


def test_an_electric_two_wheeler_is_allowed(tmp_path: Path) -> None:
    assert not _test_zone(tmp_path).blocks("bromfiets", Powertrain.ELECTRIC, [(3, 3)], on=TODAY)


def test_a_blocked_class_is_refused_whatever_its_powertrain(tmp_path: Path) -> None:
    zones = _test_zone(tmp_path, profiles=("snorfiets", "bromfiets"), blocked=("snorfiets",))
    assert zones.blocks("snorfiets", Powertrain.ELECTRIC, [(3, 3)], on=TODAY)


def test_a_class_the_rule_does_not_reach_passes(tmp_path: Path) -> None:
    assert not _test_zone(tmp_path).blocks("brommobiel", Powertrain.COMBUSTION, [(3, 3)], on=TODAY)


def test_an_empty_zone_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(LegalZoneFileError, match="no legal zones"):
        _load(tmp_path, [], expected_names=set())


def test_a_weakened_zone_file_is_refused(tmp_path: Path) -> None:
    """Amsterdam's file letting combustion through no longer matches the rules."""
    with pytest.raises(LegalZoneFileError, match="legal-zone file is invalid"):
        _load(
            tmp_path,
            [
                _feature(
                    SQUARE,
                    name="Amsterdam",
                    municipality_id="GM0363",
                    profiles=["snorfiets", "bromfiets"],
                    allowed_powertrains=["electric", "combustion"],
                )
            ],
        )


def test_a_zone_with_the_wrong_official_municipality_id_is_refused(tmp_path: Path) -> None:
    swapped = {"Amsterdam": "GM0518", "Den Haag": "GM0363"}
    with pytest.raises(LegalZoneFileError, match="municipality id"):
        _load(
            tmp_path,
            [
                _feature(
                    SQUARE,
                    name=name,
                    municipality_id=municipality_id,
                    profiles=["snorfiets", "bromfiets", "speed_pedelec"],
                )
                for name, municipality_id in swapped.items()
            ],
        )


def test_the_released_zone_file_shape_is_accepted_as_published(tmp_path: Path) -> None:
    """What infra/zones.py writes is what this reads, extra properties included."""
    geometry = {"type": "MultiPolygon", "coordinates": SQUARE}
    zone = MUNICIPAL_ZONES["Den Haag"]
    zones = _load(
        tmp_path,
        [zone_feature("Den Haag", zone, geometry, source="test")],
        expected_names={"Den Haag"},
        expected_ids={"Den Haag": zone.municipality_id},
        expected_rules={
            "Den Haag": LegalZoneRule(
                powertrain_classes=zone.powertrain_classes,
                allowed_powertrains=zone.allowed_powertrains,
                blocked_classes=zone.blocked_classes,
                valid_from=zone.valid_from,
                valid_to=zone.valid_to,
            )
        },
    )
    assert zones.blocks("bromfiets", Powertrain.COMBUSTION, [(3, 3)], on=TODAY)


class TestARuleThatIsNotYetInForce:
    """Utrecht's emission rule runs from 2028-01-01, and until then it must
    refuse nothing.

    Writing a measure down when it is published rather than when it starts to
    bite is the whole point of the dates. The failure this guards against is
    either half: a future rule that blocks trips today, or a rule everyone has
    forgotten by the time it applies.
    """

    def _blocks(self, tmp_path: Path, valid_from: str | None, on: date) -> bool:
        zones = _test_zone(tmp_path, valid_from=valid_from)
        return zones.blocks("bromfiets", Powertrain.COMBUSTION, [(3, 3)], on=on)

    def test_it_refuses_nothing_the_day_before(self, tmp_path: Path) -> None:
        assert not self._blocks(tmp_path, "2028-01-01", date(2027, 12, 31))

    def test_it_binds_on_the_day_itself(self, tmp_path: Path) -> None:
        assert self._blocks(tmp_path, "2028-01-01", date(2028, 1, 1))

    def test_a_rule_with_no_start_date_binds(self, tmp_path: Path) -> None:
        assert self._blocks(tmp_path, None, date(2026, 8, 15))

    def test_a_malformed_date_is_refused_rather_than_ignored(self, tmp_path: Path) -> None:
        """Dropping it silently would make the rule bind immediately, or never."""
        with pytest.raises(LegalZoneFileError, match="legal-zone file is invalid"):
            _load(
                tmp_path,
                [_feature(SQUARE, valid_from="the first of January")],
                expected_names={"test zone"},
                expected_ids={"test zone": "test-id"},
                expected_rules={
                    "test zone": LegalZoneRule(
                        powertrain_classes=frozenset({"bromfiets"}),
                        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
                        blocked_classes=frozenset(),
                    )
                },
            )


def test_utrecht_carries_its_announced_2028_rule() -> None:
    """Petrol, diesel or gas brom- and snorfietsen with a DET up to 31-12-2017
    may not enter Utrecht from 2028-01-01. It changes nothing today, which is
    exactly what makes it easy to leave out and easy to forget."""
    utrecht = MUNICIPAL_ZONES["Utrecht"]
    rule = LegalZoneRule(
        powertrain_classes=utrecht.powertrain_classes,
        allowed_powertrains=utrecht.allowed_powertrains,
        blocked_classes=utrecht.blocked_classes,
        valid_from=utrecht.valid_from,
        valid_to=utrecht.valid_to,
    )
    assert "snorfiets" in utrecht.powertrain_classes
    assert utrecht.allowed_powertrains == frozenset({Powertrain.ELECTRIC})
    assert not rule.in_force(date(2027, 12, 31))
    assert rule.in_force(date(2028, 1, 1))


class TestADetailedBoundary:
    """A real municipal boundary has thousands of vertices, and a route hundreds
    of points.

    Checking every point and every segment against every edge made a 15 km
    route nowhere near any zone take minutes on a small server. The timing
    bounds are loose on purpose: the quadratic check takes seconds on these
    shapes, the indexed one milliseconds.
    """

    CENTRE = (5.0, 52.0)

    def _circle(self, radius: float, vertices: int) -> list[list[float]]:
        ring = [
            [
                self.CENTRE[0] + radius * math.cos(2 * math.pi * i / vertices),
                self.CENTRE[1] + radius * math.sin(2 * math.pi * i / vertices),
            ]
            for i in range(vertices)
        ]
        return [*ring, ring[0]]

    def _zones(self, tmp_path: Path) -> LegalZones:
        """A disc of radius 0.1 degrees with a hole of radius 0.02 in the middle."""
        return _test_zone(tmp_path, [[self._circle(0.1, 10_000), self._circle(0.02, 2_000)]])

    def _line(self, start: Point, end: Point, points: int) -> list[Point]:
        return [
            (
                start[0] + (end[0] - start[0]) * i / (points - 1),
                start[1] + (end[1] - start[1]) * i / (points - 1),
            )
            for i in range(points)
        ]

    def _blocks(self, zones: LegalZones, shape: list[Point]) -> tuple[bool, float]:
        started = time.perf_counter()
        blocked = zones.blocks("bromfiets", Powertrain.COMBUSTION, shape, on=TODAY)
        return blocked, time.perf_counter() - started

    def test_a_route_far_from_the_zone_is_answered_at_once(self, tmp_path: Path) -> None:
        blocked, seconds = self._blocks(
            self._zones(tmp_path), self._line((6.0, 53.0), (6.2, 53.1), 1_000)
        )
        assert not blocked
        assert seconds < 0.5

    def test_a_route_skirting_the_zone_is_answered_quickly(self, tmp_path: Path) -> None:
        """Inside the zone's bounding box but never inside the zone: the
        corner of the box the disc does not reach."""
        blocked, seconds = self._blocks(
            self._zones(tmp_path), self._line((4.9, 52.07), (4.93, 52.1), 1_000)
        )
        assert not blocked
        assert seconds < 0.5

    def test_a_route_that_enters_is_blocked(self, tmp_path: Path) -> None:
        shape = self._line((4.8, 52.0), (4.95, 52.0), 1_000)
        assert self._blocks(self._zones(tmp_path), shape)[0]

    def test_one_segment_across_the_ring_between_two_points_outside_is_blocked(
        self, tmp_path: Path
    ) -> None:
        """No shape point falls inside, so only the edge test can see it."""
        assert self._blocks(self._zones(tmp_path), [(4.95, 52.3), (4.95, 51.7)])[0]

    def test_a_route_wholly_inside_the_hole_is_not_blocked(self, tmp_path: Path) -> None:
        blocked, seconds = self._blocks(
            self._zones(tmp_path), self._line((4.99, 52.0), (5.01, 52.005), 1_000)
        )
        assert not blocked
        assert seconds < 0.5

    def test_a_route_wholly_inside_the_zone_is_blocked(self, tmp_path: Path) -> None:
        shape = self._line((5.05, 52.0), (5.06, 52.01), 1_000)
        assert self._blocks(self._zones(tmp_path), shape)[0]
