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
        <tag k="highway" v="cycleway"/><tag k="amgraph:bromfiets" v="footpath_g12a"/></way>
      <way id="4" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="cycleway"/><tag k="amgraph:bromfiets" v="footpath_g12a"/></way>
    </osm>""")
    output = tmp_path / "result.osm.pbf"
    with osmium.SimpleWriter(output) as writer:
        Inject(writer, {4: "no"}, box(4, 51, 6, 53)).apply_file(str(source), locations=True)
    ways = {obj.id: dict(obj.tags) for obj in osmium.FileProcessor(output) if obj.is_way()}
    assert "amgraph:bromfiets" not in ways[3]
    assert ways[3]["amgraph:country"] == "NL"
    assert ways[4]["amgraph:bromfiets"] == "no"


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


def _match(source):
    """Run the cycle-path and matching passes of official_access.py."""
    from collections import defaultdict

    from official_access import Match, Paths

    paths = Paths({}, {})
    paths.apply_file(str(source), locations=True)
    match = Match(defaultdict(list), paths.usable)
    match.apply_file(str(source), locations=True)
    return match


OBLIGED_ROAD = {"highway": "secondary", "moped": "use_sidepath"}


def test_nl_acc_02_a_sidepath_obligation_beside_a_g12a_stands(tmp_path):
    """Art. 6 lid 1: the bromfiets belongs on the fiets/bromfietspad beside."""
    source = _road_and_path(
        tmp_path, 52.51, 6.09, OBLIGED_ROAD, {"highway": "cycleway", "traffic_sign": "NL:G12a"}
    )
    assert 20 not in _match(source).verdict


def test_nl_acc_02_a_sidepath_obligation_beside_a_path_it_may_not_use_is_lifted(tmp_path):
    """Art. 6 lid 2: "Zij gebruiken de rijbaan indien een fiets/bromfietspad
    ontbreekt." Closing both would leave the bromfiets nowhere lawful."""
    source = _road_and_path(
        tmp_path, 52.51, 6.09, OBLIGED_ROAD, {"highway": "cycleway", "traffic_sign": "NL:G11"}
    )
    assert _match(source).verdict[20] == "on_roadway"


def test_nl_acc_02_a_sidepath_obligation_with_no_path_beside_is_left_to_osm(tmp_path):
    source = _road_and_path(tmp_path, 52.51, 6.09, OBLIGED_ROAD, {"highway": "footway"})
    assert 20 not in _match(source).verdict
