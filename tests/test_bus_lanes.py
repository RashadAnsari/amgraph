"""NL-ACC-11: a bus-lane road is reopened only where no turn crosses the bus lane.

RVV art. 76 lid 1 forbids crossing a solid line, and no dataset says which
bus-lane lines are solid, so a road joining on a bus lane's side keeps the way
closed. These pin the geometry that decides which side a road joins on.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[1] / "infra"
sys.path.insert(0, str(INFRA))

from bus_lanes import closed_lane_sides, crosses_bus_lane  # noqa: E402

BUS_RIGHT = {
    "highway": "secondary",
    "oneway": "yes",
    "access:lanes": "yes|no",
    "bus:lanes": "|designated",
}

# A road running due north along longitude 5.0, three nodes 100 m apart.
NODES = [1, 2, 3]
POINTS = [(52.000, 5.0), (52.001, 5.0), (52.002, 5.0)]
EAST = (52.001, 5.001)
WEST = (52.001, 4.999)
STRAIGHT_ON = (52.003, 5.0)
STRAIGHT_BEHIND = (51.999, 5.0)


def test_a_bus_lane_on_the_right_is_crossed_by_a_right_turn() -> None:
    assert closed_lane_sides(BUS_RIGHT) == {"right"}


def test_a_bus_lane_on_the_left_is_crossed_by_a_left_turn() -> None:
    tags = {**BUS_RIGHT, "access:lanes": "no|yes", "bus:lanes": "designated|"}
    assert closed_lane_sides(tags) == {"left"}


def test_a_bus_lane_between_open_lanes_is_crossed_both_ways() -> None:
    tags = {**BUS_RIGHT, "access:lanes": "yes|no|yes", "bus:lanes": "|designated|"}
    assert closed_lane_sides(tags) == {"left", "right"}


@pytest.mark.parametrize(
    "change",
    [
        {"oneway": "-1"},
        {"oneway": "no"},
        {"oneway": None},
        {"access:lanes": "yes|yes|no"},
        {"access:lanes": "no|no"},
        {"psv:lanes": "|designated"},
        {"bus:lanes": None},
    ],
    ids=["reversed", "two-way", "no-oneway", "count-mismatch", "all-closed", "both-keys", "no-bus"],
)
def test_lanes_that_cannot_be_put_in_travel_order_are_not_read(change) -> None:
    tags = {**BUS_RIGHT, **change}
    tags = {key: value for key, value in tags.items() if value is not None}
    assert closed_lane_sides(tags) is None


def test_a_road_with_nothing_joining_is_clear() -> None:
    assert not crosses_bus_lane(POINTS, NODES, frozenset({"right"}), {})


def test_a_side_street_on_the_bus_lane_side_blocks_it() -> None:
    assert crosses_bus_lane(POINTS, NODES, frozenset({"right"}), {2: [EAST]})


def test_a_side_street_on_the_other_side_leaves_it_clear() -> None:
    assert not crosses_bus_lane(POINTS, NODES, frozenset({"right"}), {2: [WEST]})


def test_a_left_bus_lane_is_blocked_by_a_road_on_the_left() -> None:
    assert crosses_bus_lane(POINTS, NODES, frozenset({"left"}), {2: [WEST]})


def test_the_road_carrying_on_at_either_end_is_no_turn() -> None:
    joins = {1: [STRAIGHT_BEHIND], 3: [STRAIGHT_ON]}
    assert not crosses_bus_lane(POINTS, NODES, frozenset({"right"}), joins)


def test_a_turn_at_the_last_node_counts() -> None:
    joins = {3: [STRAIGHT_ON, (52.002, 5.001)]}
    assert crosses_bus_lane(POINTS, NODES, frozenset({"right"}), joins)


def test_joining_from_the_bus_lane_side_at_the_first_node_counts() -> None:
    joins = {1: [STRAIGHT_BEHIND, (52.000, 5.001)]}
    assert crosses_bus_lane(POINTS, NODES, frozenset({"right"}), joins)


def test_only_one_way_at_an_end_can_be_the_road_carrying_on() -> None:
    # A fork just right of straight on is still a turn across the bus lane.
    slight_right = (52.003, 5.0002)
    joins = {3: [STRAIGHT_ON, slight_right]}
    assert crosses_bus_lane(POINTS, NODES, frozenset({"right"}), joins)


def test_a_road_merging_mid_way_at_a_shallow_angle_still_counts() -> None:
    joins = {2: [(51.9995, 5.0002)]}
    assert crosses_bus_lane(POINTS, NODES, frozenset({"right"}), joins)


def test_a_road_too_close_to_the_line_to_put_on_a_side_blocks_it() -> None:
    joins = {2: [(52.0015, 5.0000001)]}
    assert crosses_bus_lane(POINTS, NODES, frozenset({"left"}), joins)
