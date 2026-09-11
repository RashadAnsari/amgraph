"""Belgian access assertions pin the primary-source rules in docs/countries/be.md."""

from pathlib import Path

import pytest
from lupa.lua54 import LuaRuntime

from amgraph_rules.countries import rules_for

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def belgium():
    runtime = LuaRuntime(unpack_returned_tuples=True)
    access = runtime.eval("function(path) return assert(loadfile(path))() end")(
        str(ROOT / "valhalla/lua/access.lua")
    )
    country = access.prepare(runtime.execute((ROOT / "valhalla/lua/countries/be.lua").read_text()))
    return runtime, access, country


def flags(belgium, **tags):
    runtime, access, country = belgium
    tags["amgraph:rules"] = country.rules_version
    return dict(access.carrier_flags(runtime.table_from(tags), country))


def test_be_release_gate(belgium):
    runtime, access, _ = belgium
    assert rules_for("BE").code == "BE"
    result = access.carrier_flags(
        runtime.table_from({"highway": "residential", "amgraph:country": "BE"})
    )
    assert set(result.values()) == {"false"}


@pytest.mark.parametrize(
    ("sign", "barred"),
    [
        ("M7", "motorcycle"),
        ("M15", "taxi"),
        ("M16", "taxi"),
        ("M16", "motorcycle"),
    ],
)
def test_be_acc_05_subplates_cannot_be_overridden_by_access(belgium, sign, barred):
    result = flags(
        belgium,
        highway="cycleway",
        traffic_sign=f"BE:D7,BE:{sign}",
        moped="yes",
        speed_pedelec="yes",
    )
    assert result[f"{barred}_forward"] == "false"


@pytest.mark.parametrize("sign", ["F5", "F9", "D11", "D13", "F99a", "F99c", "F103"])
def test_be_acc_06_reserved_infrastructure_is_not_opened_by_generic_tags(belgium, sign):
    result = flags(belgium, highway="residential", traffic_sign=f"BE:{sign}", motor_vehicle="yes")
    assert set(result.values()) == {"false"}


def test_be_acc_02_sign_alias_d07_is_not_an_unsigned_path(belgium):
    assert flags(belgium, highway="cycleway", traffic_sign="BE:D07")["motorcycle_forward"] == "true"


@pytest.mark.parametrize("sign", ["C21[3.5]", "C25", "C27", "C29", "C24a", "ZZZ"])
def test_be_unknown_restrictions_do_not_open_a_way(belgium, sign):
    assert set(flags(belgium, highway="residential", traffic_sign=f"BE:{sign}").values()) == {
        "false"
    }


def test_be_spd_02_belgian_warning_sign_does_not_borrow_dutch_speed_meaning(belgium):
    assert flags(belgium, highway="residential", traffic_sign="BE:A1")["taxi_forward"] == "true"
    assert flags(belgium, highway="residential", traffic_sign="BE:C43")["taxi_forward"] == "false"


@pytest.mark.parametrize(
    ("tags", "limit"),
    [
        ({"highway": "residential"}, "30"),
        ({"highway": "living_street", "maxspeed": "50"}, "20"),
        ({"highway": "residential", "traffic_sign": "BE:F111", "maxspeed": "50"}, "30"),
        ({"highway": "cycleway", "traffic_sign": "BE:D9", "maxspeed": "70"}, "30"),
        ({"highway": "residential", "traffic_sign": "BE:C43[10]"}, "10"),
    ],
)
def test_be_spd_02_enrichment_carries_the_binding_speed(tags, limit):
    from amgraph_rules.countries.be import enrich_way

    assert enrich_way(tags, {}).get("maxspeed") == limit


def test_be_acc_03_only_a_usable_sidepath_creates_an_obligation():
    from amgraph_rules.countries.be import enrich_way

    tags = {"highway": "primary", "maxspeed": "70"}
    adjacent = {"bromfiets_klasse_a": "optional", "speed_pedelec": "optional"}
    result = enrich_way(tags, adjacent)
    assert result["amgraph:bromfiets_klasse_a"] == "no"
    assert result["amgraph:speed_pedelec"] == "no"
    assert result.get("amgraph:bromfiets_klasse_b") is None
    assert enrich_way({**tags, "maxspeed": "50"}, adjacent).get("amgraph:speed_pedelec") is None


def test_be_def_01_carriers_agree_across_languages(belgium):
    from amgraph_rules.countries.be import CLASSES, RULES_VERSION

    _, _, country = belgium
    actual = {item.code: item.carrier for item in country.classes.values()}
    assert actual == {vehicle.code: vehicle.carrier.value for vehicle in CLASSES}
    assert len(set(actual.values())) == 4
    assert country.rules_version == RULES_VERSION


@pytest.mark.parametrize("speed", [None, "30", "50", "70", "90"])
@pytest.mark.parametrize(
    ("sign", "expected"),
    [
        ("D7", (True, True, True, False)),
        ("D9", (True, False, True, False)),
        ("D10", (False, False, False, False)),
    ],
)
def test_be_acc_02_cycle_sign_rights_do_not_depend_on_path_speed(belgium, speed, sign, expected):
    tags = {"highway": "cycleway", "traffic_sign": f"BE:{sign}"}
    if speed is not None:
        tags["maxspeed"] = speed
    result = flags(belgium, **tags)
    assert (
        tuple(
            result[f"{carrier}_forward"] == "true"
            for carrier in ("moped", "motorcycle", "taxi", "truck")
        )
        == expected
    )


@pytest.mark.parametrize("highway", ["cycleway", "path", "residential"])
@pytest.mark.parametrize("sign", ["D7", "D9", "D10"])
def test_be_acc_02_cycle_sign_cannot_put_a_quad_on_the_path(belgium, highway, sign):
    result = flags(belgium, highway=highway, traffic_sign=f"BE:{sign}", motorcar="yes")
    assert result["truck_forward"] == "false"


def test_be_acc_02_d9_does_not_admit_klasse_b_with_a_conflicting_tag(belgium):
    assert (
        flags(belgium, highway="cycleway", traffic_sign="BE:D9", moped="yes")["motorcycle_forward"]
        == "false"
    )


@pytest.mark.parametrize("carrier", ["moped", "motorcycle", "taxi", "truck"])
@pytest.mark.parametrize(
    "tags",
    [
        {"highway": "motorway"},
        {"highway": "motorway_link"},
        {"highway": "primary", "motorroad": "yes"},
    ],
)
def test_be_acc_01_motorways_and_motorroads_are_barred(belgium, carrier, tags):
    result = flags(belgium, **tags, mofa="yes", moped="yes", speed_pedelec="yes", motorcar="yes")
    assert result[f"{carrier}_forward"] == "false"


@pytest.mark.parametrize(
    ("key", "carrier"),
    [
        ("mofa", "moped"),
        ("moped", "motorcycle"),
        ("speed_pedelec", "taxi"),
    ],
)
def test_be_acc_03_sidepath_refusal_is_class_specific(belgium, key, carrier):
    result = flags(belgium, highway="residential", **{key: "use_sidepath"})
    assert result[f"{carrier}_forward"] == "false"
    assert result["truck_forward"] == "true"


def test_be_acc_03_no_sidepath_evidence_keeps_the_carriageway(belgium):
    result = flags(belgium, highway="residential")
    assert all(
        result[f"{carrier}_forward"] == "true"
        for carrier in ("moped", "motorcycle", "taxi", "truck")
    )


def test_be_unknown_unsigned_cycle_path_is_closed(belgium):
    assert set(flags(belgium, highway="cycleway").values()) == {"false"}


def test_be_acc_04_c9_bars_all_mopeds_including_the_quad(belgium):
    assert set(flags(belgium, highway="residential", traffic_sign="BE:C9").values()) == {"false"}


def test_be_acc_04_c5_only_bars_the_four_wheeler(belgium):
    result = flags(belgium, highway="residential", traffic_sign="BE:C5")
    assert result["truck_forward"] == "false"
    assert result["motorcycle_forward"] == "true"
    assert result["taxi_forward"] == "true"


def test_be_acc_04_directional_entry_sign_and_node(belgium):
    runtime, access, country = belgium
    result = flags(belgium, highway="residential", **{"traffic_sign:forward": "BE:C1"})
    assert result["taxi_forward"] == "false"
    assert result["taxi_backward"] == "true"
    assert not any(
        access.node_classes(runtime.table_from({"traffic_sign": "BE:C1"}), country).values()
    )


def test_be_acc_02_pedelec_has_its_own_access_and_oneway(belgium):
    result = flags(
        belgium, highway="residential", moped="no", oneway="yes", **{"oneway:speed_pedelec": "no"}
    )
    assert result["motorcycle_forward"] == "false"
    assert result["taxi_backward"] == "true"


def test_be_spd_01_class_caps_and_cycle_exclusion():
    from amgraph_rules.countries.be import CLASSES

    assert [vehicle.construction_limit_kph for vehicle in CLASSES] == [25, 45, 45, 45]
    assert CLASSES[-1].speeds.cycle_path_built_up is None
    assert CLASSES[-1].speeds.cycle_path_rural is None


@pytest.mark.parametrize("sign", ["C3-50", "C5[3.5]", "D9[2]", "C43[5.5]", "F4a-30"])
def test_be_acc_04_and_spd_02_numeric_suffix_cannot_evade_a_restriction(belgium, sign):
    assert set(
        flags(belgium, highway="residential", maxspeed="50", traffic_sign=f"BE:{sign}").values()
    ) == {"false"}


@pytest.mark.parametrize("sign,limit", [("C43[30]", "30"), ("F4a-30", "30"), ("C45-70", "70")])
def test_be_spd_02_resolved_speed_values_keep_road_and_node_access(belgium, sign, limit):
    runtime, access, country = belgium
    assert (
        flags(belgium, highway="residential", maxspeed=limit, traffic_sign=f"BE:{sign}")[
            "taxi_forward"
        ]
        == "true"
    )
    assert all(
        access.node_classes(runtime.table_from({"traffic_sign": f"BE:{sign}"}), country).values()
    )


@pytest.mark.parametrize("key", ["zone:maxspeed", "maxspeed:type", "source:maxspeed"])
def test_be_spd_02_an_implicit_zone_cannot_be_replaced_with_a_faster_default(key):
    from amgraph_rules.countries.be import enrich_way

    assert enrich_way({"highway": "residential", key: "BE:zone:10"}, {})["maxspeed"] == "10"
    assert (
        enrich_way({"highway": "residential", key: "unreadable"}, {})["amgraph:unreadable_speed"]
        == "yes"
    )


@pytest.mark.parametrize(
    "hint,limit",
    [
        ("BE-BRU:urban", 30),
        ("BE-VLG:urban", 50),
        ("BE-WAL:urban", 50),
        ("BE:urban", 30),
        ("BE-BRU:rural", 70),
        ("BE-WAL:rural", 70),
        ("BE-VLG:rural", 70),
        ("BE:zone30", 30),
        ("BE-VLG:zone50", 50),
        ("zone70", 70),
        ("BE:living_street", 20),
        ("BE:cyclestreet", 30),
    ],
)
def test_be_spd_02_verified_regional_and_zone_hints(hint, limit):
    from amgraph_rules.countries.be import enrich_way

    result = enrich_way({"highway": "residential", "maxspeed": "90", "source:maxspeed": hint}, {})
    assert "amgraph:unreadable_speed" not in result
    assert float(result["maxspeed"]) == limit
    slower = enrich_way({"highway": "residential", "maxspeed": "10", "source:maxspeed": hint}, {})
    assert slower["maxspeed"] == "10"


@pytest.mark.parametrize("sign", ["F17", "F18"])
def test_be_acc_06_an_unresolved_reserved_lane_cannot_borrow_taxi_permission(belgium, sign):
    assert set(
        flags(belgium, highway="residential", traffic_sign=f"BE:{sign}", taxi="yes").values()
    ) == {"false"}


def test_be_acc_06_directional_reserved_lane_sign_reaches_the_direction_flags(belgium):
    result = flags(belgium, **{"highway": "residential", "traffic_sign:forward": "BE:F18"})
    assert result["taxi_forward"] == "false"
    assert result["taxi_backward"] == "true"
