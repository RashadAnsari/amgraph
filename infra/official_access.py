"""Turn the road authority's access refusals into an overlay for the graph.

OpenStreetMap describes the Netherlands; Rijkswaterstaat's Wegkenmerkendatabase
adds official access evidence. Its Verkeerstypen product carries, per NWB road section and per
direction, whether a snorfiets or a bromfiets may be there at all — derived by
NDW from the national traffic-sign register, parallel-path detection and the
built-up-area topography. That is the mandatory-use obligation, which cannot be
modelled from OSM tags because OSM states it on only a fraction of the roads it
binds, already resolved by the people who put up the signs.

NDW documents that the traffic-sign-to-NWB coupling is often wrong, including
mandatory cycle-path signs attached to the ordinary carriageway, and the
geometric match from that network onto OSM adds another source of error. So a
refusal is cheap to accept and an affirmation is not, and this writer emits
exactly three values:

`no`     — the class may not be here. Safe by construction: wrong costs a detour.

`on_roadway` — this carriageway carries a mandatory-use closure, and a path was
    found running beside it that the rules refuse the class. That is a
    contradiction, not caution: the rider is being sent off the road and
    refused the path they are being sent to. RVV art. 5 lid 2 and art. 6 lid 2
    settle it — "Zij gebruiken de rijbaan indien een verplicht fietspad of een
    fiets/bromfietspad ontbreekt" — so the closure is lifted and the roadway,
    which the statute makes mandatory here, stays open. Where *no* path runs
    alongside, the refusal was never about mandatory use and stays `no`.

`roadway_only` — a verplicht fietspad in a municipality that has used RVV art.
    5 lid 8 to send snorfietsen to the rijbaan. The only refusal that overrides
    an OSM cycle sign, because its whole content is that the sign does not mean
    what it usually means.

`yes`    — an unsigned cycle path that the authority's own sign register says
    carries a G11 or a G12a. Snorfiets only. Art. 5 lid 1 admits it to both, so
    the register needs only to establish that one of the two is there;
    confusing them costs nothing. For a bromfiets they are opposite answers, so
    the same evidence would be a coin flip and art. 6 lid 2 already gives it
    the roadway.

Measured on the ways where OSM does state a sign, so both sources speak: the
register agrees on 96.1% overall, and disagrees on 0.47% of the snorfiets
openings against 3.00% of the bromfiets ones it is therefore not used for.

**It applies to snorfiets, bromfiets and speed pedelec only.** WKD models
SNRFTS and BRMFTS. A speed pedelec is legally a bromfiets, so BRMFTS binds it.
A brommobiel is *not* covered: RVV art. 6 lid 3 puts it on the rijbaan, so a
BRMFTS closure caused by a mandatory sidepath does not reach it, and applying
one would shut roads it may lawfully use. It keeps the tag-derived rules.

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
from cycle_rules import (
    closes_class,
    cycle_sign_of,
    is_cycle_infrastructure,
    osm_cycle_sign,
    path_classes,
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
#: tell them apart. Without this, the carriageway's "no bromfiets" verdict, the
#: one that exists *because* the path is compulsory, lands on the path and
#: closes the very road the rule sends riders onto.
CYCLE_LIKE = {"cycleway", "path", "footway", "bridleway", "steps", "track"}

#: How near a register sign must stand to be describing this path. NDW warns
#: that a sign's coordinates sometimes mark the photographer rather than the
#: post, so this is looser than a survey would need.
SIGN_METRES = 20.0

#: A different cycle sign standing this near makes the attribution ambiguous,
#: whatever the ranking. Measured: raises agreement with OSM from 95.3% to
#: 96.1% at a cost of 5% of the matches.
SIGN_CLEAR_METRES = 30.0

#: How far off a carriageway a parallel path may lie and still be the sidepath
#: that carriageway's mandatory-use verdict refers to. Wide enough for a berm
#: and a parking strip, narrow enough not to reach the next street.
SIDEPATH_METRES = 25.0


def load_snorfiets_roadway(path: Path):
    """The municipalities that have moved snorfietsen onto the rijbaan.

    Built by infra/legal_zones.py from the official BRK boundaries, and flagged
    there rather than listed here so the municipal facts stay in one file.
    """
    try:
        document = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"No legal zones at {path}: {exc}", file=sys.stderr)
        print("Build them with: make infra-legal-zones", file=sys.stderr)
        raise SystemExit(1) from exc
    areas = [
        shape(feature["geometry"])
        for feature in document.get("features", ())
        if (feature.get("properties") or {}).get("snorfiets_roadway")
    ]
    if not areas:
        print(f"No snorfiets-roadway municipality in {path}.", file=sys.stderr)
        raise SystemExit(1)
    combined = shapely.union_all(areas)
    shapely.prepare(combined)
    print(f"  art. 5 lid 8 municipalities: {len(areas)}")
    return combined


def load_signs(path: Path):
    """The road authority's cycle-path signs, indexed by grid cell."""
    grid: dict[tuple[int, int], list] = defaultdict(list)
    counts = Counter()
    with path.open() as fh:
        document = json.load(fh)
    for feature in document.get("features", ()):
        code = cycle_sign_of(feature.get("properties") or {})
        if code is None:
            continue
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            continue
        lon, lat = geometry["coordinates"][0], geometry["coordinates"][1]
        counts[code] += 1
        grid[(int(lat / CELL), int(lon / CELL))].append((lat, lon, code))
    return grid, counts


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

    sections: list[tuple[list[tuple[float, float]], bool, bool, bool]] = []
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
        snor = closes_class(rec[idx["SNRFTS_H"]], rec[idx["SNRFTS_T"]], auto_head, auto_tail)
        brom = closes_class(rec[idx["BRMFTS_H"]], rec[idx["BRMFTS_T"]], auto_head, auto_tail)
        if len(shp.points) < 2:
            continue

        # Whether this is a carriageway, so it is only ever matched to one.
        is_road = auto_head == "J" or auto_tail == "J"

        points = [(lat, lon) for lon, lat in (_to_wgs84.transform(x, y) for x, y in shp.points)]

        if snor or brom:
            sections.append((points, snor, brom, is_road))
            counts["carriageway" if is_road else "cycle-ish"] += 1
            counts["closing"] += 1
            counts["snorfiets"] += snor
            counts["bromfiets"] += brom

    grid: dict[tuple[int, int], list] = defaultdict(list)
    for points, snor, brom, is_road in sections:
        for a, b in pairwise(points):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            grid[(int(mid[0] / CELL), int(mid[1] / CELL))].append(
                (mid, bearing(a, b), snor, brom, is_road)
            )

    counts["segments"] = sum(len(v) for v in grid.values())
    return grid, counts


class Paths(osmium.SimpleHandler):
    """Read every cycle path: which sign stands on it, and who may use it.

    Two products, and the second is what breaks the deadlock. The first is the
    register's sign for a path OSM left unsigned. The second is an index of
    where a path each class may lawfully use actually runs, which is the only
    evidence that can justify closing the carriageway beside it.
    """

    def __init__(self, signs, snorfiets_roadway=None) -> None:
        super().__init__()
        self.signs = signs
        self.snorfiets_roadway = snorfiets_roadway
        self.opened: dict[int, str] = {}
        self.closed: dict[int, str] = {}
        self.usable: dict[tuple[int, int], list] = defaultdict(list)
        self.counts = Counter()

    def _art5_lid8(self, points) -> bool:
        """Is this path where a verplicht fietspad can send a snorfiets away?

        RVV art. 5 lid 8 lets a municipality put snorfietsen on the rijbaan by
        a verkeersbesluit plus an onderbord on the G11. Amsterdam and Utrecht
        have both done it, over most of their central cycle network. Neither
        OSM nor the register records those onderborden reliably, so inside
        those municipalities a G11 cannot be read as admitting a snorfiets.

        Refusing the path is the conservative side here and it costs nothing:
        art. 5 lid 2 and the mandatory-use gating put the rider on the rijbaan,
        which is exactly where the verkeersbesluit wants them.
        """
        if self.snorfiets_roadway is None:
            return False
        sample = points[len(points) // 2]
        return shapely.contains_xy(self.snorfiets_roadway, sample[1], sample[0])

    def _sign_for(self, points) -> str | None:
        """The register's sign for this path, or None if it is not clear."""
        near: list[tuple[float, str]] = []
        for a, b in pairwise(points):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            cy, cx = int(mid[0] / CELL), int(mid[1] / CELL)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for lat, lon, code in self.signs.get((cy + dy, cx + dx), ()):
                        distance = metres(mid, (lat, lon))
                        if distance <= SIGN_CLEAR_METRES:
                            near.append((distance, code))
        if not near:
            return None
        near.sort()
        distance, code = near[0]
        if distance > SIGN_METRES:
            return None
        # Two different cycle signs this close cannot both describe this path,
        # and there is no way to tell which one does.
        if any(other != code for _, other in near):
            self.counts["ambiguous"] += 1
            return None
        return code

    def way(self, w) -> None:
        tags = dict(w.tags)
        if not is_cycle_infrastructure(tags):
            return
        try:
            points = [(n.lat, n.lon) for n in w.nodes if n.location.valid()]
        except osmium.InvalidLocationError:
            return
        if len(points) < 2:
            return
        self.counts["cycle paths"] += 1

        register = self._sign_for(points)
        if register is not None:
            self.counts[f"register says {register}"] += 1

        snorfiets, bromfiets = path_classes(tags, register)

        # A verplicht fietspad in a municipality that has moved snorfietsen to
        # the rijbaan. The sign alone does not settle it there, so the class
        # comes off the path and the rijbaan carries it instead.
        if snorfiets and (osm_cycle_sign(tags) or register) == "G11" and self._art5_lid8(points):
            snorfiets = False
            self.closed[w.id] = "roadway_only"
            self.counts["snorfiets off a G11 under art. 5 lid 8"] += 1
        # Only worth writing where it changes the answer: the mapper's own sign
        # already decides the rest, and a tag nothing reads is noise.
        elif (
            register is not None
            and osm_cycle_sign(tags) is None
            and snorfiets
            and stated_access(tags, ("mofa",)) is None
        ):
            self.opened[w.id] = "yes"
            self.counts["snorfiets opened by the register"] += 1

        for a, b in pairwise(points):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            self.usable[(int(mid[0] / CELL), int(mid[1] / CELL))].append(
                (mid, bearing(a, b), snorfiets, bromfiets)
            )
        self.counts["usable by a snorfiets"] += snorfiets
        self.counts["usable by a bromfiets"] += bromfiets


class Match(osmium.SimpleHandler):
    """Ask every routable OSM way whether the authority forbids it."""

    def __init__(self, grid, usable, snorfiets_roadway=None) -> None:
        super().__init__()
        self.grid = grid
        self.usable = usable
        self.snorfiets_roadway = snorfiets_roadway
        self.verdict: dict[int, tuple[str | None, str | None]] = {}
        self.seen = 0
        self.counts = Counter()
        # Held-out check: where OSM already states the answer, does WKD agree?
        self.agree = Counter()

    def _sidepath(self, points):
        """Per class: is there a path beside this road, and may the class use it?

        Returns ((present, usable), (present, usable)) for snorfiets and
        bromfiets. `present and not usable` is the deadlock this whole pass
        exists to find: something is running alongside that the rules refuse,
        while the carriageway is being closed because a rider is supposed to be
        on it. `not present` is the opposite case and matters just as much — a
        refusal with no path beside it was never a mandatory-use verdict, so it
        keeps its closure.

        Both answers need most of the road to agree, so a path that joins for
        one block neither justifies a closure nor lifts one.
        """
        samples = found = 0
        usable = [0, 0]
        for a, b in pairwise(points):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            head = bearing(a, b)
            samples += 1
            cy, cx = int(mid[0] / CELL), int(mid[1] / CELL)
            best = None
            best_d = SIDEPATH_METRES
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for other, other_head, snor, brom in self.usable.get((cy + dy, cx + dx), ()):
                        d = metres(mid, other)
                        if d < best_d and aligned(head, other_head):
                            best_d, best = d, (snor, brom)
            if best is not None:
                found += 1
                usable[0] += best[0]
                usable[1] += best[1]
        if samples == 0 or found / samples < COVERAGE:
            return (False, False), (False, False)
        return tuple((True, usable[index] / found >= COVERAGE) for index in (0, 1))

    def _vote(self, points, index, want_road=None):
        """How many samples matched, and how many voted for each class."""
        hits = snor_votes = brom_votes = 0
        tries = 0
        for a, b in pairwise(points):
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            head = bearing(a, b)
            tries += 1
            best = None
            best_d = MATCH_METRES
            cy, cx = int(mid[0] / CELL), int(mid[1] / CELL)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    for entry in index.get((cy + dy, cx + dx), ()):
                        other, other_head, snor, brom = (
                            entry[0],
                            entry[1],
                            entry[2],
                            entry[3],
                        )
                        if want_road is not None and entry[4] != want_road:
                            continue
                        d = metres(mid, other)
                        if d < best_d and aligned(head, other_head):
                            best_d, best = d, (snor, brom)
            if best is not None:
                hits += 1
                snor_votes += best[0]
                brom_votes += best[1]
        return tries, hits, snor_votes, brom_votes

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

        tries, hits, snor_votes, brom_votes = self._vote(points, self.grid, want_road)
        closes = [False, False]
        if tries > 0 and hits / tries >= COVERAGE:
            # A closure needs most of the matched samples to agree, so one stray
            # section beside a long way cannot shut it.
            closes = [snor_votes / hits >= COVERAGE, brom_votes / hits >= COVERAGE]

        # OSM's own mandatory-use statement needs the same test. A rider is
        # only obliged off the carriageway if there is somewhere lawful to go.
        sidepath_tag = [
            w.tags.get("mofa") == "use_sidepath" or w.tags.get("bicycle") == "use_sidepath",
            w.tags.get("moped") == "use_sidepath",
        ]

        if not want_road:
            # A path is not a carriageway; art. 5 lid 2 and art. 6 lid 2 have
            # nothing to say about it, so a refusal here stands as it is.
            if any(closes):
                self.verdict[w.id] = tuple("no" if c else None for c in closes)
            return

        beside = self._sidepath(points)
        verdict: list[str | None] = [None, None]

        # RVV art. 5 lid 8, the other half of the rule applied in Paths. Where a
        # municipality has moved snorfietsen to the rijbaan, the rijbaan is
        # where they belong, so nothing may take them off it. OSM often still
        # carries the pre-decision `mofa=use_sidepath` on these carriageways
        # while the path beside now says `mofa=no` — an outright contradiction,
        # and the verkeersbesluit is what settles it. Utrecht is the clearest
        # case: with both honoured, a snorfiets could not leave a 1.5 km island
        # in the city centre.
        if self.snorfiets_roadway is not None:
            middle = points[len(points) // 2]
            if shapely.contains_xy(self.snorfiets_roadway, middle[1], middle[0]):
                verdict[0] = "on_roadway"
                self.counts["snorfiets kept on the roadway under art. 5 lid 8"] += 1
        for index in (0, 1):
            if verdict[index] is not None or not (closes[index] or sidepath_tag[index]):
                continue
            present, usable = beside[index]
            if present and not usable:
                # The deadlock. Something runs alongside and the rules refuse
                # it, so the class has nowhere lawful at all. RVV art. 5 lid 2
                # and art. 6 lid 2 answer this case explicitly and put the
                # rider on the rijbaan; the router follows them there.
                verdict[index] = "on_roadway"
                self.counts["deadlock resolved to the roadway"] += 1
            elif closes[index]:
                # Either the path beside is one this class may use, so the
                # closure is a genuine mandatory-use verdict, or nothing runs
                # alongside at all, which means the refusal was never about
                # mandatory use and is a prohibition in its own right.
                verdict[index] = "no"
                self.counts["closure kept" if present else "closure kept, no path beside"] += 1
        if any(verdict):
            self.verdict[w.id] = tuple(verdict)
        brom = closes[1]

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
SNOR_TAG = "amgraph:snorfiets"
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

    def __init__(self, writer, closed, supported_area) -> None:
        super().__init__()
        self.writer = writer
        self.closed = closed
        self.supported_area = supported_area
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

        tags = dict(w.tags)
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
            snor, brom = verdict
            if snor:
                tags[SNOR_TAG] = snor
            if brom:
                tags[BROM_TAG] = brom
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


def inject(extract: str, closed, supported_area, out: Path) -> None:
    # Never replace the last complete extract until the new one has survived a
    # full OSM pass. A newly encountered fail-closed tag can abort late in a
    # country-sized write, and build.sh must not find that partial PBF.
    completed: dict[str, Inject] = {}

    def write(candidate: Path) -> None:
        writer = osmium.SimpleWriter(str(candidate))
        handler = Inject(writer, closed, supported_area)
        try:
            handler.apply_file(extract, locations=True)
        finally:
            writer.close()
        completed["handler"] = handler

    replace_atomically(out, write)
    handler = completed["handler"]

    # build.sh refuses to guess between multiple enriched extracts. Remove an
    # artefact from an earlier source name only after this one is complete.
    for stale in out.parent.glob("*-official.osm.pbf"):
        if stale != out:
            stale.unlink()
    print(f"  ways tagged             : {handler.tagged:,}")
    print(f"  wholly inside NL        : {handler.dutch:,}")
    print(f"  foreign or crossing     : {handler.unsupported:,}")
    print(f"wrote {out} ({out.stat().st_size / 1e9:.2f} GB)")


WORK_BOUNDARY = Path(__file__).parent / "work" / "boundaries" / "netherlands.geojson"


def enriched_name(extract: str) -> str:
    """`netherlands-latest.osm.pbf` -> `netherlands-latest-official.osm.pbf`.

    Derived rather than hardcoded so the extract's country is not baked in:
    `make infra-extract EXTRACT_URL=...` saves whatever Geofabrik calls the
    file, and build.sh looks for `*-official.osm.pbf`.
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
    shp = next((here / "work" / "wkd").glob("**/WKD_VRKRSTPNV2.shp"), None)
    if shp is None:
        print("No Verkeerstypen shapefile under infra/work/wkd.", file=sys.stderr)
        print("Fetch it with: make infra-official-data", file=sys.stderr)
        raise SystemExit(1)

    boundary_path = Path(os.environ.get("AMGRAPH_SUPPORTED_AREA", WORK_BOUNDARY))
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
    print(f"    snorfiets forbidden   : {counts['snorfiets']:,}")
    print(f"    bromfiets forbidden   : {counts['bromfiets']:,}")
    print(f"  indexed segments        : {counts['segments']:,}", flush=True)

    signs_path = here / "work" / "ndw" / "signs.geojson"
    if not signs_path.exists():
        print(f"No sign register at {signs_path}.", file=sys.stderr)
        print("Fetch it with: make infra-official-data", file=sys.stderr)
        raise SystemExit(1)
    print(f"\nreading {signs_path.name}…", flush=True)
    signs, sign_counts = load_signs(signs_path)
    print(f"  placed cycle signs      : {sum(sign_counts.values()):,}")
    for code in sorted(sign_counts):
        print(f"    {code:20s}: {sign_counts[code]:,}")

    zones_path = Path(
        os.environ.get("AMGRAPH_LEGAL_ZONES", here / "work" / "boundaries" / "legal-zones.geojson")
    )
    snorfiets_roadway = load_snorfiets_roadway(zones_path)

    print("\nreading the cycle network…", flush=True)
    paths = Paths(signs, snorfiets_roadway)
    paths.apply_file(extract, locations=True)
    for label in (
        "cycle paths",
        "register says G11",
        "register says G12a",
        "register says G13",
        "ambiguous",
        "snorfiets opened by the register",
        "usable by a snorfiets",
        "usable by a bromfiets",
    ):
        print(f"  {label:<34}: {paths.counts[label]:,}")

    print("\nmatching against OpenStreetMap…", flush=True)
    match = Match(grid, paths.usable, snorfiets_roadway)
    match.apply_file(extract, locations=True)

    print(f"  routable ways considered: {match.seen:,}")
    print(f"  ways the authority rules: {len(match.verdict):,}")
    for label, n in sorted(match.counts.items()):
        print(f"    {label:<38}: {n:,}")

    print("\n=== held out: where OSM already states the answer ===")
    for label, n in sorted(match.agree.items()):
        print(f"  {label:48s} {n:>7,}")

    # One verdict per way per class. Two passes can reach the same cycle path:
    # the register opens it, and WKD refuses the class on the section beside it.
    # The refusal wins, always. Both are geometric matches onto a network we do
    # not control, and they fail in opposite directions — a wrong closure costs
    # a detour, a wrong opening legalises a way — so a disagreement between them
    # is not a tie to be broken on evidence, it is a case for the safe answer.
    overlay: dict[int, tuple[str | None, str | None]] = dict(match.verdict)
    contested = Counter()
    for source in (paths.opened, paths.closed):
        for way_id, value in source.items():
            snorfiets, bromfiets = overlay.get(way_id, (None, None))
            if snorfiets == "no" or value == "no":
                if snorfiets is not None and snorfiets != value:
                    contested["register opened it, the authority refuses it"] += 1
                snorfiets = "no"
            else:
                snorfiets = value
            overlay[way_id] = (snorfiets, bromfiets)
    for label, n in contested.items():
        print(f"  refusal kept over an opening ({label}): {n:,}")

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        fh.write("# way_id\tsnorfiets\tbromfiets   (no | on_roadway | yes)\n")
        for way_id in sorted(overlay):
            snor, brom = overlay[way_id]
            fh.write(f"{way_id}\t{snor or '-'}\t{brom or '-'}\n")
    print(f"\nwrote {out} ({len(overlay):,} ways)")

    print("\nwriting the enriched extract…", flush=True)
    inject(
        extract,
        overlay,
        supported_area,
        Path(extract).with_name(enriched_name(extract)),
    )


if __name__ == "__main__":
    root = Path(__file__).parent
    main(
        sys.argv[1] if len(sys.argv) > 1 else str(default_extract(root / "work")),
        Path(sys.argv[2]) if len(sys.argv) > 2 else root / "work" / "official-access.tsv",
    )
