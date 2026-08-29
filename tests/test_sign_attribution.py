"""The pure Dutch cycle-path rules: signs, who may use a path, and direction.

Everything in infra/cycle_rules.py, which is the half of the overlay writer
that is a statement about law rather than about geometry. It needs no extract,
no shapefile and no projection library, so it runs in the fast gate.

These are pure functions, so they can be pinned without an extract or a graph.
The one they exist to protect is `path_classes`: it decides which class may use
a path, and it has to give the same answer as the cycle branch of
`valhalla/lua/access.lua`. If the two drift, the writer indexes a path
as usable that the graph refuses, and the mandatory-use gating built on that
index starts keeping carriageways closed for a sidepath nobody may ride on.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[1] / "infra"
sys.path.insert(0, str(INFRA))

from cycle_rules import (  # noqa: E402
    OPENS_FOR_SNORFIETS,
    closes_class,
    cycle_sign_of,
    is_cycle_infrastructure,
    osm_cycle_sign,
    path_classes,
)


class TestWhichRegisterRecordsCount:
    def test_a_placed_cycle_sign_is_read(self) -> None:
        assert cycle_sign_of({"status": "PLACED", "rvvCode": "G12a"}) == "G12a"

    @pytest.mark.parametrize("status", ["PLANNED", "REMOVED", "UNKNOWN", None])
    def test_only_a_placed_sign_describes_the_road_as_it_is(self, status) -> None:
        """A planned sign is somebody's intention, not a path a rider may use."""
        assert cycle_sign_of({"status": status, "rvvCode": "G12a"}) is None

    def test_a_sign_that_is_not_about_cycle_paths_is_ignored(self) -> None:
        assert cycle_sign_of({"status": "PLACED", "rvvCode": "A1"}) is None


class TestReadingTheMappersSign:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("NL:G12a", "G12a"),
            ("G11", "G11"),
            ("NL:G13", "G13"),
            ("NL:G12a;NL:OB503", "G12a"),
            ("NL:C1", None),
            ("", None),
        ],
    )
    def test_the_sign_is_found_in_the_forms_osm_writes_it(self, value, expected) -> None:
        assert osm_cycle_sign({"traffic_sign": value}) == expected

    def test_a_directional_sign_is_read_too(self) -> None:
        assert osm_cycle_sign({"traffic_sign:forward": "NL:G11"}) == "G11"


class TestWhatCountsAsCycleInfrastructure:
    def test_a_cycleway_always_does(self) -> None:
        assert is_cycle_infrastructure({"highway": "cycleway"})

    def test_a_bare_path_does_not(self) -> None:
        """Otherwise a track across a field is indexed as a usable sidepath."""
        assert not is_cycle_infrastructure({"highway": "path"})

    def test_a_designated_or_signed_path_does(self) -> None:
        assert is_cycle_infrastructure({"highway": "path", "bicycle": "designated"})
        assert is_cycle_infrastructure({"highway": "path", "traffic_sign": "NL:G12a"})

    def test_a_roadway_never_does(self) -> None:
        assert not is_cycle_infrastructure({"highway": "residential"})


class TestWhoMayUseThePath:
    def test_a_g12a_admits_both_two_wheeled_classes(self) -> None:
        assert path_classes({"traffic_sign": "NL:G12a"}, None) == (True, True)

    def test_a_g11_admits_the_snorfiets_alone(self) -> None:
        assert path_classes({"traffic_sign": "NL:G11"}, None) == (True, False)

    def test_a_g13_admits_neither(self) -> None:
        """Optional, so never using it can only lengthen a route."""
        assert path_classes({"traffic_sign": "NL:G13"}, None) == (False, False)

    def test_an_unsigned_path_admits_neither(self) -> None:
        assert path_classes({}, None) == (False, False)

    def test_the_register_opens_a_g12a_for_the_snorfiets_only(self) -> None:
        assert path_classes({}, OPENS_FOR_SNORFIETS) == (True, False)

    def test_the_register_never_opens_a_g11(self) -> None:
        """Art. 5 lid 8 can hang an onderbord on a G11 and the register's
        onderbord coverage is poor, so a G11 cannot be read at face value."""
        assert path_classes({}, "G11") == (False, False)

    def test_the_register_never_opens_a_g13(self) -> None:
        assert path_classes({}, "G13") == (False, False)

    def test_the_mappers_sign_beats_the_register(self) -> None:
        assert path_classes({"traffic_sign": "NL:G13"}, "G12a") == (False, False)

    def test_an_explicit_refusal_beats_the_register(self) -> None:
        assert path_classes({"mofa": "no"}, "G12a") == (False, False)

    def test_an_explicit_permission_is_honoured(self) -> None:
        assert path_classes({"moped": "designated"}, None) == (False, True)

    def test_use_sidepath_on_a_path_is_a_refusal_not_a_permission(self) -> None:
        assert path_classes({"traffic_sign": "NL:G12a", "moped": "use_sidepath"}, None) == (
            True,
            False,
        )

    def test_a_blanket_ban_leaves_only_a_class_specific_permission(self) -> None:
        assert path_classes({"access": "no"}, "G12a") == (False, False)
        assert path_classes({"access": "no", "mofa": "yes"}, None) == (True, False)

    def test_a_bicycle_refusal_reaches_the_snorfiets(self) -> None:
        """RVV art. 2b: it follows the bicycle rules."""
        assert path_classes({"traffic_sign": "NL:G12a", "bicycle": "no"}, None) == (False, True)


class TestReadingADirectionalWkdRefusal:
    """`closes_class`, which reads WKD's per-direction verdicts.

    A one-way section marks its unused direction N for every class, which is
    not a class prohibition. AUTO is the reference that tells the two apart.
    """

    def test_the_unused_direction_of_a_one_way_carriageway_is_not_a_refusal(self) -> None:
        assert not closes_class("J", "N", "J", "N")

    def test_a_refusal_in_the_travelled_direction_closes_a_one_way_carriageway(self) -> None:
        assert closes_class("N", "N", "J", "N")

    def test_one_refused_direction_closes_a_two_way_carriageway(self) -> None:
        assert closes_class("J", "N", "J", "J")

    def test_a_directional_refusal_on_a_cycle_section_cannot_be_guessed(self) -> None:
        assert closes_class("J", "N", "N", "N")

    def test_a_cycle_section_open_in_both_directions_stays_open(self) -> None:
        assert not closes_class("J", "J", "N", "N")
