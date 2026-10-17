"""Find the bus-lane roads a rider can ride without ever crossing the bus lane.

NL-ACC-11. RVV art. 81 reserves a busstrook and nothing beside it, so the
general lane next to one is ordinary rijbaan. Reaching or leaving that lane
across the bus lane is another matter: art. 76 lid 1 forbids crossing a solid
line, and no national dataset says which bus-lane lines are solid. A turn
across the lane therefore cannot be shown to be lawful.

So a way is reopened only where no such turn exists: no road the rider could
turn into or out of joins it on the side of a closed lane. That is a fact
about the junctions, which access.lua cannot see because Valhalla hands it one
way's tags at a time. This pass works it out from the geometry and writes
`amgraph:bus_lane_turns=none` onto the ways it clears. access.lua reopens a
bus-lane way only when the tag is there, and the injector strips any
`amgraph:` tag a mapper wrote, so the tag means this pass and nothing else.

Turn restrictions would be the finer tool and are deliberately not used.
Valhalla 3.8.3 (`CreateSimpleTurnRestriction`, mjolnir/graphbuilder.cc) blocks
only the first edge whose way id matches the restriction's `to` way, so where a
side street runs through the junction it can block the lawful half of it and
leave the turn across the bus lane open.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping

import osmium

TAG = "amgraph:bus_lane_turns"

ALLOW = frozenset({"yes", "designated", "permissive"})

#: Ways no class here can ever be routed onto, so a junction with one is no
#: turn. Mirrors NEVER and the outright prohibitions in access.lua; a value
#: missing here only makes the pass stricter.
NO_TURN_INTO = frozenset(
    {
        "footway",
        "pedestrian",
        "steps",
        "bridleway",
        "corridor",
        "elevator",
        "platform",
        "via_ferrata",
        "busway",
        "bus_guideway",
        "construction",
        "proposed",
        "raceway",
        "motorway",
        "motorway_link",
    }
)

#: How far from dead ahead, in degrees, a way at the end of the bus-lane way
#: may run and still be read as the same road carrying on rather than a turn.
CONTINUATION_DEGREES = 25.0

#: A side street this close to the road's own line cannot be put on a side.
AMBIGUOUS_DEGREES = 5.0


def closed_lane_sides(tags: Mapping[str, str]) -> frozenset[str] | None:
    """Which sides of the road the closed lanes lie on, or None if unreadable.

    Only a forward one-way is read, because the lanes of `oneway=-1` and of a
    two-way road cannot be put in travel order without guessing. Lanes are
    counted left to right in the way's direction.
    """
    if tags.get("oneway") not in {"yes", "true", "1"} and tags.get("junction") not in {
        "roundabout",
        "circular",
    }:
        return None
    if ("bus:lanes" in tags) == ("psv:lanes" in tags):
        return None
    reserved = (tags.get("bus:lanes") or tags["psv:lanes"]).split("|")
    general = [tags[key].split("|") for key in ("access:lanes", "vehicle:lanes") if key in tags]
    if not general or any(len(lanes) != len(reserved) for lanes in general):
        return None

    closed = [
        lane for lane in range(len(reserved)) if not all(lanes[lane] in ALLOW for lanes in general)
    ]
    if not closed or len(closed) == len(reserved):
        return None
    sides: set[str] = set()
    for lane in closed:
        # A closed lane in the middle has open lanes on both sides of it, so a
        # turn either way from the far side would cross it.
        if lane < len(reserved) - 1:
            sides.add("left")
        if lane > 0:
            sides.add("right")
    return frozenset(sides)


Point = tuple[float, float]


def _vector(a: Point, b: Point) -> tuple[float, float]:
    """East and north components from `a` to `b`, in scaled degrees."""
    return ((b[1] - a[1]) * math.cos(math.radians(a[0])), b[0] - a[0])


def _angle(forward: tuple[float, float], other: tuple[float, float]) -> tuple[float, float]:
    """Unsigned angle between two vectors, and the cross product's sign source."""
    cross = forward[0] * other[1] - forward[1] * other[0]
    dot = forward[0] * other[0] + forward[1] * other[1]
    return math.degrees(math.atan2(abs(cross), dot)), cross


def crosses_bus_lane(
    points: list[Point],
    node_ids: list[int],
    sides: frozenset[str],
    joins: Mapping[int, Iterable[Point]],
) -> bool:
    """Does any road join on a closed lane's side, so that a turn would cross it?

    `joins` maps a node of this way to the next point along every other way
    that leaves that node, one entry per direction a rider could take. At the
    first and last node the one way most nearly straight on, within
    CONTINUATION_DEGREES, is the road carrying on; everything else is a turn.
    """
    last = len(node_ids) - 1
    for index, node in enumerate(node_ids):
        here = points[index]
        if index < last:
            forward = _vector(here, points[index + 1])
        else:
            forward = _vector(points[index - 1], here)
        others = list(joins.get(node, ()))

        continuation = None
        if index in (0, last):
            ahead = forward if index == last else (-forward[0], -forward[1])
            best = None
            for position, point in enumerate(others):
                angle, _ = _angle(ahead, _vector(here, point))
                if angle <= CONTINUATION_DEGREES and (best is None or angle < best):
                    best, continuation = angle, position

        for position, point in enumerate(others):
            if position == continuation:
                continue
            angle, cross = _angle(forward, _vector(here, point))
            if angle < AMBIGUOUS_DEGREES or angle > 180 - AMBIGUOUS_DEGREES:
                return True
            if ("left" if cross > 0 else "right") in sides:
                return True
    return False


class _Candidates(osmium.SimpleHandler):
    def __init__(self) -> None:
        super().__init__()
        self.ways: dict[int, tuple[frozenset[str], list[int], list[Point]]] = {}

    def way(self, w) -> None:
        if w.tags.get("highway") is None:
            return
        sides = closed_lane_sides(dict(w.tags))
        if sides is None:
            return
        try:
            points = [(n.lat, n.lon) for n in w.nodes]
        except osmium.InvalidLocationError:
            return
        self.ways[w.id] = (sides, [n.ref for n in w.nodes], points)


class _Joins(osmium.SimpleHandler):
    def __init__(self, nodes: set[int]) -> None:
        super().__init__()
        self.nodes = nodes
        self.joins: dict[int, list[tuple[int, Point]]] = defaultdict(list)
        self.broken: set[int] = set()

    def way(self, w) -> None:
        highway = w.tags.get("highway")
        if highway is None or highway in NO_TURN_INTO:
            return
        refs = [n.ref for n in w.nodes]
        for index, ref in enumerate(refs):
            if ref not in self.nodes:
                continue
            for neighbour in (index - 1, index + 1):
                if 0 <= neighbour < len(refs):
                    try:
                        node = w.nodes[neighbour]
                        self.joins[ref].append((w.id, (node.lat, node.lon)))
                    except osmium.InvalidLocationError:
                        # A join whose direction cannot be read cannot be put on
                        # a side, so the way it touches is not cleared.
                        self.broken.add(ref)


def clear_bus_lane_ways(extract: str) -> set[int]:
    """The bus-lane ways no turn across the bus lane can reach or leave."""
    candidates = _Candidates()
    candidates.apply_file(extract, locations=True)
    nodes = {node for _, ids, _ in candidates.ways.values() for node in ids}
    joins = _Joins(nodes)
    joins.apply_file(extract, locations=True)

    clear = set()
    for way_id, (sides, ids, points) in candidates.ways.items():
        if any(node in joins.broken for node in ids):
            continue
        others = {
            node: [point for owner, point in joins.joins.get(node, []) if owner != way_id]
            for node in ids
        }
        if not crosses_bus_lane(points, ids, sides, others):
            clear.add(way_id)
    return clear
