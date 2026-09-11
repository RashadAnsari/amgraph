"""A combined graph has no implicit country or input-order preference."""

import sys
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "infra"))

from amgraph_rules.countries import modelled_countries
from prepare_country import Access


def test_pedelec_carrier_is_stable_across_supported_borders():
    assert {c.vehicle("speed_pedelec").carrier.value for c in modelled_countries()} == {"taxi"}


def test_each_country_has_exactly_the_same_carriers_in_lua_and_python():
    for country in modelled_countries():
        access = Access(country.code)
        assert dict(access.classes) == {v.code: v.carrier.value for v in country.classes}


def test_border_geometry_is_not_assigned_to_the_first_country():
    from merge_countries import Territories

    for boundaries in (
        {"NL": box(0, 0, 1, 1), "BE": box(1, 0, 2, 1)},
        {"BE": box(1, 0, 2, 1), "NL": box(0, 0, 1, 1)},
    ):
        territories = Territories(boundaries)
        assert territories.countries(Point(0.5, 0.5)) == ("NL",)
        assert territories.countries(Point(1, 0.5)) == ("BE", "NL")
        assert territories.countries(LineString([(0.5, 0.5), (1.5, 0.5)])) == ("BE", "NL")
        assert territories.countries(LineString([(0.5, 0.5), (2.5, 0.5)])) == ()


def test_a_boundary_gap_is_not_repaired_into_supported_territory():
    from merge_countries import Territories

    territories = Territories({"NL": box(0, 0, 1, 1), "BE": box(1.001, 0, 2, 1)})
    assert territories.countries(LineString([(0.5, 0.5), (1.5, 0.5)])) == ()


def test_border_access_is_the_intersection_of_every_applicable_law():
    access = Access("BE")
    version = access.country.rules_version
    tags = {
        "amgraph:country": "BE;NL",
        "highway": "residential",
        "maxspeed": "30",
        "amgraph:BE:amgraph:rules": version,
        "amgraph:BE:highway": "residential",
        "amgraph:BE:maxspeed": "30",
        "amgraph:NL:highway": "residential",
        "amgraph:NL:maxspeed": "30",
    }

    def flags():
        return dict(access.lua.carrier_flags(access.runtime.table_from(tags)))

    assert flags()["taxi_forward"] == "true"
    tags["amgraph:BE:traffic_sign"] = "BE:C9"
    assert set(flags().values()) == {"false"}
    del tags["amgraph:BE:traffic_sign"]
    tags["amgraph:NL:traffic_sign"] = "NL:C13"
    assert flags()["taxi_forward"] == "false"
    assert flags()["truck_forward"] == "true"


@pytest.mark.parametrize("attribution", ["", "NL;XX", "BE;", "NL;NL"])
def test_malformed_or_unknown_border_attribution_cannot_borrow_a_country(attribution):
    access = Access("BE")
    flags = access.lua.carrier_flags(
        access.runtime.table_from(
            {"amgraph:country": attribution, "highway": "residential", "maxspeed": "30"}
        )
    )
    assert set(flags.values()) == {"false"}


@pytest.mark.parametrize("missing_owner", [False, True])
@pytest.mark.parametrize("conflicting_relation", [False, True])
def test_merge_selects_the_geographic_owner_and_attributes_shared_nodes(
    tmp_path, conflicting_relation, missing_owner
):
    import json

    import osmium
    from shapely.geometry import mapping

    from merge_countries import merge, source_paths
    from prepare_country import digest

    sources = source_paths(tmp_path)
    for code, (directory, extract, module) in sources.items():
        (directory / "boundaries").mkdir(parents=True)
        geometry = box(0, 0, 1, 1) if code == "NL" else box(1, 0, 2, 1)
        (directory / "boundaries" / module.BOUNDARY_FILENAME).write_text(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {"type": "Feature", "properties": {}, "geometry": mapping(geometry)}
                    ],
                }
            )
        )
        (directory / "boundaries/legal-zones.geojson").write_text(json.dumps({"features": []}))
        with osmium.SimpleWriter(str(extract)) as writer:
            for identifier, lon in ((1, 0.2), (2, 0.8), (3, 1.0), (4, 1.2)):
                writer.add_node(
                    osmium.osm.mutable.Node(id=identifier, version=1, location=(lon, 0.5))
                )
            for identifier, nodes in ((10, [1, 2]), (11, [2, 3, 4])):
                if missing_owner and code == "BE" and identifier == 11:
                    continue
                tags = {"highway": "residential", "maxspeed": "30", "amgraph:country": code}
                if code == "BE":
                    tags.update(
                        {"amgraph:rules": module.RULES_VERSION, "amgraph:bromfiets_klasse_a": "no"}
                    )
                writer.add_way(
                    osmium.osm.mutable.Way(id=identifier, version=1, nodes=nodes, tags=tags)
                )
            writer.add_relation(
                osmium.osm.mutable.Relation(
                    id=20,
                    version=1,
                    members=[("w", 11 if conflicting_relation and code == "BE" else 10, "")],
                    tags={"type": "route", "route": "bicycle"},
                )
            )
        (directory / "audit.json").write_text(
            json.dumps(
                {
                    "country": code,
                    "rules_version": module.RULES_VERSION,
                    "enriched_sha256": digest(extract),
                    "ways": 1 if missing_owner and code == "BE" else 2,
                }
            )
        )
    if conflicting_relation:
        with pytest.raises(ValueError, match="conflicting relation members"):
            merge(tmp_path)
        assert not (tmp_path / "all-countries-official.osm.pbf").exists()
        return
    result = merge(tmp_path)
    objects = {}
    for obj in osmium.FileProcessor(result):
        objects[obj.id] = dict(obj.tags)
    assert objects[3]["amgraph:country"] == "BE;NL"
    assert objects[10]["amgraph:country"] == "NL"
    assert "amgraph:bromfiets_klasse_a" not in objects[10]
    if missing_owner:
        assert objects[11]["amgraph:country"] == "unsupported"
        access = Access("BE")
        flags = dict(access.lua.carrier_flags(access.runtime.table_from(objects[11])))
        assert set(flags.values()) == {"false"}
        return
    assert objects[11]["amgraph:country"] == "BE;NL"
    access = Access("BE")
    flags = dict(access.lua.carrier_flags(access.runtime.table_from(objects[11])))
    assert flags["moped_forward"] == "false"
    assert flags["taxi_forward"] == "true"


def test_an_external_border_is_not_assumed_to_be_supported_on_both_sides():
    from merge_countries import Territories

    territories = Territories({"NL": box(0, 0, 1, 1), "BE": box(1, 0, 2, 1)})
    assert territories.countries(Point(0, 0.5)) == ()
    assert territories.countries(LineString([(0, 0.2), (0, 0.8)])) == ()


def test_package_contains_every_country_in_one_zip_and_rejects_tampering(tmp_path):
    import json
    import zipfile

    from package_graph import package
    from prepare_country import digest

    names = (
        "valhalla.json",
        "valhalla/tiles.tar",
        "valhalla/admin.sqlite",
        "boundaries/be.geojson",
        "boundaries/nl.geojson",
        "boundaries/legal-zones.geojson",
    )
    for name in names:
        path = tmp_path / name
        path.parent.mkdir(exist_ok=True)
        path.write_text(name)
    manifest = {
        "countries": {
            c.code: {
                "boundary": f"boundaries/{c.code.lower()}.geojson",
                "boundary_sha256": digest(tmp_path / f"boundaries/{c.code.lower()}.geojson"),
            }
            for c in modelled_countries()
        },
        "legal_zones": "boundaries/legal-zones.geojson",
        "legal_zones_sha256": digest(tmp_path / "boundaries/legal-zones.geojson"),
        "build": {"tiles_sha256": digest(tmp_path / "valhalla/tiles.tar")},
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    output = tmp_path / "graph.zip"
    package(tmp_path, output)
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {*names, "manifest.json", "NOTICE.md"}
    before = output.read_bytes()
    (tmp_path / "boundaries/be.geojson").write_text("changed")
    with pytest.raises(ValueError, match="content changed"):
        package(tmp_path, output)
    assert output.read_bytes() == before
    del manifest["countries"]["BE"]
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="every supported country"):
        package(tmp_path, output)


def test_batched_node_attribution_preserves_border_and_unknown_decisions():
    from merge_countries import Territories

    territories = Territories({"NL": box(0, 0, 1, 1), "BE": box(1, 0, 2, 1)})
    coordinates = [(0, 0.5), (0.5, 0.5), (1, 0.5), (1.5, 0.5), (2.1, 0.5)]
    assert territories.points(coordinates) == [
        territories.countries(Point(*p)) for p in coordinates
    ]


def test_compaction_preserves_access_nodes_roads_and_relation_members(tmp_path):
    import osmium

    from compact_source import compact

    source = tmp_path / "source.osm"
    source.write_text("""<osm version="0.6">
      <node id="1" version="1" lat="50" lon="4"><tag k="traffic_sign" v="BE:C9"/></node>
      <node id="2" version="1" lat="50" lon="4.1"/>
      <node id="3" version="1" lat="50.1" lon="4"/>
      <node id="4" version="1" lat="50.1" lon="4.1"/>
      <node id="5" version="1" lat="50.2" lon="4"/>
      <node id="6" version="1" lat="50.2" lon="4.1"/>
      <way id="10" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="residential"/><tag k="amgraph:country" v="BE"/></way>
      <way id="11" version="1"><nd ref="3"/><nd ref="4"/><tag k="building" v="yes"/></way>
      <way id="12" version="1"><nd ref="5"/><nd ref="6"/><tag k="building" v="yes"/></way>
      <way id="13" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="highway" v="service"/><tag k="building" v="yes"/></way>
      <way id="14" version="1"><nd ref="1"/><nd ref="2"/>
        <tag k="route" v="ferry"/><tag k="building" v="yes"/></way>
      <relation id="20" version="1"><member type="way" ref="12" role="outer"/>
        <tag k="type" v="multipolygon"/></relation>
      <relation id="21" version="1"><member type="relation" ref="20" role="subarea"/>
        <tag k="type" v="boundary"/></relation>
    </osm>""")
    output = tmp_path / "compact.osm.pbf"
    compact(source, output, 2)
    nodes, ways, relations = {}, {}, {}
    for obj in osmium.FileProcessor(output).with_locations():
        if obj.is_node():
            nodes[obj.id] = dict(obj.tags)
        elif obj.is_way():
            assert all(node.location.valid() for node in obj.nodes)
            ways[obj.id] = dict(obj.tags)
        else:
            relations[obj.id] = [(member.type, member.ref) for member in obj.members]
    assert set(nodes) == {1, 2, 5, 6}
    assert nodes[1]["traffic_sign"] == "BE:C9"
    assert set(ways) == {10, 12, 13, 14}
    assert ways[10]["amgraph:country"] == "BE"
    assert relations == {20: [("w", 12)], 21: [("r", 20)]}
    before = output.read_bytes()
    with pytest.raises(ValueError, match="audited highway"):
        compact(source, output, 3)
    assert output.read_bytes() == before


def test_a_manifest_cannot_certify_two_disconnected_country_graphs(tmp_path):
    import importlib
    import json
    import shutil
    from importlib.metadata import version

    import manifest
    from prepare_country import ROOT, digest

    (tmp_path / "lua/countries").mkdir(parents=True)
    (tmp_path / "valhalla").mkdir()
    (tmp_path / "boundaries").mkdir()
    (tmp_path / "valhalla/tiles.tar").write_text("a built graph")
    names = ["access.lua", "amgraph.lua", "countries/be.lua", "countries/nl.lua"]
    for name in names:
        shutil.copyfile(ROOT / "valhalla/lua" / name, tmp_path / "lua" / name)
    for name in ("be", "nl", "legal-zones"):
        (tmp_path / f"boundaries/{name}.geojson").write_text("{}")
    stamp = {
        "countries": {c.code: {"rules_version": c.rules_version} for c in modelled_countries()},
        "lua_sha256": {name: digest(tmp_path / "lua" / name) for name in names},
        "tiles_sha256": digest(tmp_path / "valhalla/tiles.tar"),
        "rules_package_version": version("amgraph-rules"),
    }
    (tmp_path / "build.json").write_text(json.dumps(stamp))
    routes = {
        "passed": True,
        "tiles_sha256": stamp["tiles_sha256"],
        "countries": {
            c.code: {v.code: {"attempted": 10, "successful": 10} for v in c.classes}
            for c in modelled_countries()
        },
        "borders": {},
    }
    (tmp_path / "routes.json").write_text(json.dumps(routes))
    with pytest.raises(ValueError, match="border crossing"):
        manifest.build(1, "test", tmp_path)
    for country in modelled_countries():
        module = importlib.import_module(f"amgraph_rules.countries.{country.code.lower()}")
        for neighbour, pairs in getattr(module, "BORDER_ROUTE_CHECKS", {}).items():
            for vehicle in country.classes:
                routes["borders"][f"{country.code}-{neighbour}/{vehicle.carrier}"] = [
                    {"ok": True} for _ in pairs
                ]
    (tmp_path / "routes.json").write_text(json.dumps(routes))
    routes["access_probes"] = {
        country.code: {
            f"{a}/{b}": {"passed": True, "way_ids": [1]}
            for a, b in importlib.import_module(
                f"amgraph_rules.countries.{country.code.lower()}"
            ).ACCESS_PROBES
        }
        for country in modelled_countries()
    }
    (tmp_path / "routes.json").write_text(json.dumps(routes))
    result = manifest.build(1, "test", tmp_path)
    assert set(result["countries"]) == {"BE", "NL"}
    assert "country" not in result
    del stamp["countries"]["BE"]
    (tmp_path / "build.json").write_text(json.dumps(stamp))
    with pytest.raises(ValueError, match="supported country set"):
        manifest.build(1, "test", tmp_path)
