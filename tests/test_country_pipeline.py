"""Country attribution and a sidepath obligation need actual geometric evidence."""

import json
import sys
from pathlib import Path

import pytest
import shapely
from shapely.geometry import LineString, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "infra"))

from amgraph_rules.countries import rules_for
from prepare_country import Access, Sidepaths, checked_geometry, require_current


def test_legal_review_deadline_is_exclusive():
    from dataclasses import replace
    from datetime import date

    with pytest.raises(ValueError, match="expired"):
        require_current(replace(rules_for("NL"), valid_until=date(2026, 1, 1)))


def test_invalid_authority_boundary_is_not_repaired_into_new_territory():
    feature = {
        "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 1], [0, 0]]]}
    }
    with pytest.raises(ValueError, match="valid"):
        checked_geometry(feature)


def test_a_crossing_path_is_not_a_sidepath(second_country):
    paths = Sidepaths(Access("ZZ"), second_country, box(1, 0, 2, 1))
    paths.project = lambda x, y: (x, y)
    paths.lines = [LineString([(50, -50), (50, 50)]), LineString([(0, 10), (100, 10)])]
    paths.ids = [1, 2]
    paths.permissions = [{"brommobiel": "mandatory"}, {"bromfiets": "mandatory"}]
    paths.finish()
    adjacent, evidence = paths.adjacent([(0, 0), (100, 0)])
    assert adjacent == {"bromfiets": "mandatory"}
    assert evidence == [2]


def test_an_unusable_path_never_becomes_an_obligation(second_country):
    paths = Sidepaths(Access("ZZ"), second_country, box(1, 0, 2, 1))
    paths.project = lambda x, y: (x, y)
    paths.finish()
    assert paths.adjacent([(0, 0), (100, 0)]) == ({}, [])


def test_a_boundary_fixture_is_a_real_multipolygon():
    feature = {"geometry": shapely.geometry.mapping(box(1, 0, 2, 1))}
    assert checked_geometry(json.loads(json.dumps(feature))).geom_type == "MultiPolygon"


def test_an_unmodelled_turn_closes_its_incident_ways_before_enrichment(tmp_path):
    from prepare_country import RestrictionClosures

    source = tmp_path / "turn.osm"
    source.write_text("""<osm version="0.6"><relation id="1" version="1">
      <member type="way" ref="12" role="from"/>
      <member type="node" ref="34" role="via"/>
      <member type="way" ref="56" role="to"/>
      <tag k="type" v="restriction"/><tag k="restriction" v="unmodelled"/>
    </relation></osm>""")
    closures = RestrictionClosures()
    closures.apply_file(str(source))
    assert closures.ways == {12, 56}
    assert set(closures.relations) == {1}


def test_native_passthrough_keeps_all_objects_and_way_locations(tmp_path):
    import osmium

    from prepare_country import enrich_extract

    source = tmp_path / "source.osm"
    source.write_text("""<osm version="0.6">
      <node id="1" version="1" lat="50" lon="4"/>
      <node id="2" version="1" lat="50.1" lon="4.1"/>
      <way id="3" version="1"><nd ref="1"/><nd ref="2"/><tag k="building" v="yes"/></way>
      <way id="4" version="1"><nd ref="1"/><nd ref="2"/><tag k="highway" v="residential"/></way>
      <relation id="5" version="1"><tag k="type" v="route"/></relation>
      <relation id="6" version="1"/>
    </osm>""")
    output = tmp_path / "result.osm.pbf"
    visited = []
    with osmium.SimpleWriter(output) as writer:

        class Handler:
            def way(self, way):
                assert all(node.location.valid() for node in way.nodes)
                visited.append(way.id)
                writer.add_way(way)

            def relation(self, relation):
                visited.append(relation.id)
                writer.add_relation(relation)

        enrich_extract(source, writer, Handler())
    assert visited == [4, 5]
    assert [obj.id for obj in osmium.FileProcessor(output)] == [1, 2, 3, 4, 5, 6]


def test_a_border_way_keeps_its_verified_sidepath_obligation(tmp_path, second_country):
    from types import SimpleNamespace

    import osmium

    from prepare_country import Enrich, RestrictionClosures

    source = tmp_path / "border.osm"
    source.write_text("""<osm version="0.6">
      <node id="1" version="1" lat="0.5" lon="1"/>
      <node id="2" version="1" lat="0.5" lon="1.1"/>
      <way id="3" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="residential"/></way>
    </osm>""")
    output = tmp_path / "result.osm.pbf"
    paths = SimpleNamespace(
        access=Access("ZZ"),
        adjacent=lambda points: ({"bromfiets": "mandatory"}, [99]),
    )
    with osmium.SimpleWriter(output) as writer:
        Enrich(
            writer,
            second_country,
            rules_for("ZZ"),
            box(1.05, 0, 2, 1),
            paths,
            RestrictionClosures(),
        ).apply_file(str(source), locations=True)
    ways = [dict(obj.tags) for obj in osmium.FileProcessor(output) if obj.is_way()]
    assert ways[0]["amgraph:country"] == "unsupported"
    assert ways[0]["amgraph:bromfiets"] == "no"
    assert ways[0]["amgraph:sidepaths"] == "99"


def test_dutch_authority_evidence_cannot_be_supplied_by_raw_osm(tmp_path):
    import osmium

    from official_access import Inject

    source = tmp_path / "source.osm"
    source.write_text("""<osm version="0.6">
      <node id="1" version="1" lat="52" lon="5"/>
      <node id="2" version="1" lat="52.1" lon="5.1"/>
      <way id="3" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="cycleway"/><tag k="amgraph:snorfiets" v="yes"/></way>
      <way id="4" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="cycleway"/><tag k="amgraph:bromfiets" v="yes"/></way>
    </osm>""")
    output = tmp_path / "result.osm.pbf"
    with osmium.SimpleWriter(output) as writer:
        Inject(writer, {4: ("yes", "no")}, box(4, 51, 6, 53)).apply_file(
            str(source), locations=True
        )
    ways = {obj.id: dict(obj.tags) for obj in osmium.FileProcessor(output) if obj.is_way()}
    assert "amgraph:snorfiets" not in ways[3]
    assert ways[3]["amgraph:country"] == "NL"
    assert ways[4]["amgraph:snorfiets"] == "yes"
    assert ways[4]["amgraph:bromfiets"] == "no"


def test_nl_acc_04_every_carriageway_in_the_municipality_is_kept_on_the_roadway(tmp_path):
    """NL-ACC-04 writes `on_roadway` on every carriageway inside the boundary.

    The length floor exists because a geometric match onto a junction stub is
    unreliable, and a wrong match would close a road. Whether a way lies inside
    Amsterdam or Utrecht is not a match; it is as certain for 5 m as for 5 km.
    Skipping the short pieces left 2,680 junction and bridge stubs in the two
    cities carrying their pre-decision `mofa=use_sidepath`, each one closing
    the only road the verkeersbesluit left the snorfiets, and trapped it in
    about a square kilometre of each city centre.
    """
    from collections import defaultdict

    from official_access import MIN_LENGTH_METRES, Match

    # About 10 m and about 200 m of latitude.
    short, long_ = 0.00009, 0.0018
    source = tmp_path / "source.osm"
    source.write_text(f"""<osm version="0.6">
      <node id="1" version="1" lat="52.0" lon="5.0"/>
      <node id="2" version="1" lat="{52.0 + short}" lon="5.0"/>
      <node id="3" version="1" lat="{52.0 + long_}" lon="5.0"/>
      <node id="4" version="1" lat="53.0" lon="6.0"/>
      <node id="5" version="1" lat="{53.0 + short}" lon="6.0"/>
      <way id="10" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="primary"/><tag k="mofa" v="use_sidepath"/></way>
      <way id="11" version="1"><nd ref="1"/><nd ref="3"/>
        <tag k="highway" v="primary"/><tag k="mofa" v="use_sidepath"/></way>
      <way id="12" version="1"><nd ref="4"/><nd ref="5"/>
        <tag k="highway" v="primary"/><tag k="mofa" v="use_sidepath"/></way>
      <way id="13" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="cycleway"/></way>
    </osm>""")
    municipality = box(4.9, 51.9, 5.1, 52.1)
    shapely.prepare(municipality)

    match = Match(defaultdict(list), defaultdict(list), municipality)
    match.apply_file(str(source), locations=True)

    assert short * 111_000 < MIN_LENGTH_METRES < long_ * 111_000
    assert match.verdict[10][0] == "on_roadway"  # the stub the floor used to skip
    assert match.verdict[11][0] == "on_roadway"
    # Outside the municipality the floor still guards every judgement it did.
    assert 12 not in match.verdict
    # A path is not a carriageway; lid 8 takes the snorfiets off it, not onto it.
    assert 13 not in match.verdict


def _road_and_path(tmp_path, lat, lon, road, path):
    """A carriageway and, 15 m beside it, a cycle path, both about 200 m long."""
    step, offset = 0.0005, 0.000135
    nodes, refs_road, refs_path = [], [], []
    for i in range(7):
        nodes.append(f'<node id="{100 + i}" version="1" lat="{lat}" lon="{lon + i * step / 2}"/>')
        nodes.append(
            f'<node id="{200 + i}" version="1" lat="{lat - offset}" lon="{lon + i * step / 2}"/>'
        )
        refs_road.append(f'<nd ref="{100 + i}"/>')
        refs_path.append(f'<nd ref="{200 + i}"/>')

    def tags(values):
        return "".join(f'<tag k="{k}" v="{v}"/>' for k, v in values.items())

    source = tmp_path / "source.osm"
    source.write_text(
        '<osm version="0.6">'
        + "".join(nodes)
        + f'<way id="20" version="1">{"".join(refs_road)}{tags(road)}</way>'
        + f'<way id="21" version="1">{"".join(refs_path)}{tags(path)}</way>'
        + "</osm>"
    )
    return source


def _overlay(source, municipality, register=None):
    """Run the three passes of official_access.py the way main() does."""
    from collections import defaultdict

    from amgraph_rules.countries.nl import ART5_LID8_EXEMPT_ROADS
    from official_access import CELL, ExemptCarriageways, Match, Paths

    signs = defaultdict(list)
    for lat, lon, code in register or ():
        signs[(int(lat / CELL), int(lon / CELL))].append((lat, lon, code))
    if municipality is not None:
        shapely.prepare(municipality)
    exempt = ExemptCarriageways(ART5_LID8_EXEMPT_ROADS)
    exempt.apply_file(str(source), locations=True)
    paths = Paths(signs, municipality, {}, exempt.index)
    paths.apply_file(str(source), locations=True)
    match = Match(defaultdict(list), paths.usable, municipality)
    match.apply_file(str(source), locations=True)
    return paths, match


UTRECHT_WEST = (52.0995, 5.0500)
G11_PATH = {"highway": "cycleway", "traffic_sign": "NL:G11", "mofa": "designated", "moped": "no"}
OBLIGED_ROAD = {"highway": "secondary", "bicycle": "use_sidepath", "oneway": "yes"}


def test_nl_acc_04_an_unnamed_g11_beside_a_road_utrecht_does_not_list_keeps_the_snorfiets(
    tmp_path,
):
    """Utrecht's art. 5 lid 8 decision names its roads, and the onderbord stands
    only there. Elsewhere art. 5 lid 1 holds: "Fietsers gebruiken het verplichte
    fietspad", so the snorfiets belongs on the G11 and not on the carriageway its
    obligation closes. A G11 that OSM leaves unnamed is told apart from the
    decision's solitary paths by the road it runs beside."""
    lat, lon = UTRECHT_WEST
    source = _road_and_path(tmp_path, lat, lon, {**OBLIGED_ROAD, "name": "Vleutensebaan"}, G11_PATH)
    paths, match = _overlay(source, box(4.97, 52.02, 5.20, 52.15))

    assert 21 not in paths.closed
    assert match.verdict.get(20, (None, None))[0] != "on_roadway"


def test_nl_acc_04_an_unnamed_g11_beside_a_listed_road_still_loses_the_snorfiets(tmp_path):
    lat, lon = UTRECHT_WEST
    source = _road_and_path(tmp_path, lat, lon, {**OBLIGED_ROAD, "name": "Vleutenseweg"}, G11_PATH)
    paths, match = _overlay(source, box(4.97, 52.02, 5.20, 52.15))

    assert paths.closed[21] == "roadway_only"
    assert match.verdict[20][0] == "on_roadway"


def test_nl_acc_04_a_solitary_unnamed_g11_in_utrecht_stays_closed(tmp_path):
    """Nothing beside it says which road it serves, and it may be one of the
    solitary paths the decision lists."""
    lat, lon = UTRECHT_WEST
    source = _road_and_path(tmp_path, lat, lon, {"highway": "footway"}, G11_PATH)
    paths, _ = _overlay(source, box(4.97, 52.02, 5.20, 52.15))

    assert paths.closed[21] == "roadway_only"


ZWOLLE = (52.5100, 6.0900)


def test_nl_acc_02_a_register_g11_on_an_unsigned_path_keeps_the_snorfiets_on_it(tmp_path):
    """Art. 5 lid 1 obliges the snorfiets onto a G11 wherever no art. 5 lid 8
    measure reaches it. Leaving the path closed makes the obligation beside it
    look like a deadlock, and the carriageway it bars would be opened."""
    lat, lon = ZWOLLE
    source = _road_and_path(
        tmp_path, lat, lon, {**OBLIGED_ROAD, "name": "Ceintuurbaan"}, {"highway": "cycleway"}
    )
    paths, match = _overlay(source, None, [(lat - 0.000135, lon + 0.0005, "G11")])

    assert paths.opened[21] == "yes"
    assert match.verdict.get(20, (None, None))[0] != "on_roadway"


def test_nl_acc_02_a_register_g13_leaves_the_snorfiets_the_roadway(tmp_path):
    """Art. 5 lid 2: no verplicht fietspad, so the rijbaan."""
    lat, lon = ZWOLLE
    source = _road_and_path(
        tmp_path, lat, lon, {**OBLIGED_ROAD, "name": "Ceintuurbaan"}, {"highway": "cycleway"}
    )
    paths, match = _overlay(source, None, [(lat - 0.000135, lon + 0.0005, "G13")])

    assert 21 not in paths.opened
    assert match.verdict[20][0] == "on_roadway"


def test_nl_acc_04_a_register_g11_in_amsterdam_loses_the_snorfiets(tmp_path):
    lat, lon = 52.3600, 4.8800
    source = _road_and_path(
        tmp_path, lat, lon, {**OBLIGED_ROAD, "name": "Overtoom"}, {"highway": "cycleway"}
    )
    paths, match = _overlay(
        source, box(4.72, 52.27, 5.08, 52.44), [(lat - 0.000135, lon + 0.0005, "G11")]
    )

    assert paths.closed[21] == "roadway_only"
    assert 21 not in paths.opened
    assert match.verdict[20][0] == "on_roadway"
