-- An invented country, ZZ, for the tests that need a second one.
--
-- Only the Netherlands is modelled, and the multi-country machinery (border
-- attribution, the merge, the manifest, per-country zones and carriers) still
-- has to be proved with two, or it rots unseen until somebody adds a country.
-- Nothing here is law and nothing may be cited as a rule. Its class codes,
-- sign codes and OSM keys are invented or chosen so that no Dutch answer can
-- stand in for one of its answers by accident.
--
-- It shares the four Dutch carriers, because a way on a border is open to a
-- carrier only where both countries have a class on it. It trusts only
-- enriched ways, as a country without the Dutch authority overlay must, by
-- requiring the `amgraph:rules` stamp its Python half writes.
--
-- Returns a function of the rules version, so the Python half can hand over
-- the same version it stamps.

return function(version)
  local function restricts(tags, _, node)
    if not node and tags["amgraph:rules"] ~= version then return true end
    return false
  end

  return {
    code = "ZZ",
    sign_prefix = "ZZ",
    rules_version = version,
    restricts = restricts,
    extra_keys = { "amgraph:rules" },

    classes = {
      { overlay = "amgraph:light", code = "light", carrier = "moped",
        access_keys = { "mofa" }, cycle_infrastructure = true },
      { overlay = "amgraph:heavy", code = "heavy", carrier = "motorcycle",
        access_keys = { "moped" }, cycle_infrastructure = true },
      { overlay = "amgraph:pedelec", code = "pedelec", carrier = "taxi",
        access_keys = { "speed_pedelec" }, cycle_infrastructure = true },
      { code = "quad", carrier = "truck",
        access_keys = { "motorcar", "motor_vehicle" }, cycle_infrastructure = false },
    },

    forbidden_highways = { motorway = true, motorway_link = true },
    forbidden_when_motorroad = true,

    cycle_signs = {
      { sign = "P1", admits = { light = true, heavy = true, pedelec = true } },
    },
    unsigned_cycleway = { light = true, heavy = false, pedelec = true },
    closed_signs = {
      { sign = "X1", bars = { light = true, heavy = true, pedelec = true, quad = true },
        bars_entry = true },
    },
    all_directions_sign = "X2",
    oneway_signs = {},
  }
end
