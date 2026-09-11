-- Belgian access rules. Primary-source quotations and dates: docs/rules.md §11.
-- Ways require the matching enrichment version; raw OSM is never enough.

local all = {
  bromfiets_klasse_a = true,
  bromfiets_klasse_b = true,
  speed_pedelec = true,
  lichte_vierwieler = true,
}

local VERSION = "be-2026-09-09.3"

local function normalize_tags(tags)
  local out = {}
  for key, value in pairs(tags) do out[key] = value end
  for _, key in ipairs({ "traffic_sign", "traffic_sign:forward", "traffic_sign:backward" }) do
    if out[key] then
      out[key] = out[key]:gsub("BE:([A-Z])0+(%d)", "BE:%1%2")
        :gsub("_nl", ""):gsub("_fr", ""):gsub("_de", "")
    end
  end
  return out
end

-- BE-ACC-05/06. Recognised supplementary permissions cannot override a
-- prohibition. Unknown sign forms close rather than silently lose a condition.
local known_signs = {}
for sign in ("A1 A3 A5 A7 A9 A11 A13 A14 A15 A17 A19 A21 A23 A25 A27 A29 A31 A33 " ..
  "A35 A37 A39 A41 A43 A45 A47 A49 A51 B1 B3 B5 B7 B9 B11 B13 B15 B17 B19 B21 B22 B23 " ..
  "C1 C3 C5 C7 C9 C11 C13 C15 C17 C19 C21 C22 C23 C24a C24b C24c C25 C27 C29 " ..
  "C31 C31a C31b C33 C35 C37 C39 C41 C43 C45 C46 C47 C48 D1 D3 D4 D5 D7 D9 D10 D11 D13 " ..
  "E1 E3 E5 E7 E9a E9b E9c E9d E9e E9f E9g E9h E9i E11 " ..
  "F1 F1a F1b F3 F3a F3b F4a F4b F5 F7 F9 F11 F12a F12b F13 F14 F15 F17 F18 F19 " ..
  "F21 F23a F23b F23c F25 F27 F29 F31 F33a F33b F33c F34a F34b F35 F37 F39 F41 " ..
  "F43 F45 F45b F47 F49 F50 F50bis F51a F51b F53 F55 F57 F59 F61 F63 F65 F67 F69 F71 " ..
  "F73 F75 F77 F79 F81 F83 F85 F87 F89 F91 F93 F95 F97 F98 F99a F99b F99c " ..
  "F101a F101b F101c F103 F105 F107 F109 F111 F111zone F113 F117 F118 " ..
  "M1 M2 M3 M4 M5 M6 M7 M8 M9 M10 M11 M12 M13 M14 M15 M16"):gmatch("%S+") do
  known_signs[sign] = true
end

local numeric_restrictions = {}
for sign in ("C21 C23 C24a C24b C24c C25 C27 C29 D1 D3 D4 C31 F99a F99b F99c"):gmatch("%S+") do
  numeric_restrictions[sign] = true
end

local function restricts(tags, code, node)
  if not node and tags["amgraph:rules"] ~= VERSION then return true end
  if not node and tags["amgraph:unreadable_speed"] then return true end
  for _, key in ipairs({ "traffic_sign", "traffic_sign:forward", "traffic_sign:backward" }) do
    for token in (tags[key] or ""):gmatch("[^;,]+") do
      token = token:match("^%s*(.-)%s*$"):gsub("^BE:", "")
      local sign = token:match("^([A-Z]%d+[a-z]*)")
      if not sign or not known_signs[sign] then return true end
      local tail = token:sub(#sign + 1)
      -- A suffix is evidence too. Only numeric sign values have a verified
      -- interpretation; do not lose an unknown subplate inside brackets.
      if tail ~= "" then
        local value = tonumber(tail:match("^%[([%d%.]+)%]$") or tail:match("^%-([%d%.]+)$"))
        if not value then return true end
        if sign == "C43" or sign == "F4a" then
          if sign == "F4a" and value ~= 30 then return true end
          if not node then
            if tags.maxspeed == nil then return true end
            for _, speed in ipairs({ "maxspeed", "maxspeed:forward", "maxspeed:backward" }) do
              if tags[speed] ~= nil then
                local mapped = tonumber(tags[speed])
                if not mapped or mapped > value then return true end
              end
            end
          end
        elseif sign ~= "C45" and not numeric_restrictions[sign] then
          return true
        end
      end
      if sign == "M7" and code == "bromfiets_klasse_b" then return true end
      if sign == "M15" and code == "speed_pedelec" then return true end
      if sign == "M16" and (code == "bromfiets_klasse_b" or code == "speed_pedelec") then
        return true
      end
    end
  end
  return false
end

return {
  code = "BE",
  sign_prefix = "BE",
  rules_version = VERSION,
  normalize_tags = normalize_tags,
  restricts = restricts,
  speed_sign = "C43",
  dynamic_speed_sign = false,
  extra_keys = { "amgraph:rules", "amgraph:unreadable_speed" },

  -- BE-DEF-01. A and B here name two-wheelers only. The four-wheeled
  -- klasse B vehicle has its own carrier because art. 9.1.2 does not admit it.
  classes = {
    {
      overlay = "amgraph:bromfiets_klasse_a",
      code = "bromfiets_klasse_a", carrier = "moped",
      access_keys = { "mofa", "motor_vehicle" }, cycle_infrastructure = true,
    },
    {
      overlay = "amgraph:bromfiets_klasse_b",
      code = "bromfiets_klasse_b", carrier = "motorcycle",
      access_keys = { "moped", "motor_vehicle" }, cycle_infrastructure = true,
    },
    {
      overlay = "amgraph:speed_pedelec",
      code = "speed_pedelec", carrier = "taxi",
      access_keys = { "speed_pedelec", "motor_vehicle" }, cycle_infrastructure = true,
    },
    {
      code = "lichte_vierwieler", carrier = "truck",
      access_keys = { "motorcar", "motor_vehicle" }, cycle_infrastructure = false,
    },
  },

  -- BE-ACC-01. Arts. 21.1 and 22.1 exclude bromfietsen, including the
  -- four-wheeled klasse B vehicle defined in art. 2.17.
  forbidden_highways = { motorway = true, motorway_link = true },
  forbidden_when_motorroad = true,

  -- BE-ACC-02. Art. 9.1.2 changes the obligation at 50 km/h, not permission
  -- to use D7. A cycleway's maxspeed is not the adjacent carriageway's limit.
  cycle_signs = {
    { sign = "D10", admits = {} },
    { sign = "D9", admits = { bromfiets_klasse_a = true, speed_pedelec = true } },
    { sign = "D7", admits = {
      bromfiets_klasse_a = true, bromfiets_klasse_b = true, speed_pedelec = true,
    } },
  },
  unsigned_cycleway = {},

  closed_signs = {
    -- BE-ACC-02. A contradictory access tag must not open signed cycle
    -- infrastructure to a vehicle the statute does not admit.
    { sign = "D7", bars = { lichte_vierwieler = true }, bars_entry = true },
    { sign = "D9", bars = { bromfiets_klasse_b = true, lichte_vierwieler = true },
      bars_entry = true },
    { sign = "D10", bars = all, bars_entry = true },

    -- BE-ACC-06. These signs establish reserved infrastructure even when
    -- highway was tagged as an ordinary road. F99 pictograms are not encoded
    -- by the base sign, so no class is opened by guessing its symbols.
    { sign = "F5", bars = all, bars_entry = true },
    { sign = "F9", bars = all, bars_entry = true },
    { sign = "D11", bars = all, bars_entry = true },
    { sign = "D13", bars = all, bars_entry = true },
    { sign = "F99a", bars = all, bars_entry = true, valued = true },
    { sign = "F99b", bars = all, bars_entry = true, valued = true },
    { sign = "F99c", bars = all, bars_entry = true, valued = true },
    { sign = "F103", bars = all, bars_entry = true },
    { sign = "F17", bars = all },
    { sign = "F18", bars = all },
    -- BE-ACC-07. The route cannot recover the required movement from a sign
    -- code. Nodes remain passable: an arrow is not an entry prohibition.
    { sign = "D1", bars = all, valued = true },
    { sign = "D3", bars = all, valued = true },
    { sign = "D4", bars = all, valued = true },
    { sign = "C31a", bars = all },
    { sign = "C31b", bars = all },
    { sign = "C31", bars = all, valued = true },
    { sign = "C33", bars = all },
    -- BE-ACC-08. Dimensions, load and cargo are unknown at graph build time.
    { sign = "C21", bars = all, bars_entry = true, valued = true },
    { sign = "C23", bars = all, bars_entry = true, valued = true },
    { sign = "C24a", bars = all, bars_entry = true, valued = true },
    { sign = "C24b", bars = all, bars_entry = true, valued = true },
    { sign = "C24c", bars = all, bars_entry = true, valued = true },
    { sign = "C25", bars = all, bars_entry = true, valued = true },
    { sign = "C27", bars = all, bars_entry = true, valued = true },
    { sign = "C29", bars = all, bars_entry = true, valued = true },
    -- BE-ACC-04. These are Belgian codes, not their Dutch namesakes.
    { sign = "C3", bars = all, bars_entry = true },
    { sign = "C5", bars = { lichte_vierwieler = true }, bars_entry = true },
    { sign = "C9", bars = all, bars_entry = true },
  },
  all_directions_sign = "C1",
  oneway_signs = { "F19" },
}
