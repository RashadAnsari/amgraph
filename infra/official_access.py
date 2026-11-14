"""Turn the road authority's access refusals into an overlay for the graph.

OpenStreetMap describes the Netherlands; Rijkswaterstaat's Wegkenmerkendatabase
adds official access evidence. Its Verkeerstypen product carries, per NWB road
section and per direction, whether a bromfiets may be there at all — derived by
NDW from the national traffic-sign register, parallel-path detection and the
built-up-area topography. That is the mandatory-use obligation, which cannot be
modelled from OSM tags because OSM states it on only a fraction of the roads it
binds, already resolved by the people who put up the signs.

NDW documents that the traffic-sign-to-NWB coupling is often wrong, including
mandatory cycle-path signs attached to the ordinary carriageway, and the
geometric match from that network onto OSM adds another source of error. So a
refusal is cheap to accept and an affirmation is not, and this writer emits
these values:

`no`     — the class may not be here. Safe by construction: wrong costs a detour.

`on_roadway` — this carriageway carries a mandatory-use closure, and a path was
    found running beside it that the rules refuse the class. That is a
    contradiction, not caution: the rider is being sent off the road and
    refused the path they are being sent to. RVV art. 6 lid 2 settles it —
    "Zij gebruiken de rijbaan indien een fiets/bromfietspad ontbreekt" — so the
    closure is lifted and the roadway, which the statute makes mandatory here,
    stays open. Where *no* path runs
    alongside, the refusal was never about mandatory use and stays `no`.

`footpath_onderbord` and `footpath_g12a` — NL-ACC-12, on a footway or
    pedestrian way only. The first says a register G7 beside the way carries an
    onderbord admitting bromfietsen and the mapper permits the class too; the
    second that the register confirms the G12a the mapper put on it. Each needs
    both sources. Where the register's A1 beside such a way is lower than its
    maxspeed, or the way has none, the A1's figure is written as maxspeed.

**It applies to the bromfiets only.** WKD models it as BRMFTS. A brommobiel is
*not* covered: RVV art. 6 lid 3 puts it on the rijbaan, so a BRMFTS closure
caused by a mandatory sidepath does not reach it, and applying one would shut
roads it may lawfully use. It keeps the tag-derived rules.

The join is geometric. NWB and OSM are independent networks with no shared
identifier, so a section is matched to a way by running close beside it on the
same heading for most of its length — the same test used elsewhere in this
repo, here comparing two centrelines rather than guessing at a sidepath.

    make infra-official-access

Writes a way-id keyed overlay for access.lua to read at graph build time.
"""

from __future__ import annotations

import json
import math
import os
import sys
from collections import Counter, defaultdict
from itertools import pairwise
from pathlib import Path

import osmium
import shapefile
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, shape

from artifacts import replace_atomically
from bus_lanes import TAG as BUS_LANE_TAG
from bus_lanes import clear_bus_lane_ways
from cycle_rules import (
    FOOTPATH,
    FOOTPATH_PLATE,
    closes_class,
    cycle_sign_of,
    footpath_overlay,
    is_cycle_infrastructure,
    mapped_signs,
    path_admits,
    plate_admits,
    stated_access,
)
from restrictions import conservative_restriction_tags

#: How near two centrelines must run to be the same road. NWB and OSM are
#: surveyed independently, so a few metres of disagreement is normal; 20 m
#: absorbs that without reaching the parallel cycleway beside a carriageway.
MATCH_METRES = 20.0

#: Headings within this count as the same direction. Loose enough for a curve
#: sampled at nodes, tight enough to reject a road that merely crosses.
ANGLE_DEGREES = 30.0

#: Fraction of a way's samples that must find the same section. A way that only
#: brushes a section near a junction is not that section.
COVERAGE = 0.6

#: Grid cell for the spatial index, in degrees. ~250 m of latitude.
CELL = 0.003

#: Ways too short to judge. Junction stubs inherit their neighbours' character
#: and matching them reliably is not possible.
MIN_LENGTH_METRES = 30.0

#: OSM highway values a Dutch AM-class vehicle could plausibly be routed along.
#: Anything else cannot be closed because it was never open.
ROUTABLE = {
    "residential",
    "unclassified",
    "tertiary",
    "tertiary_link",
    "secondary",
    "secondary_link",
    "primary",
    "primary_link",
    "living_street",
    "road",
    "service",
    "cycleway",
    "path",
    "track",
}

#: OSM ways that are cycle infrastructure rather than carriageway.
#:
#: A section is only ever matched to a way of its own kind, and that is not a
#: refinement — it is what makes the overlay safe. A bromfietspad runs a few
#: metres from its carriageway on the same heading, so proximity alone cannot
#: tell them apart, and the carriageway's "no bromfiets" verdict, which exists
#: *because* the path is compulsory, would land on the path and close the very
#: road the rule sends riders onto.
CYCLE_LIKE = {"cycleway", "path", "footway", "bridleway", "steps", "track"}

#: How near a register sign must stand to be describing this path. NDW warns
#: that a sign's coordinates sometimes mark the photographer rather than the
#: post, so this is looser than a survey would need.
SIGN_METRES = 20.0

#: How far off a carriageway a parallel path may lie and still be the sidepath
#: that carriageway's mandatory-use verdict refers to. Wide enough for a berm
#: and a parking strip, narrow enough not to reach the next street.
SIDEPATH_METRES = 25.0

#: How far a confirmed G7 onderbord is carried over the voetpad behind it. A
#: station square or a ferry approach, not a town centre's pedestrian network.
SPREAD_METRES = 150.0


#: Register signs whose onderborden or value the rules read, beside the cycle
#: signs: the G7 for NL-ACC-12, and the A1 for the limit on a voetpad it opens.
PLATED = {"G7", "A1"}


def load_signs(path: Path):
    """The road authority's signs, indexed by grid cell.

    Two indexes: the cycle signs as codes, and the signs in PLATED with the
    text of their onderborden and the value they show.
    """
    grid: dict[tuple[int, int], list] = defaultdict(list)
    plated: dict[tuple[int, int], list] = defaultdict(list)
    counts = Counter()
    with path.open() as fh:
        document = json.load(fh)
    for feature in document.get("features", ()):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point" or properties.get("status") != "PLACED":
            continue
        lon, lat = geometry["coordinates"][0], geometry["coordinates"][1]
        cell = (int(lat / CELL), int(lon / CELL))
        code = cycle_sign_of(properties)
        if code is not None:
            counts[code] += 1
            grid[cell].append((lat, lon, code))
        if properties.get("rvvCode") in PLATED:
            texts = [plate.get("text") or "" for plate in properties.get("textSigns") or ()]
            plated[cell].append(
                (lat, lon, properties["rvvCode"], texts, properties.get("blackCode"))
            )
    return grid, counts, plated


def _speed(value) -> int | None:
    """A km/h figure from an OSM maxspeed or a register A1 value, if plain."""
    text = str(value or "").strip()
    return int(text) if text.isdigit() else None


_to_wgs84 = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    dy = (b[0] - a[0]) * 111_320
    dx = (b[1] - a[1]) * 111_320 * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot(dx, dy)


def bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    dy = b[0] - a[0]
    dx = (b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2))
    return math.degrees(math.atan2(dx, dy)) % 180.0  # undirected


def aligned(one: float, two: float) -> bool:
    gap = abs(one - two) % 180.0
    return min(gap, 180.0 - gap) <= ANGLE_DEGREES


def load_closures(path: Path):
    """WKD sections that decide something, in WGS84.

    Returns the refusals only. Positive WKD answers are deliberately discarded.
    """
    reader = shapefile.Reader(str(path))
    names = [f[0] for f in reader.fields[1:]]
    idx = {name: i for i, name in enumerate(names)}

    sections: list[tuple[list[tuple[float, float]], bool, bool]] = []
    counts = Counter()

    # Streamed rather than reader.records() + reader.shapes(), which would pull
    # 1.5 million records and their geometry into memory at once.
    for sr in reader.iterShapeRecords():
        rec, shp = sr.record, sr.shape
        counts["total"] += 1

        # A one-way section marks its unused direction N for every class. Use
        # AUTO to distinguish that from a class refusal on a carriageway. On a
        # cycle-like section there is no automobile direction to disambiguate,
        # so any refusal closes the complete matched way.
        auto_head = rec[idx["AUTO_H"]]
        auto_tail = rec[idx["AUTO_T"]]
        brom = closes_class(rec[idx["BRMFTS_H"]], rec[idx["BRMFTS_T"]], auto_head, auto_tail)
        if len(shp.points) < 2:
            continue

        # Whether this is a carriageway, so it is only ever matched to one.
        is_road = auto_head == "J" or auto_tail == "J"

        points = [(lat, lon) for lon, lat in (_to_wgs84.transform(x, y) for x, y in shp.points)]

        if brom:
            sections.append((points, brom, is_road))
            counts["carriageway" if is_road else "cycle-ish"] += 1
            counts["closing"] += 1

    grid: dict[tuple[int, int], list] = defaultdict(list)
    for points, brom, is_road in sections:
        for a, b in pairwise(points):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            grid[(int(mid[0] / CELL), int(mid[1] / CELL))].append(
                (mid, bearing(a, b), brom, is_road)
            )

    counts["segments"] = sum(len(v) for v in grid.values())
    return grid, counts


def _near(index, points, radius: float):
    """Every entry of a sign index within `radius` of the way, nearest first.

    Measured from each node and segment midpoint, so a short way and a sign at
    one of its ends still meet.
    """
    probes = list(points) + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in pairwise(points)]
    best: dict[tuple[float, float], tuple[float, tuple]] = {}
    for probe in probes:
        cy, cx = int(probe[0] / CELL), int(probe[1] / CELL)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for entry in index.get((cy + dy, cx + dx), ()):
                    distance = metres(probe, (entry[0], entry[1]))
                    key = (entry[0], entry[1])
                    if distance <= radius and (key not in best or distance < best[key][0]):
                        best[key] = (distance, entry)
    return [entry for _, entry in sorted(best.values(), key=lambda item: item[0])]


class Paths(osmium.SimpleHandler):
    """Read every cycle path and voetpad: who may use it.

    The cycle paths become an index of where a path the bromfiets may lawfully
    use actually runs, which is the only evidence that can justify closing the
    carriageway beside it and what breaks the deadlock.

    Every voetpad is read for NL-ACC-12, which opens one only where the mapper's
    sign and the register's sign or onderbord say the same thing.
    """

    def __init__(self, signs, plated=None) -> None:
        super().__init__()
        self.signs = signs
        self.plated = plated or {}
        self.footpath: dict[int, str] = {}
        self.voetpaden: dict[int, tuple[dict, tuple[int, ...], float]] = {}
        self.speed: dict[int, str] = {}
        self.usable: dict[tuple[int, int], list] = defaultdict(list)
        self.counts = Counter()

    def _footpath(self, way_id: int, tags: dict, points, refs=()) -> None:
        """NL-ACC-12 for one voetpad, and the A1 that binds whoever it admits."""
        signs = mapped_signs(tags)
        unsigned = not (tags.get("traffic_sign") or "").strip()
        if not signs & {"G7", "G12a"} and not unsigned:
            return
        # The nearest register sign, without the clearance _sign_for demands.
        # That clearance stands in for the mapper on a path OSM left unsigned;
        # here the mapper has already named the sign, so a register sign of a
        # different kind further off belongs to the next path, not this one.
        nearest = _near(self.signs, points, SIGN_METRES) if "G12a" in signs else []
        register = nearest[0][2] if nearest else None
        plate = ("G7" in signs or unsigned) and any(
            entry[2] == "G7" and plate_admits(entry[3])
            for entry in _near(self.plated, points, SIGN_METRES)
        )
        verdict = footpath_overlay(tags, register, plate)
        if "G12a" not in signs:
            # Kept for spread(): a G7 governs the voetpad behind it, not only
            # the metres beside the post.
            length = sum(metres(a, b) for a, b in pairwise(points))
            self.voetpaden[way_id] = (tags, tuple(refs), length)
        if verdict is None:
            return
        self.footpath[way_id] = verdict
        self.counts["voetpad opened by a confirmed sign"] += 1

        # The plate admits the class; the A1 beside it still binds it. OSM
        # often leaves the value off a voetpad, and the API reads the limit
        # from maxspeed alone, so the register's figure is written there.
        limits = [
            _speed(entry[4])
            for entry in _near(self.plated, points, SIGN_METRES)
            if entry[2] == "A1" and _speed(entry[4]) is not None
        ]
        current = _speed(tags.get("maxspeed"))
        if limits and (current is None or min(limits) < current):
            self.speed[way_id] = str(min(limits))
            self.counts["voetpad limit taken from the register"] += 1

    def spread(self) -> None:
        """Carry a confirmed onderbord over the voetpad it governs.

        A G7 and its onderbord hold until the next sign, so the plate the
        register shows at the entrance reaches the voetpad behind it. It is
        carried only over connected footways and pedestrian ways that are
        unsigned or G7 themselves, and only to a class the mapper permits on
        each of them, so every way it opens still has both sources. It stops at
        SPREAD_METRES from the confirmed way, because nothing in the data marks
        where the zone ends.
        """
        at_node: dict[int, list[int]] = defaultdict(list)
        for way_id, (_, refs, _) in self.voetpaden.items():
            for ref in refs:
                at_node[ref].append(way_id)
        reach = {
            way_id: (verdict, 0.0, self.speed.get(way_id))
            for way_id, verdict in self.footpath.items()
            if way_id in self.voetpaden and verdict == FOOTPATH_PLATE
        }
        queue = sorted(reach, key=lambda way_id: reach[way_id][1])
        while queue:
            way_id = queue.pop(0)
            verdict, travelled, limit = reach[way_id]
            for ref in self.voetpaden[way_id][1]:
                for other in at_node[ref]:
                    tags, _, length = self.voetpaden[other]
                    distance = travelled + length
                    if other in reach or distance > SPREAD_METRES:
                        continue
                    if not stated_access(tags, ("moped",)):
                        continue
                    reach[other] = (verdict, distance, limit)
                    queue.append(other)
                    if other not in self.footpath:
                        self.footpath[other] = verdict
                        self.counts["voetpad opened by the onderbord before it"] += 1
                        current = _speed(tags.get("maxspeed"))
                        if limit is not None and (current is None or int(limit) < current):
                            self.speed[other] = limit

    def way(self, w) -> None:
        tags = dict(w.tags)
        footpath = tags.get("highway") in FOOTPATH
        if not footpath and not is_cycle_infrastructure(tags):
            return
        try:
            points = [(n.lat, n.lon) for n in w.nodes if n.location.valid()]
        except osmium.InvalidLocationError:
            return
        if len(points) < 2:
            return
        if footpath:
            self._footpath(w.id, tags, points, [n.ref for n in w.nodes])
            return
        self.counts["cycle paths"] += 1

        bromfiets = path_admits(tags)
        for a, b in pairwise(points):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            self.usable[(int(mid[0] / CELL), int(mid[1] / CELL))].append(
                (mid, bearing(a, b), bromfiets)
            )
        self.counts["usable by a bromfiets"] += bromfiets


class Match(osmium.SimpleHandler):
    """Ask every routable OSM way whether the authority forbids it."""

    def __init__(self, grid, usable) -> None:
        super().__init__()
        self.grid = grid
        self.usable = usable
        self.verdict: dict[int, str] = {}
        self.seen = 0
        self.counts = Counter()
        # Held-out check: where OSM already states the answer, does WKD agree?
        self.agree = Counter()

    def _sidepath(self, points) -> tuple[bool, bool]:
        """Is there a path beside this road, and may the bromfiets use it?

        `present and not usable` is the deadlock this whole pass exists to
        find: something is running alongside that the rules refuse, while the
        carriageway is being closed because a rider is supposed to be on it.
        `not present` is the opposite case and matters just as much — a refusal
        with no path beside it was never a mandatory-use verdict, so it keeps
        its closure.

        Both answers need most of the road to agree, so a path that joins for
        one block neither justifies a closure nor lifts one.
        """
        samples = found = usable = 0
        for a, b in pairwise(points):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            head = bearing(a, b)
            samples += 1
            cy, cx = int(mid[0] / CELL), int(mid[1] / CELL)
            best = None
            best_d = SIDEPATH_METRES
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for other, other_head, brom in self.usable.get((cy + dy, cx + dx), ()):
                        d = metres(mid, other)
                        if d < best_d and aligned(head, other_head):
                            best_d, best = d, brom
            if best is not None:
                found += 1
                usable += best
        if samples == 0 or found / samples < COVERAGE:
            return False, False
        return True, usable / found >= COVERAGE

    def _vote(self, points, index, want_road=None):
        """How many samples matched, and how many voted to close the bromfiets."""
        tries = hits = votes = 0
        for a, b in pairwise(points):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            head = bearing(a, b)
            tries += 1
            best = None
            best_d = MATCH_METRES
            cy, cx = int(mid[0] / CELL), int(mid[1] / CELL)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for other, other_head, brom, is_road in index.get((cy + dy, cx + dx), ()):
                        if want_road is not None and is_road != want_road:
                            continue
                        d = metres(mid, other)
                        if d < best_d and aligned(head, other_head):
                            best_d, best = d, brom
            if best is not None:
                hits += 1
                votes += best
        return tries, hits, votes

    def way(self, w) -> None:
        highway = w.tags.get("highway")
        if highway not in ROUTABLE:
            return
        want_road = highway not in CYCLE_LIKE
        try:
            points = [(n.lat, n.lon) for n in w.nodes if n.location.valid()]
        except osmium.InvalidLocationError:
            return
        if len(points) < 2:
            return
        length = sum(metres(a, b) for a, b in pairwise(points))
        self.seen += 1
        if length < MIN_LENGTH_METRES:
            return

        tries, hits, votes = self._vote(points, self.grid, want_road)
        # A closure needs most of the matched samples to agree, so one stray
        # section beside a long way cannot shut it.
        closes = tries > 0 and hits / tries >= COVERAGE and votes / hits >= COVERAGE

        if not want_road:
            # A path is not a carriageway; art. 6 lid 2 has nothing to say about
            # it, so a refusal here stands as it is.
            if closes:
                self.verdict[w.id] = "no"
            return

        # OSM's own mandatory-use statement needs the same test. A rider is
        # only obliged off the carriageway if there is somewhere lawful to go.
        if closes or w.tags.get("moped") == "use_sidepath":
            present, usable = self._sidepath(points)
            if present and not usable:
                # The deadlock. Something runs alongside and the rules refuse
                # it, so the bromfiets has nowhere lawful at all. RVV art. 6 lid
                # 2 answers this case explicitly and puts the rider on the
                # rijbaan; the router follows it there.
                self.verdict[w.id] = "on_roadway"
                self.counts["deadlock resolved to the roadway"] += 1
            elif closes:
                # Either the path beside is one the bromfiets may use, so the
                # closure is a genuine mandatory-use verdict, or nothing runs
                # alongside at all, which means the refusal was never about
                # mandatory use and is a prohibition in its own right.
                self.verdict[w.id] = "no"
                self.counts["closure kept" if present else "closure kept, no path beside"] += 1
        brom = closes

        # Does the authority confirm what OSM already claims?
        moped = w.tags.get("moped")
        if moped == "use_sidepath":
            self.agree[
                "osm says sidepath, WKD closes bromfiets"
                if brom
                else "osm says sidepath, WKD does not close"
            ] += 1
        elif moped == "no":
            self.agree[
                "osm says moped=no, WKD closes bromfiets"
                if brom
                else "osm says moped=no, WKD does not close"
            ] += 1


#: Namespaced so nobody mistakes them for something a mapper typed, and so a
#: stray one in the wild cannot reach our rules.
BROM_TAG = "amgraph:bromfiets"
COUNTRY_TAG = "amgraph:country"


def load_supported_area(path: Path):
    """The authoritative BRK land boundary used by both graph and API."""
    try:
        document = json.loads(path.read_text())
        features = document["features"]
        feature = features[0]
        properties = feature["properties"]
        if len(features) != 1 or properties.get("identificatie") != "LND6030":
            raise ValueError("expected the single BRK land area LND6030")
        if properties.get("naam") != "Nederland":
            raise ValueError("expected the Netherlands land area")
        area = shape(feature["geometry"])
        if area.geom_type != "MultiPolygon" or area.is_empty or not area.is_valid:
            raise ValueError("the Netherlands boundary is not a valid MultiPolygon")
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Invalid supported-area file at {path}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    shapely.prepare(area)
    return area


class Inject(osmium.SimpleHandler):
    """Write the extract back out with the authority's verdict as tags.

    Valhalla's Lua transform is handed a way's tags and nothing else — no id —
    so an id-keyed overlay cannot be consulted there. Writing the verdict into
    the extract puts it where the rules already look, keeps access.lua free of
    file handling, and leaves an artefact that can be inspected with any OSM
    tool when a rider asks why a road was refused.
    """

    def __init__(
        self, writer, closed, supported_area, bus_lanes_clear=frozenset(), speed=None
    ) -> None:
        super().__init__()
        self.writer = writer
        self.closed = closed
        self.supported_area = supported_area
        self.bus_lanes_clear = bus_lanes_clear
        self.speed = speed or {}
        self.tagged = 0
        self.dutch = 0
        self.unsupported = 0

    def node(self, n) -> None:
        self.writer.add_node(n)

    def relation(self, r) -> None:
        original = dict(r.tags)
        try:
            tags = conservative_restriction_tags(original)
        except ValueError as exc:
            raise ValueError(f"restriction relation {r.id}: {exc}") from exc
        self.writer.add_relation(r if tags == original else r.replace(tags=tags))

    def way(self, w) -> None:
        verdict = self.closed.get(w.id)
        is_route = w.tags.get("highway") is not None or w.tags.get("route") == "ferry"
        if verdict is None and not is_route:
            self.writer.add_way(w)
            return

        # Only this authority pass can supply internal access evidence.
        tags = {key: value for key, value in w.tags if not key.startswith("amgraph:")}
        if is_route:
            try:
                coordinates = [(n.lon, n.lat) for n in w.nodes if n.location.valid()]
                wholly_dutch = len(coordinates) >= 2 and shapely.contains_properly(
                    self.supported_area, LineString(coordinates)
                )
            except (osmium.InvalidLocationError, ValueError):
                wholly_dutch = False
            tags[COUNTRY_TAG] = "NL" if wholly_dutch else "unsupported"
            if wholly_dutch:
                self.dutch += 1
            else:
                self.unsupported += 1
        if verdict is not None:
            tags[BROM_TAG] = verdict
        if w.id in self.bus_lanes_clear:
            tags[BUS_LANE_TAG] = "none"
        if w.id in self.speed:
            tags["maxspeed"] = self.speed[w.id]
        self.writer.add_way(w.replace(tags=tags))
        self.tagged += 1


class RestrictionAudit(osmium.SimpleHandler):
    """Reject every unmodelled turn restriction before expensive enrichment."""

    def __init__(self) -> None:
        super().__init__()
        self.seen = 0
        self.failures: list[str] = []

    def relation(self, relation) -> None:
        tags = dict(relation.tags)
        if tags.get("type") != "restriction":
            return
        self.seen += 1
        try:
            conservative_restriction_tags(tags)
        except ValueError as exc:
            self.failures.append(f"{relation.id}: {exc}")


def validate_turn_restrictions(extract: str) -> int:
    audit = RestrictionAudit()
    audit.apply_file(extract)
    if audit.failures:
        examples = "; ".join(audit.failures[:20])
        remainder = len(audit.failures) - 20
        if remainder > 0:
            examples += f"; and {remainder} more"
        raise ValueError(f"unmodelled turn restriction relations: {examples}")
    return audit.seen


def inject(
    extract: str, closed, supported_area, out: Path, bus_lanes_clear=frozenset(), speed=None
) -> None:
    # Never replace the last complete extract until the new one has survived a
    # full OSM pass. A newly encountered fail-closed tag can abort late in a
    # country-sized write, and build.sh must not find that partial PBF.
    completed: dict[str, Inject] = {}

    def write(candidate: Path) -> None:
        writer = osmium.SimpleWriter(str(candidate))
        handler = Inject(writer, closed, supported_area, bus_lanes_clear, speed)
        try:
            handler.apply_file(extract, locations=True)
        finally:
            writer.close()
        completed["handler"] = handler

    replace_atomically(out, write)
    handler = completed["handler"]

    # The country merger requires one current input per country. Remove an
    # artefact from an earlier source name only after this one is complete.
    for stale in out.parent.glob("*-official.osm.pbf"):
        if stale != out:
            stale.unlink()
    print(f"  ways tagged             : {handler.tagged:,}")
    print(f"  wholly inside NL        : {handler.dutch:,}")
    print(f"  foreign or crossing     : {handler.unsupported:,}")
    print(f"wrote {out} ({out.stat().st_size / 1e9:.2f} GB)")


def enriched_name(extract: str) -> str:
    """`netherlands-latest.osm.pbf` -> `netherlands-latest-official.osm.pbf`.

    The country merger derives the same name from the module's source URL.
    """
    name = Path(extract).name
    return name.removesuffix(".osm.pbf") + "-official.osm.pbf"


def default_extract(work: Path) -> Path:
    """The one plain extract in the working directory."""
    plain = sorted(p for p in work.glob("*.osm.pbf") if not p.name.endswith("-official.osm.pbf"))
    if len(plain) == 1:
        return plain[0]
    if not plain:
        print(f"No extract in {work}. Fetch one with: make infra-extract", file=sys.stderr)
    else:
        print(f"More than one extract in {work}; name the one to use:", file=sys.stderr)
        for p in plain:
            print(f"  {p}", file=sys.stderr)
    raise SystemExit(1)


def main(extract: str, out: Path) -> None:
    here = Path(__file__).parent
    work = Path(os.environ.get("AMGRAPH_WORK", here / "work/countries/nl"))
    shp = next((work / "wkd").glob("**/WKD_VRKRSTPNV2.shp"), None)
    if shp is None:
        print(f"No Verkeerstypen shapefile under {work / 'wkd'}.", file=sys.stderr)
        print("Fetch it with: make infra-official-data", file=sys.stderr)
        raise SystemExit(1)

    boundary_path = Path(
        os.environ.get("AMGRAPH_SUPPORTED_AREA", work / "boundaries" / "netherlands.geojson")
    )
    supported_area = load_supported_area(boundary_path)

    print("checking every turn restriction…", flush=True)
    restriction_count = validate_turn_restrictions(extract)
    print(f"  restriction relations   : {restriction_count:,}", flush=True)

    print(f"\nreading {shp.name}…", flush=True)
    grid, counts = load_closures(shp.with_suffix(""))
    print(f"  NWB sections            : {counts['total']:,}")
    print(f"  of which close a class  : {counts['closing']:,}")
    print(f"    on a carriageway      : {counts['carriageway']:,}")
    print(f"    on cycle-ish ways     : {counts['cycle-ish']:,}")
    print(f"  indexed segments        : {counts['segments']:,}", flush=True)

    signs_path = work / "ndw" / "signs.geojson"
    if not signs_path.exists():
        print(f"No sign register at {signs_path}.", file=sys.stderr)
        print("Fetch it with: make infra-official-data", file=sys.stderr)
        raise SystemExit(1)
    print(f"\nreading {signs_path.name}…", flush=True)
    signs, sign_counts, plated = load_signs(signs_path)
    print(f"  placed cycle signs      : {sum(sign_counts.values()):,}")
    for code in sorted(sign_counts):
        print(f"    {code:20s}: {sign_counts[code]:,}")

    print("\nreading the cycle network…", flush=True)
    paths = Paths(signs, plated)
    paths.apply_file(extract, locations=True)
    paths.spread()
    for label in (
        "cycle paths",
        "voetpad opened by a confirmed sign",
        "voetpad opened by the onderbord before it",
        "voetpad limit taken from the register",
        "usable by a bromfiets",
    ):
        print(f"  {label:<34}: {paths.counts[label]:,}")

    print("\nmatching against OpenStreetMap…", flush=True)
    match = Match(grid, paths.usable)
    match.apply_file(extract, locations=True)

    print(f"  routable ways considered: {match.seen:,}")
    print(f"  ways the authority rules: {len(match.verdict):,}")
    for label, n in sorted(match.counts.items()):
        print(f"    {label:<38}: {n:,}")

    print("\n=== held out: where OSM already states the answer ===")
    for label, n in sorted(match.agree.items()):
        print(f"  {label:48s} {n:>7,}")

    overlay: dict[int, str] = dict(match.verdict)

    # NL-ACC-12. Match never reaches a voetpad, so nothing here can collide.
    for way_id, verdict in paths.footpath.items():
        assert way_id not in overlay, f"way {way_id} is both a voetpad and a matched way"
        overlay[way_id] = verdict

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        fh.write("# way_id\tbromfiets   (no | on_roadway | footpath_onderbord | footpath_g12a)\n")
        for way_id in sorted(overlay):
            fh.write(f"{way_id}\t{overlay[way_id]}\n")
    print(f"\nwrote {out} ({len(overlay):,} ways)")

    print("\nfinding bus-lane roads no turn crosses the bus lane on…", flush=True)
    bus_lanes_clear = clear_bus_lane_ways(extract)
    print(f"  cleared                 : {len(bus_lanes_clear):,}")

    print("\nwriting the enriched extract…", flush=True)
    inject(
        extract,
        overlay,
        supported_area,
        Path(extract).with_name(enriched_name(extract)),
        bus_lanes_clear,
        paths.speed,
    )


if __name__ == "__main__":
    root = Path(__file__).parent
    work = Path(os.environ.get("AMGRAPH_WORK", root / "work/countries/nl"))
    main(
        sys.argv[1] if len(sys.argv) > 1 else str(default_extract(work)),
        Path(sys.argv[2]) if len(sys.argv) > 2 else work / "official-access.tsv",
    )
