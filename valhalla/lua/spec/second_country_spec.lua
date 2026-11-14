-- Proves that a country the Netherlands does not resemble can be added to the
-- graph rules without editing access.lua, and that no country can step outside
-- the three supported vehicles.
--
-- This synthetic module is a fixture with invented sign codes and OSM keys;
-- nothing here may be cited as a rule. It must fail if somebody makes access.lua
-- own the Dutch answer again: `mofa`/`moped`/`motorcar`, a sign that admits a
-- class unconditionally or not at all.
--
-- What it exercises:
--
--   1. A country without the 25 km/h moped, as one whose law sets no rules for
--      it would be. Its `moped` carrier stays closed everywhere.
--   2. A cycle rule CONDITIONAL on the way, not settled by the sign alone.
--   3. Its own OSM key vocabulary, so the derived tag families follow the
--      country's keys rather than the Dutch ones.
--   4. The fixed vehicle set: an unknown class, a class on another carrier, a
--      duplicate, or a missing required vehicle is refused when it loads.

local access = assert(loadfile(arg[1] or "valhalla/lua/access.lua"))()

local failures = 0
local checks = 0

local function equals(description, actual, expected)
  checks = checks + 1
  if actual ~= expected then
    failures = failures + 1
    print(string.format("FAIL %s: expected %s, got %s",
      description, tostring(expected), tostring(actual)))
  end
end

--- The road's own limit, for the conditional rule below.
local function limit_above(threshold)
  return function(tags)
    local value = tonumber(tags["maxspeed"] or "")
    return value ~= nil and value > threshold
  end
end

local FIXTURE = access.prepare({
  code = "ZZ",
  sign_prefix = "ZZ",

  classes = {
    { code = "bromfiets", carrier = "motorcycle", access_keys = { "zz_moped" },
      cycle_infrastructure = true },
    { code = "brommobiel", carrier = "truck", access_keys = { "zz_car" },
      cycle_infrastructure = false },
  },

  forbidden_highways = { motorway = true },
  forbidden_when_motorroad = false,

  cycle_signs = {
    {
      sign = "P1",
      -- Invented: admission depends on the fixture way being faster than 50.
      -- This is not any country's law.
      admits = { bromfiets = limit_above(50) },
    },
  },

  unsigned_cycleway = { bromfiets = false },
  closed_signs = {
    { sign = "X1", bars = { bromfiets = true, brommobiel = true }, bars_entry = true },
  },
  all_directions_sign = "X2",
  oneway_signs = {},
})

local function flags_for(tags)
  return access.carrier_flags(tags, FIXTURE)
end

-- Two vehicles, and the one the country lacks stays closed -------------------

local road = flags_for({ highway = "residential" })
equals("an ordinary road opens the two declared vehicles", table.concat({
  road.motorcycle_forward, road.truck_forward,
}, " "), "true true")
equals("and keeps the 25 km/h moped's carrier closed", road.moped_forward, "false")

local car_closed = flags_for({ highway = "residential", zz_car = "no" })
equals("a class is closed by this country's own key", car_closed.truck_forward, "false")
equals("and closing it leaves the other alone", car_closed.motorcycle_forward, "true")

-- The conditional cycle rule ------------------------------------------------

local slow_path = flags_for({ highway = "cycleway", traffic_sign = "ZZ:P1", maxspeed = "50" })
equals("the conditional class is refused where the road is 50",
  slow_path.motorcycle_forward, "false")

local fast_path = flags_for({ highway = "cycleway", traffic_sign = "ZZ:P1", maxspeed = "70" })
equals("and admitted where the road is faster than 50",
  fast_path.motorcycle_forward, "true")
equals("a class barred from cycle infrastructure stays off it whatever the sign",
  fast_path.truck_forward, "false")

-- The derived key families follow this country's keys ------------------------

local lanes = flags_for({ highway = "residential", ["zz_moped:lanes"] = "yes|no" })
equals("a lane-level tag on this country's own key closes that class",
  lanes.motorcycle_forward, "false")
equals("and leaves the class that key does not name open", lanes.truck_forward, "true")

equals("this country's keys are what consulted_keys reports",
  (function()
    for _, key in ipairs(access.consulted_keys(FIXTURE)) do
      if key == "maxspeed:zz_moped:backward" then
        return true
      end
    end
    return false
  end)(), true)

-- Every carrier is named even when the country uses none of them -------------

local unattributed = access.carrier_flags({ highway = "residential" }, nil)
equals("a way with no country closes every carrier this build names",
  table.concat({
    unattributed.moped_forward, unattributed.motorcycle_forward,
    unattributed.truck_forward, unattributed.taxi_forward, unattributed.bus_forward,
  }, " "), "false false false false false")

equals("the carriers no vehicle uses are named and closed", table.concat({
  road.taxi_forward, road.bus_forward,
}, " "), "false false")

-- Only the three vehicles, each on its own carrier ---------------------------

local function loads(classes)
  return (pcall(access.prepare, { code = "YY", classes = classes }))
end

local BROMFIETS = { code = "bromfiets", carrier = "motorcycle", access_keys = { "moped" } }
local BROMMOBIEL = { code = "brommobiel", carrier = "truck", access_keys = { "motorcar" } }

equals("the two required vehicles alone load", loads({ BROMFIETS, BROMMOBIEL }), true)
equals("a class outside the supported three is refused", loads({
  BROMFIETS, BROMMOBIEL, { code = "trike", carrier = "taxi", access_keys = { "motorcycle" } },
}), false)
equals("a supported class on another carrier is refused", loads({
  BROMFIETS, { code = "brommobiel", carrier = "bus", access_keys = { "motorcar" } },
}), false)
equals("a class declared twice is refused", loads({ BROMFIETS, BROMFIETS, BROMMOBIEL }), false)
equals("a country without the microcar is refused", loads({ BROMFIETS }), false)
equals("a country without the 45 km/h moped is refused", loads({ BROMMOBIEL }), false)

print(string.format("%d second-country checks, %d failures", checks, failures))
os.exit(failures == 0 and 0 or 1)
