"""NL-ACC-12 and the art. 5 lid 8 exceptions, as pure functions.

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

from amgraph_rules.countries.nl import ART5_LID8_EXEMPT_ROADS  # noqa: E402
from cycle_rules import (  # noqa: E402
    FOOTPATH_G12A,
    FOOTPATH_PLATE,
    footpath_overlay,
    is_cycle_infrastructure,
    on_exempt_road,
    plate_admits,
    plate_refuses_snorfiets,
)

SQUARE = {"highway": "pedestrian", "traffic_sign": "NL:G7", "moped": "yes", "mofa": "yes"}


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
    def test_the_forms_the_register_writes_admit_both_two_wheelers(self, texts) -> None:
        """A snorfiets is a bromfiets (NL-DEF-01), so a plate admitting
        bromfietsen admits it too."""
        assert plate_admits(texts) == (True, True)

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
        assert plate_admits(texts) == (False, False)

    def test_a_snorfiets_refusal_is_recognised(self) -> None:
        assert plate_refuses_snorfiets(["snorfietsen niet toegestaan"])
        assert plate_refuses_snorfiets(["fietsen toegestaan", "snorfietsers verboden"])
        assert not plate_refuses_snorfiets(["brom-fietsen toegestaan"])
        assert not plate_refuses_snorfiets([])


class TestWhatTheOverlayWritesOnAVoetpad:
    def test_both_sources_open_both_classes(self) -> None:
        assert footpath_overlay(SQUARE, None, (True, True)) == (FOOTPATH_PLATE, FOOTPATH_PLATE)

    def test_an_unsigned_voetpad_needs_the_register_plate_and_the_permission(self) -> None:
        tags = {"highway": "pedestrian", "moped": "yes", "mofa": "yes"}
        assert footpath_overlay(tags, None, (True, True)) == (FOOTPATH_PLATE, FOOTPATH_PLATE)
        assert footpath_overlay(tags, None, None) == (None, None)

    def test_the_register_alone_opens_nothing(self) -> None:
        tags = {"highway": "pedestrian", "traffic_sign": "NL:G7"}
        assert footpath_overlay(tags, None, (True, True)) == (None, None)

    def test_the_map_alone_opens_nothing(self) -> None:
        assert footpath_overlay(SQUARE, None, None) == (None, None)

    def test_each_class_needs_its_own_permission_on_the_way(self) -> None:
        tags = {**SQUARE, "mofa": "no"}
        assert footpath_overlay(tags, None, (True, True)) == (None, FOOTPATH_PLATE)

    def test_without_a_mapped_g7_the_plate_has_nothing_to_qualify(self) -> None:
        tags = {**SQUARE, "traffic_sign": "NL:C1"}
        assert footpath_overlay(tags, None, (True, True)) == (None, None)

    def test_a_confirmed_g12a_makes_the_way_a_fiets_bromfietspad(self) -> None:
        tags = {"highway": "pedestrian", "traffic_sign": "NL:G12a"}
        assert footpath_overlay(tags, "G12a", None) == (FOOTPATH_G12A, FOOTPATH_G12A)

    def test_an_unconfirmed_g12a_does_not(self) -> None:
        tags = {"highway": "footway", "traffic_sign": "NL:G12a"}
        assert footpath_overlay(tags, None, None) == (None, None)
        assert footpath_overlay(tags, "G11", None) == (None, None)

    def test_nothing_is_written_off_a_voetpad(self) -> None:
        assert footpath_overlay({**SQUARE, "highway": "steps"}, "G12a", (True, True)) == (
            None,
            None,
        )

    def test_the_g12a_value_is_what_makes_it_cycle_infrastructure(self) -> None:
        """Mirrors M.is_cycle_infrastructure in access.lua."""
        tags = {"highway": "pedestrian", "traffic_sign": "NL:G12a"}
        assert not is_cycle_infrastructure(tags)
        assert is_cycle_infrastructure({**tags, "amgraph:bromfiets": FOOTPATH_G12A})
        assert not is_cycle_infrastructure({**tags, "amgraph:bromfiets": FOOTPATH_PLATE})


class TestTheArt5Lid8Exceptions:
    def test_de_ruijterkade_is_excepted(self) -> None:
        assert on_exempt_road("De Ruijterkade", (52.3813, 4.8970), ART5_LID8_EXEMPT_ROADS)

    def test_kattenburgerstraat_was_brought_under_the_measure_in_2023(self) -> None:
        assert not on_exempt_road("Kattenburgerstraat", (52.3745, 4.9210), ART5_LID8_EXEMPT_ROADS)

    def test_prins_hendrikkade_only_east_of_the_station(self) -> None:
        roads = ART5_LID8_EXEMPT_ROADS
        assert on_exempt_road("Prins Hendrikkade", (52.3725, 4.9080), roads)
        assert not on_exempt_road("Prins Hendrikkade", (52.3769, 4.8990), roads)

    def test_a_name_outside_amsterdam_is_not_excepted(self) -> None:
        assert not on_exempt_road("Nassaukade", (52.0900, 5.1200), ART5_LID8_EXEMPT_ROADS)

    def test_utrechts_measure_reaches_only_the_roads_it_names(self) -> None:
        from official_access import lid8_reaches

        assert lid8_reaches("Vleutenseweg", (52.0920, 5.1000))
        assert not lid8_reaches("Venuslaan", (52.0905, 5.1460))
        assert lid8_reaches(None, (52.0905, 5.1460))
        assert lid8_reaches("Damrak", (52.3750, 4.8960))

    def test_the_onderbord_written_into_the_mapped_sign_is_read(self) -> None:
        assert plate_refuses_snorfiets(['NL:G11,"snorfietsen niet toegestaan"'])
        assert not plate_refuses_snorfiets(["NL:G11"])

    def test_an_unlisted_road_is_not_excepted(self) -> None:
        assert not on_exempt_road("Damrak", (52.3750, 4.8960), ART5_LID8_EXEMPT_ROADS)
        assert not on_exempt_road(None, (52.3813, 4.8970), ART5_LID8_EXEMPT_ROADS)


class TestTheOnderbordGovernsTheVoetpadBehindIt:
    def _paths(self):
        from official_access import Paths

        paths = Paths({}, None, {}, {})
        permitted = {"highway": "pedestrian", "moped": "yes", "mofa": "yes"}
        paths.voetpaden = {
            1: (permitted, (10, 11), 20.0),
            2: (permitted, (11, 12), 30.0),
            3: ({"highway": "pedestrian"}, (12, 13), 20.0),
            4: ({"highway": "pedestrian", "moped": "yes"}, (11, 14), 500.0),
        }
        paths.footpath = {1: (FOOTPATH_PLATE, FOOTPATH_PLATE)}
        paths.speed = {1: "15"}
        paths.spread()
        return paths

    def test_a_connected_permitted_voetpad_is_opened_with_the_limit(self) -> None:
        paths = self._paths()
        assert paths.footpath[2] == (FOOTPATH_PLATE, FOOTPATH_PLATE)
        assert paths.speed[2] == "15"

    def test_a_way_the_mapper_does_not_permit_is_not(self) -> None:
        assert 3 not in self._paths().footpath

    def test_it_stops_at_the_distance_cap(self) -> None:
        assert 4 not in self._paths().footpath
