"""The invented second country, ZZ, for the tests of the multi-country machinery.

Only the Netherlands is modelled. Border attribution, the merge, the manifest,
the package and per-country zones and carriers must still be proved over two
countries, or they rot unseen until somebody adds one. `second_country`
registers ZZ for the one test that asks for it: in the rules registry, as an
importable country module, and in every Lua runtime `Access` opens. Its Lua half
is valhalla/lua/spec/fixture_country.lua, shared with the adapter spec.

Nothing here is law. The real registries never see ZZ, and there is no switch
outside a test that could put it there.
"""

from __future__ import annotations

import sys
import types
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "infra"))

from amgraph_rules import countries
from amgraph_rules.countries.nl import NETHERLANDS
from amgraph_rules.profiles import Carrier, Powertrain
from amgraph_rules.rules import BoundaryDocument, CountryRules, MunicipalZone, SearchBounds

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_LUA = ROOT / "valhalla/lua/spec/fixture_country.lua"

#: Dated today so require_current's review window always admits it.
RULES_VERSION = f"zz-{datetime.now(UTC).date().isoformat()}.1"

#: The Dutch carriers under invented codes, so a border way is open to a carrier
#: only where both countries have a class on it, and no Dutch code can stand in.
_CODES = {Carrier.MOPED: "light", Carrier.MOTORCYCLE: "heavy", Carrier.TAXI: "pedelec"}
_CODES[Carrier.TRUCK] = "quad"
CLASSES = tuple(
    replace(vehicle, code=_CODES[vehicle.carrier], names={"en": _CODES[vehicle.carrier]})
    for vehicle in NETHERLANDS.classes
)

MUNICIPAL_ZONES = {
    "Zedtown": MunicipalZone(
        municipality_id="ZZ0001",
        powertrain_classes=frozenset({"light", "heavy", "pedelec"}),
        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
        blocked_classes=frozenset(),
    ),
}

ZEDLAND = CountryRules(
    code="ZZ",
    name="Zedland",
    classes=CLASSES,
    default_class=None,
    municipal_zones=MUNICIPAL_ZONES,
    address_search_bounds=SearchBounds(south=0.0, north=1.0, west=1.0, east=2.0),
    boundary=BoundaryDocument(properties={"code": "ZZ"}),
    rules_version=RULES_VERSION,
    source="An invented test fixture; not law",
)


def sidepath_obligation(tags: dict[str, str], code: str) -> str:
    """Invented: the light class must take any path it may use, the others may."""
    return "mandatory" if code == "light" else "optional"


def enrich_way(source: dict[str, str], adjacent: dict[str, str]) -> dict[str, str]:
    """Stamp the way as enriched, and close a class a mandatory path beside it binds."""
    tags = {key: value for key, value in source.items() if not key.startswith("amgraph:")}
    tags["amgraph:rules"] = RULES_VERSION
    if tags.get("highway") not in {"cycleway", "path", "footway", "pedestrian"}:
        for code, obligation in adjacent.items():
            if obligation == "mandatory":
                tags[f"amgraph:{code}"] = "no"
    return tags


def _module() -> types.ModuleType:
    module = types.ModuleType("amgraph_rules.countries.zz")
    module.__dict__.update(
        ZEDLAND=ZEDLAND,
        CLASSES=CLASSES,
        MUNICIPAL_ZONES=MUNICIPAL_ZONES,
        RULES_VERSION=RULES_VERSION,
        EXTRACT_URL="https://example.invalid/zedland-latest.osm.pbf",
        BOUNDARY_URL="https://example.invalid/zedland-boundary.zip",
        BOUNDARY_LAYER="zedland",
        ZONE_LAYER="zedland_municipalities",
        ZONE_ID_KEY="code",
        BOUNDARY_FILENAME="zedland.geojson",
        ROUTE_CHECKS=tuple(((0.5, 1.1 + i / 20), (0.5, 1.2 + i / 20)) for i in range(10)),
        ACCESS_PROBES=(("light", "heavy"), ("pedelec", "quad")),
        # ZZ lies east of the test Netherlands, so these cross the shared border.
        BORDER_ROUTE_CHECKS={"NL": (((0.5, 1.1), (0.5, 0.9)), ((0.5, 0.9), (0.5, 1.1)))},
        sidepath_obligation=sidepath_obligation,
        enrich_way=enrich_way,
    )
    return module


@pytest.fixture
def second_country(monkeypatch):
    import prepare_country

    module = _module()
    monkeypatch.setitem(countries._MODELLED, "ZZ", ZEDLAND)
    monkeypatch.setitem(sys.modules, "amgraph_rules.countries.zz", module)

    original = prepare_country.load_rules

    def load_rules(runtime):
        lua = original(runtime)
        fixture = runtime.eval(f'function() return assert(loadfile("{FIXTURE_LUA}"))() end')()
        lua.COUNTRIES.ZZ = lua.prepare(fixture(RULES_VERSION))
        return lua

    monkeypatch.setattr(prepare_country, "load_rules", load_rules)
    return module
