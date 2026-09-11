"""Belgian classes, statutory constraints and extract-enrichment policy.

Every legal rule is quoted and dated in docs/rules.md §11. Geometry and PBF
handling belong to infra/prepare_country.py; the interpretation belongs here.
"""

import re
from datetime import date

from amgraph_rules.profiles import Carrier, Powertrain
from amgraph_rules.rules import (
    BoundaryDocument,
    ClassSpeeds,
    CountryRules,
    MunicipalZone,
    Plate,
    SearchBounds,
    VehicleClass,
)

RULES_VERSION = "be-2026-09-09.3"

# BE-PLATE-01. This is a screen approximation of ruby red, not a claim that
# the statute specifies an sRGB colour. Plate validates the measured contrast.
_PLATE = Plate(background="#FFFFFF", foreground="#861A22")

# BE-DEF-01, BE-SPD-01. The A/B scooter profiles cover two-wheelers only;
# three-wheelers need a separate review. A pedelec's 45 is its assistance
# cut-off and our routing cap, not an absolute statutory speed prohibition.
# The cycle cap of 30 avoids distinguishing regional D9 limits in the client.
CLASSES: tuple[VehicleClass, ...] = (
    VehicleClass(
        code="bromfiets_klasse_a",
        carrier=Carrier.MOPED,
        construction_limit_kph=25,
        speeds=ClassSpeeds(roadway=25, cycle_path_built_up=25, cycle_path_rural=25),
        plate=_PLATE,
        marker="scooter",
        powertrain_matters=True,
        names={
            "en": "Class A moped (two wheels)",
            "nl": "Tweewielige bromfiets klasse A",
            "fr": "Cyclomoteur classe A à deux roues",
        },
    ),
    VehicleClass(
        code="bromfiets_klasse_b",
        carrier=Carrier.MOTORCYCLE,
        construction_limit_kph=45,
        speeds=ClassSpeeds(roadway=45, cycle_path_built_up=30, cycle_path_rural=30),
        plate=_PLATE,
        marker="scooter",
        powertrain_matters=True,
        names={
            "en": "Class B moped (two wheels)",
            "nl": "Tweewielige bromfiets klasse B",
            "fr": "Cyclomoteur classe B à deux roues",
        },
    ),
    VehicleClass(
        code="speed_pedelec",
        carrier=Carrier.TAXI,
        construction_limit_kph=45,
        speeds=ClassSpeeds(roadway=45, cycle_path_built_up=30, cycle_path_rural=30),
        plate=_PLATE,
        marker="pedelec",
        powertrain_matters=True,
        names={"en": "Speed pedelec", "nl": "Speed pedelec", "fr": "Speed pedelec"},
    ),
    VehicleClass(
        code="lichte_vierwieler",
        carrier=Carrier.TRUCK,
        construction_limit_kph=45,
        speeds=ClassSpeeds(roadway=45, cycle_path_built_up=None, cycle_path_rural=None),
        plate=_PLATE,
        marker="microcar",
        powertrain_matters=True,
        names={"en": "Light quadricycle", "nl": "Lichte vierwieler", "fr": "Quadricycle léger"},
    ),
)

# BE-LEZ-01. The API knows combustion versus electric, not diesel versus
# petrol. Refusing combustion throughout the region covers the diesel ban
# without pretending every combustion moped is prohibited by the statute.
MUNICIPAL_ZONES = {
    "Brussels-Capital Region": MunicipalZone(
        municipality_id="04000",
        powertrain_classes=frozenset(vehicle.code for vehicle in CLASSES),
        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
        blocked_classes=frozenset(),
    ),
}

BELGIUM = CountryRules(
    code="BE",
    name="Belgium",
    classes=CLASSES,
    # No class's rights are a subset of all the others: guessing a quad for a
    # klasse A rider can put them on a roadway with a compulsory sidepath.
    default_class=None,
    municipal_zones=MUNICIPAL_ZONES,
    address_search_bounds=SearchBounds(south=49.49, north=51.51, west=2.54, east=6.41),
    boundary=BoundaryDocument(properties={"niscode": "01000", "namedut": "België"}, geocoder=""),
    rules_version=RULES_VERSION,
    source="KB 1 december 1975; regional LEZ legislation; docs/rules.md §11",
    valid_until=date(2027, 6, 1),
)

EXTRACT_URL = "https://download.geofabrik.de/europe/belgium-latest.osm.pbf"
BOUNDARY_URL = (
    "https://ac.ngi.be/remoteclient-open/ngi-standard-open/Vectordata/"
    "TerritorialDivisions/TerritorialDivisions-AdminVector/"
    "fb1e2993-2020-428c-9188-eb5f75e284b9_x-shapefile_4326.zip"
)
BOUNDARY_LAYER = "belgianterritory_4326"
ZONE_LAYER = "region_4326"
ZONE_ID_KEY = "niscode"
BOUNDARY_FILENAME = "belgium.geojson"

# Coordinates are verification fixtures, not legal boundaries. Cover urban,
# rural and inter-city connectivity in all three regions.
ROUTE_CHECKS = (
    ((51.2194, 4.4025), (51.2253, 4.4152)),
    ((51.0543, 3.7174), (51.0443, 3.7270)),
    ((50.8503, 4.3517), (50.8610, 4.3600)),
    ((50.6326, 5.5797), (50.6410, 5.5700)),
    ((50.4674, 4.8718), (50.4750, 4.8600)),
    ((50.8798, 4.7005), (50.8900, 4.7100)),
    ((50.9300, 5.3378), (50.9410, 5.3510)),
    ((51.2089, 3.2242), (51.2190, 3.2310)),
    ((50.8798, 4.7005), (51.0259, 4.4776)),
    ((50.4674, 4.8718), (50.5660, 4.6910)),
)


def signs(tags: dict[str, str]) -> set[str]:
    result = set()
    for key in ("traffic_sign", "traffic_sign:forward", "traffic_sign:backward"):
        for token in re.split("[;,]", tags.get(key, "")):
            token = token.strip().removeprefix("BE:")
            token = re.sub(r"^([A-Z])0+(\d)", r"\1\2", token)
            result.add(token)
    return result - {""}


def numeric_speed(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*(km/h|kph|mph)?\s*", value)
    if not match:
        return None
    number = float(match[1])
    return number * 1.609344 if match[2] == "mph" else number


def sidepath_obligation(tags: dict[str, str], code: str) -> str:
    """BE-ACC-03/05: a path's permission is separate from its obligation."""
    tokens = signs(tags)
    if code == "bromfiets_klasse_a":
        return "mandatory"
    mandatory = {"bromfiets_klasse_b": {"M6", "M14"}, "speed_pedelec": {"M13", "M14"}}
    return "mandatory" if tokens & mandatory.get(code, set()) else "optional"


def enrich_way(source: dict[str, str], adjacent: dict[str, str]) -> dict[str, str]:
    """Add conservative whole-way evidence; never relax an explicit ban.

    Adjacent contains only classes for which the geometry pass has found an
    accessible cycle edge. It never interprets an unsigned path as mandatory.
    """
    tags = {key: value for key, value in source.items() if not key.startswith("amgraph:")}
    tokens = signs(tags)
    raw_speed = numeric_speed(tags.get("maxspeed"))
    roadway = tags.get("highway") not in {"cycleway", "path", "footway", "pedestrian"}
    if roadway:
        for code, obligation in adjacent.items():
            mandatory = code == "bromfiets_klasse_a" or obligation == "mandatory"
            # Unknown road speed could be above 50; both the permissive and
            # mandatory regimes admit the already-verified adjacent path.
            if mandatory or raw_speed is None or raw_speed > 50:
                tags[f"amgraph:{code}"] = "no"

    # BE-SPD-02. Without a mapped road limit, 30 is conservative throughout
    # the country. Living streets have their own lower cap. Numeric OSM limits
    # remain evidence; unknown/conditional strings stay unknown for Lua to bar.
    cap = 20 if tags.get("highway") == "living_street" or "F12a" in tokens else None
    if tokens & {"F4a", "F111", "F111zone", "D9", "A14", "F87"} or (
        tags.get("cyclestreet") == "yes"
        or tags.get("bicycle_road") == "yes"
        or tags.get("traffic_calming") is not None
    ):
        cap = min(cap or 30, 30)
    for suffix in ("", ":forward", ":backward"):
        for key in ("zone:maxspeed", "maxspeed:type", "source:maxspeed"):
            hint = tags.get(key + suffix)
            if hint is None:
                continue
            number = re.fullmatch(r"(?:BE(?:-BRU|-VLG|-WAL)?:)?(?:zone:?)?(\d+(?:\.\d+)?)", hint)
            regional = re.fullmatch(
                r"BE(?:-(BRU|VLG|WAL))?:(urban|rural|motorway|dual_carriageway|living_street|cyclestreet)",
                hint,
            )
            if number:
                cap = min(cap or 1000, float(number[1]))
            elif regional:
                region, kind = regional.groups()
                # BE-SPD-02: the shared rural cap is below every researched
                # regional default, including Walloon middle carriageways.
                limit = {
                    "urban": 50 if region in {"VLG", "WAL"} else 30,
                    "rural": 70,
                    "motorway": 120,
                    "dual_carriageway": 70,
                    "living_street": 20,
                    "cyclestreet": 30,
                }[kind]
                cap = min(cap or 1000, limit)
            elif hint not in {"survey", "estimated", "sign"} or (
                hint == "sign" and raw_speed is None
            ):
                tags["amgraph:unreadable_speed"] = "yes"
    for token in tokens:
        match = re.fullmatch(r"C43(?:\[(\d+)\]|-(\d+))", token)
        if match:
            cap = min(cap or 1000, int(match[1] or match[2]))
        elif token == "C43" and raw_speed is None:
            tags["amgraph:unreadable_speed"] = "yes"
    for suffix in ("", ":forward", ":backward"):
        key = "maxspeed" + suffix
        value = numeric_speed(tags.get(key))
        if value is not None:
            tags[key] = f"{min(value, cap) if cap is not None else value:g}"
        elif key not in tags and not suffix:
            tags[key] = f"{min(cap or 30, 30):g}"
    tags["amgraph:rules"] = RULES_VERSION
    return tags


def audit_access(tags: dict[str, str], flags: dict[str, str]) -> None:
    """Statutory invariants checked for every observed tag combination.

    This deliberately does not call the Lua sign/access helpers whose answers
    it checks. Rule IDs identify the quotations behind each assertion.
    """
    opened = {
        v.code
        for v in CLASSES
        if any(flags[f"{v.carrier}_{direction}"] == "true" for direction in ("forward", "backward"))
    }
    if tags.get("amgraph:country") != "BE" or tags.get("amgraph:rules") != RULES_VERSION:
        assert not opened, ("BE-BOUND-01", tags, opened)
    if tags.get("highway") in {"motorway", "motorway_link"} or tags.get("motorroad") == "yes":
        assert not opened, ("BE-ACC-01", tags, opened)
    if tags.get("highway") == "cycleway":
        assert "lichte_vierwieler" not in opened, ("BE-ACC-02", tags)
    tokens = signs({"traffic_sign": tags.get("traffic_sign", "")})
    if tokens & {"D7", "D9", "D10"}:
        assert "lichte_vierwieler" not in opened, ("BE-ACC-02", tags)
    if "D9" in tokens:
        assert "bromfiets_klasse_b" not in opened, ("BE-ACC-02", tags)
    if tokens & {
        "D10",
        "D11",
        "D13",
        "F5",
        "F9",
        "F99a",
        "F99b",
        "F99c",
        "F103",
        "F17",
        "F18",
        "C3",
        "C9",
    }:
        assert not opened, ("BE-ACC-04/06", tags, opened)
    for code in opened:
        assert tags.get(f"amgraph:{code}") != "no", ("BE-ACC-03", tags, code)
    for sign, code in (
        ("M7", "bromfiets_klasse_b"),
        ("M15", "speed_pedelec"),
        ("M16", "bromfiets_klasse_b"),
        ("M16", "speed_pedelec"),
    ):
        if sign in tokens:
            assert code not in opened, ("BE-ACC-05", tags, code)
    if opened:
        speed = numeric_speed(tags.get("maxspeed"))
        assert speed is not None and speed >= 10, ("BE-SPD-02", tags)
        if tags.get("highway") == "living_street" or "F12a" in tokens:
            assert speed <= 20, ("BE-SPD-02", tags)
        if tokens & {"D9", "F4a", "F111", "F111zone"}:
            assert speed <= 30, ("BE-SPD-02", tags)


ACCESS_PROBES = (
    ("speed_pedelec", "bromfiets_klasse_b"),
    ("bromfiets_klasse_a", "lichte_vierwieler"),
    ("bromfiets_klasse_b", "lichte_vierwieler"),
)
