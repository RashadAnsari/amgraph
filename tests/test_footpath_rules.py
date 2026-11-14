"""NL-ACC-12, as pure functions.

`footpath_overlay` decides what infra/official_access.py writes on a footway or
pedestrian way, and it has to agree with the NEVER branch of
`valhalla/lua/access.lua`: a value written where the Lua will not read it is
inert, and one the Lua reads where the law does not reach is a fine.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[1] / "infra"
sys.path.insert(0, str(INFRA))

from cycle_rules import (  # noqa: E402
    FOOTPATH_G12A,
    FOOTPATH_PLATE,
    footpath_overlay,
    is_cycle_infrastructure,
    plate_admits,
)

SQUARE = {"highway": "pedestrian", "traffic_sign": "NL:G7", "moped": "yes"}


class TestReadingThePlate:
    @pytest.mark.parametrize(
        "texts",
        [
            ["brom-fietsen toegestaan"],
            ["(brom)fietsen toegestaan"],
            ["brom - fietsen toegestaan"],
            ["(brom)fietsers toegestaan"],
            ["fietsen, brom- en snorfietsen toegestaan"],
        ],
    )
    def test_the_forms_the_register_writes_admit_the_bromfiets(self, texts) -> None:
        assert plate_admits(texts)

    @pytest.mark.parametrize(
        "texts",
        [
            [],
            [""],
            ["fietsen toegestaan"],
            ["fietsen toegestaan brom- en snorfietsen niet"],
            ["dus niet brommen"],
            ["(brom)fietsen toegestaan", "laden en lossen ma t/m za 06:00 - 11:00 h"],
            ["onleesbaar"],
        ],
    )
    def test_anything_else_admits_nobody(self, texts) -> None:
        """A second plate can carry hours this graph cannot hold, and a plate
        nobody could read says nothing."""
        assert not plate_admits(texts)


class TestWhatTheOverlayWritesOnAVoetpad:
    def test_both_sources_open_it(self) -> None:
        assert footpath_overlay(SQUARE, None, True) == FOOTPATH_PLATE

    def test_an_unsigned_voetpad_needs_the_register_plate_and_the_permission(self) -> None:
        tags = {"highway": "pedestrian", "moped": "yes"}
        assert footpath_overlay(tags, None, True) == FOOTPATH_PLATE
        assert footpath_overlay(tags, None, False) is None

    def test_the_register_alone_opens_nothing(self) -> None:
        tags = {"highway": "pedestrian", "traffic_sign": "NL:G7"}
        assert footpath_overlay(tags, None, True) is None

    def test_the_map_alone_opens_nothing(self) -> None:
        assert footpath_overlay(SQUARE, None, False) is None

    def test_a_refusal_on_the_way_keeps_it_closed(self) -> None:
        assert footpath_overlay({**SQUARE, "moped": "no"}, None, True) is None

    def test_without_a_mapped_g7_the_plate_has_nothing_to_qualify(self) -> None:
        tags = {**SQUARE, "traffic_sign": "NL:C1"}
        assert footpath_overlay(tags, None, True) is None

    def test_a_confirmed_g12a_makes_the_way_a_fiets_bromfietspad(self) -> None:
        tags = {"highway": "pedestrian", "traffic_sign": "NL:G12a"}
        assert footpath_overlay(tags, "G12a", False) == FOOTPATH_G12A

    def test_an_unconfirmed_g12a_does_not(self) -> None:
        tags = {"highway": "footway", "traffic_sign": "NL:G12a"}
        assert footpath_overlay(tags, None, False) is None
        assert footpath_overlay(tags, "G11", False) is None

    def test_nothing_is_written_off_a_voetpad(self) -> None:
        assert footpath_overlay({**SQUARE, "highway": "steps"}, "G12a", True) is None

    def test_the_g12a_value_is_what_makes_it_cycle_infrastructure(self) -> None:
        """Mirrors M.is_cycle_infrastructure in access.lua."""
        tags = {"highway": "pedestrian", "traffic_sign": "NL:G12a"}
        assert not is_cycle_infrastructure(tags)
        assert is_cycle_infrastructure({**tags, "amgraph:bromfiets": FOOTPATH_G12A})
        assert not is_cycle_infrastructure({**tags, "amgraph:bromfiets": FOOTPATH_PLATE})


class TestTheOnderbordGovernsTheVoetpadBehindIt:
    def _paths(self):
        from official_access import Paths

        paths = Paths({}, {})
        permitted = {"highway": "pedestrian", "moped": "yes"}
        paths.voetpaden = {
            1: (permitted, (10, 11), 20.0),
            2: (permitted, (11, 12), 30.0),
            3: ({"highway": "pedestrian"}, (12, 13), 20.0),
            4: ({"highway": "pedestrian", "moped": "yes"}, (11, 14), 500.0),
        }
        paths.footpath = {1: FOOTPATH_PLATE}
        paths.speed = {1: "15"}
        paths.spread()
        return paths

    def test_a_connected_permitted_voetpad_is_opened_with_the_limit(self) -> None:
        paths = self._paths()
        assert paths.footpath[2] == FOOTPATH_PLATE
        assert paths.speed[2] == "15"

    def test_a_way_the_mapper_does_not_permit_is_not(self) -> None:
        assert 3 not in self._paths().footpath

    def test_it_stops_at_the_distance_cap(self) -> None:
        assert 4 not in self._paths().footpath
