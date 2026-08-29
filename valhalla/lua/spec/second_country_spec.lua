-- Proves that a country the Netherlands does not resemble can be added to the
-- graph rules without editing access.lua.
--
-- Deliberately written while there is no second country to add, because that is
-- when it is cheap. Its purpose is not to describe anybody's law: the module
-- below is a fixture, its sign codes are invented, and nothing here may be
-- cited as a rule. Its purpose is to fail the day somebody makes access.lua own
-- the Dutch answer again — three classes, `mofa`/`moped`/`motorcar`, a sign
-- that admits a class unconditionally or not at all.
--
-- The three things it exercises are the three the research found a real country
-- needs:
--
--   1. A FOURTH access class. Belgian art. 9.1.2 splits into four sets of road
--      rights, because a speed pedelec and a klasse B bromfiets differ on a
--      cycle path where the limit is 50 km/h or less. Three stock carriers were
--      all there were; `taxi` and `bus` are the two remaining Valhalla costings
--      that read an access bit of their own.
--   2. A cycle rule CONDITIONAL on the way, not settled by the sign alone.
--   3. Its own OSM key vocabulary, so the derived tag families follow the
--      country's classes rather than the Dutch ones.

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
    { code = "light", carrier = "moped", access_keys = { "mofa" },
      bicycle_rules = true, cycle_infrastructure = true },
    { code = "heavy", carrier = "motorcycle", access_keys = { "moped" },
      cycle_infrastructure = true },
    -- The fourth and fifth: neither existed as an option before, and the
    -- pedelec is the case that made a fourth necessary.
    { code = "pedelec", carrier = "taxi", access_keys = { "speed_pedelec" },
      cycle_infrastructure = true },
    { code = "quad", carrier = "bus", access_keys = { "motorcar", "motor_vehicle" },
      cycle_infrastructure = false },
  },

  forbidden_highways = { motorway = true },
  forbidden_when_motorroad = false,

  cycle_signs = {
    {
      sign = "P1",
      admits = {
        light = true,
        -- Invented, and shaped after the real Belgian rule: admitted only
        -- where the road beside it is faster than 50.
        heavy = limit_above(50),
        pedelec = true,
      },
    },
  },

  unsigned_cycleway = { light = false, heavy = false, pedelec = false },
  closed_signs = {
    { sign = "X1", bars = { light = true, heavy = true, pedelec = true, quad = true },
      bars_entry = true },
  },
  all_directions_sign = "X2",
  oneway_signs = {},
})

local function flags_for(tags)
  return access.carrier_flags(tags, FIXTURE)
end

-- Four classes, four carriers, and the two new ones carry real answers -------

local road = flags_for({ highway = "residential" })
equals("an ordinary road opens all four carriers", table.concat({
  road.moped_forward, road.motorcycle_forward, road.taxi_forward, road.bus_forward,
}, " "), "true true true true")

local quad_closed = flags_for({ highway = "residential", motorcar = "no" })
equals("a class on the bus carrier is closed by its own key",
  quad_closed.bus_forward, "false")
equals("and closing it leaves the other three alone", table.concat({
  quad_closed.moped_forward, quad_closed.motorcycle_forward, quad_closed.taxi_forward,
}, " "), "true true true")

local pedelec_closed = flags_for({ highway = "residential", speed_pedelec = "no" })
equals("a class on the taxi carrier is closed by its own key",
  pedelec_closed.taxi_forward, "false")
equals("and it is a class of its own, not the heavy class's shadow",
  pedelec_closed.motorcycle_forward, "true")

-- The conditional cycle rule ------------------------------------------------
-- The single thing three static booleans per sign could not say.

local slow_path = flags_for({ highway = "cycleway", traffic_sign = "ZZ:P1", maxspeed = "50" })
equals("the conditional class is refused where the road is 50",
  slow_path.motorcycle_forward, "false")
equals("while the unconditional ones are admitted", table.concat({
  slow_path.moped_forward, slow_path.taxi_forward,
}, " "), "true true")

local fast_path = flags_for({ highway = "cycleway", traffic_sign = "ZZ:P1", maxspeed = "70" })
equals("and admitted where the road is faster than 50",
  fast_path.motorcycle_forward, "true")

equals("a class barred from cycle infrastructure stays off it whatever the sign",
  fast_path.bus_forward, "false")

-- The derived key families follow this country's keys ------------------------

equals("a lane-level tag on this country's own key closes that class",
  flags_for({ highway = "residential", ["speed_pedelec:lanes"] = "yes|no" }).taxi_forward,
  "false")

equals("and leaves the classes that key does not name open",
  flags_for({ highway = "residential", ["speed_pedelec:lanes"] = "yes|no" }).moped_forward,
  "true")

equals("this country's keys are what consulted_keys reports",
  (function()
    for _, key in ipairs(access.consulted_keys(FIXTURE)) do
      if key == "maxspeed:speed_pedelec:backward" then
        return true
      end
    end
    return false
  end)(), true)

-- Every carrier is named even when the country uses none of them -------------

local unattributed = access.carrier_flags({ highway = "residential" }, nil)
equals("a way with no country closes every carrier this build could borrow",
  table.concat({
    unattributed.moped_forward, unattributed.motorcycle_forward,
    unattributed.truck_forward, unattributed.taxi_forward, unattributed.bus_forward,
  }, " "), "false false false false false")

equals("a carrier this country does not use is still named and still closed",
  flags_for({ highway = "residential" }).truck_forward, "false")

-- Two classes may not share a carrier ----------------------------------------
-- They would be indistinguishable in the graph, so the router would answer for
-- whichever it happened to ask about.

local ok = pcall(access.prepare, {
  code = "YY",
  classes = {
    { code = "one", carrier = "moped", access_keys = { "mofa" } },
    { code = "two", carrier = "moped", access_keys = { "moped" } },
  },
})
equals("two classes on one carrier is refused when the country loads", ok, false)

local unknown_carrier = pcall(access.prepare, {
  code = "YY",
  classes = { { code = "one", carrier = "hovercraft", access_keys = { "mofa" } } },
})
equals("a carrier Valhalla does not have is refused too", unknown_carrier, false)

print(string.format("%d second-country checks, %d failures", checks, failures))
os.exit(failures == 0 and 0 or 1)
