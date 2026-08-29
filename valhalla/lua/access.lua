-- Access rules for the AM-licence vehicle classes, as pure functions of a way's OSM
-- tags. No Valhalla, no globals, no side effects, so every rule can be
-- unit-tested against a tag table.
--
-- A *class* here is a set of road rights, not a vehicle. Two vehicles whose
-- rights are identical share one class: in the Netherlands a bromfiets and a
-- speed pedelec do, because RVV art. 6 sends them to the same places.
--
-- This file holds what is the same wherever the rider is: how to read an access
-- tag, how a one-way binds, that a footway is never open to a motor. What
-- differs by country lives in countries/<cc>.lua — how many classes there are,
-- which OSM keys name them, the cycle-path sign vocabulary, what an unsigned
-- cycle path is assumed to be, which roads are barred outright.
--
-- The split matters because OpenStreetMap access tagging is already local:
-- mappers write `moped=designated` on a Dutch bromfietspad because Dutch law
-- puts a bromfiets there. Reading an explicit tag needs no country. Deciding
-- what an *absent* tag means does.
--
-- When a rule is not verified, or the data does not say, the answer is "no".

local M = {}

--- The stock Valhalla travel modes amgraph may borrow to carry an access class.
--
-- Borrowing is what lets one graph serve rules that contradict each other on
-- the cycle network: each class gets its own access bit, and the API asks for
-- the costing that reads it. `mask` is the bit in Valhalla's node access mask
-- (baldr/graphconstants.h), which nodes_proc clears when a class may not pass.
--
-- Five, and the count is the ceiling on how many classes a country may have.
-- Three would not reach Belgium: art. 9.1.2 of the Code van de openbare weg
-- splits into four sets of rights, because a speed pedelec and a klasse B
-- bromfiets differ on a cycle path where the limit is 50 or less. `taxi` and `bus` are the two Valhalla
-- costings that read an access bit of their own and are otherwise unused here
-- — both derive from AutoCost with kTaxiAccess and kBusAccess respectively,
-- verified against the 3.8.3 source. `auto` is deliberately left alone: it is
-- the mode everything else in the toolchain assumes when it wants to know
-- whether a road exists at all.
M.CARRIERS = {
  moped      = { forward = "moped_forward",      backward = "moped_backward",      mask = 512 },
  motorcycle = { forward = "motorcycle_forward", backward = "motorcycle_backward", mask = 1024 },
  truck      = { forward = "truck_forward",      backward = "truck_backward",      mask = 8 },
  taxi       = { forward = "taxi_forward",       backward = "taxi_backward",       mask = 32 },
  bus        = { forward = "bus_forward",        backward = "bus_backward",        mask = 64 },
}

--- Every carrier flag, in a fixed order, so an unsupported way can be closed
-- without knowing which country it would have belonged to.
M.CARRIER_ORDER = { "moped", "motorcycle", "truck", "taxi", "bus" }

-- Access values meaning yes. `use_sidepath` is deliberately absent: for the
-- class it names it is a prohibition, because the rider is obliged onto the
-- parallel path.
local ALLOW = {
  yes = true,
  designated = true,
  permissive = true,
}

local DENY = {
  no = true,
  use_sidepath = true,
  agricultural = true,
  forestry = true,
  dismount = true,
}

-- Values in the dimension and hazmat families that state *no* limit, so the
-- key's presence is not a restriction at all.
--
-- `hazmat=designated` and `hazmat=yes` mark a road as a route *for* dangerous
-- goods, which is a permission for lorries and says nothing about anybody
-- else; only `hazmat=no` and the conditional forms are prohibitions. Treating
-- the designation as a refusal closed whole arterial roads to every class:
-- Utrecht's Ruimteweg, the western exit from the city, is tagged that way, and
-- with it shut a brommobiel could not leave the city at all.
--
-- `maxheight=default` and `maxwidth=none` likewise say that the ordinary legal
-- maximum applies, which is not a signed restriction to be conservative about.
--
-- Measured 2026-08-15: 5,734 ways reopened, of which 5,340 are
-- `maxheight=default`, 206 `hazmat=designated` and 196 `maxheight=none`. The
-- hazmat case is the one that cost a city its exit, but it is far from the
-- largest. 14,600 ways carry a dimensional value that *is* a limit and stay
-- closed, and the country contains exactly one genuine hazmat prohibition.
local NOT_A_LIMIT = {
  designated = true,
  yes = true,
  default = true,
  none = true,
}

--- Does this restriction-family value actually state a limit?
local function limits(value)
  return value ~= nil and not NOT_A_LIMIT[value]
end

-- Ways no motorised class may ever use, whatever else is tagged.
local NEVER = {
  footway = true,
  pedestrian = true,
  steps = true,
  bridleway = true,
  corridor = true,
  elevator = true,
  platform = true,
  via_ferrata = true,
  busway = true,
  bus_guideway = true,
  construction = true,
  proposed = true,
  raceway = true,
}

-- Roadway values whose ordinary legal use is modelled. Everything outside
-- this table is unknown infrastructure, not a new road type to open by
-- accident when OSM adds a value.
local ROADWAY = {
  trunk = true,
  trunk_link = true,
  primary = true,
  primary_link = true,
  secondary = true,
  secondary_link = true,
  tertiary = true,
  tertiary_link = true,
  unclassified = true,
  residential = true,
  living_street = true,
}

-- These values can describe public access, but also private driveways, farm
-- tracks and roads whose type is not known. They need an explicit permission.
local UNCERTAIN_ROADWAY = {
  path = true,
  service = true,
  track = true,
  road = true,
}

-- Suffixes that put a key beyond what a class-wide, direction-resolved access
-- bit can represent. Presence alone closes the class and the value is never
-- read, because there is nothing here that could carry it: a lane-level or
-- directional permission has no home in one boolean per direction, and a
-- conditional one has no home in a graph with no clock.
local UNREPRESENTABLE = {
  ":conditional",
  ":forward", ":backward",
  ":lanes", ":lanes:forward", ":lanes:backward",
  ":forward:conditional", ":backward:conditional",
}

-- Stock Valhalla does not expose class-specific speed tags on the exact route
-- edge. If one exists, the API cannot display the limit that binds the
-- borrowed class, so that class must not receive the edge.
local CLASS_MAXSPEED = { "", ":forward", ":backward" }

-- A conditional speed schedule is not carried on the exact-edge response at
-- all, so a route over one could display 45 while a timed 30 is in force.
-- Until the request and response are time-aware, no class may use the way —
-- including when the schedule names some *other* class, because the API has no
-- way to know the schedule does not also reach this rider's vehicle.
local CONDITIONAL_MAXSPEED = {
  ":conditional", ":forward:conditional", ":backward:conditional",
}

--- Fill in everything about a country that follows from its class list.
--
-- Called once per country when this module is loaded, so the per-way path never
-- builds a table. The derived key families are generated rather than written
-- out per class: they are mechanical variants of the keys a class already
-- names, and the hand-written lists they replaced were four near-copies of each
-- other in which a missing entry would have been invisible.
--
-- Public so that spec/second_country_spec.lua can hand it a country that does
-- not exist. Country modules on disk go through `load_country` and never need
-- to call it.
function M.prepare(country)
  country.class_index = {}
  country.consulted = {}

  local function consult(key)
    country.consulted[key] = true
  end

  for _, key in ipairs({
    "highway", "junction", "motorroad", "access", "vehicle", "oneway",
    "maxspeed", "maxspeed:forward", "maxspeed:backward",
    "zone:maxspeed", "source:maxspeed", "maxspeed:type",
    "zone:maxspeed:forward", "source:maxspeed:forward", "maxspeed:type:forward",
    "zone:maxspeed:backward", "source:maxspeed:backward", "maxspeed:type:backward",
    "traffic_sign", "traffic_sign:forward", "traffic_sign:backward",
    "amgraph:country",
  }) do
    consult(key)
  end

  for index, class in ipairs(country.classes) do
    assert(M.CARRIERS[class.carrier],
      "class " .. class.code .. " names no carrier this Valhalla build has")
    for other = 1, index - 1 do
      assert(country.classes[other].carrier ~= class.carrier,
        "classes " .. country.classes[other].code .. " and " .. class.code ..
        " share carrier " .. class.carrier .. ", so neither can be told from the other")
    end
    country.class_index[class.code] = index

    -- Every key that binds this class: the ones that decide its access, the
    -- ones that may only close it, and the bicycle key where the country's law
    -- reads bicycle rules onto it.
    local bound = {}
    for _, key in ipairs(class.access_keys) do
      bound[#bound + 1] = key
    end
    for _, key in ipairs(class.closing_keys or {}) do
      bound[#bound + 1] = key
    end
    if class.bicycle_rules then
      bound[#bound + 1] = "bicycle"
    end
    class.bound_keys = bound

    -- Most specific last, which is the order M.directions resolves in, and the
    -- reverse of the access lookup order. A country that reads `motorcar`
    -- before `motor_vehicle` when deciding access must let `oneway:motorcar`
    -- beat `oneway:motor_vehicle` when deciding direction.
    local oneway = { "oneway:vehicle" }
    for position = #class.access_keys, 1, -1 do
      oneway[#oneway + 1] = "oneway:" .. class.access_keys[position]
    end
    class.oneway_keys = oneway

    local oneway_conditional = { "oneway:conditional" }
    for _, key in ipairs(oneway) do
      oneway_conditional[#oneway_conditional + 1] = key .. ":conditional"
    end
    for _, key in ipairs(class.closing_keys or {}) do
      oneway_conditional[#oneway_conditional + 1] = "oneway:" .. key .. ":conditional"
    end
    class.oneway_conditional_keys = oneway_conditional

    local closes_class = {}
    for _, key in ipairs(bound) do
      for _, suffix in ipairs(UNREPRESENTABLE) do
        closes_class[#closes_class + 1] = key .. suffix
      end
      for _, suffix in ipairs(CLASS_MAXSPEED) do
        closes_class[#closes_class + 1] = "maxspeed:" .. key .. suffix
      end
    end
    class.closes_class_keys = closes_class

    for _, key in ipairs(bound) do
      consult(key)
      for _, suffix in ipairs(CONDITIONAL_MAXSPEED) do
        consult("maxspeed:" .. key .. suffix)
      end
    end
    for _, key in ipairs(closes_class) do
      consult(key)
    end
    for _, key in ipairs(oneway) do
      consult(key)
    end
    for _, key in ipairs(oneway_conditional) do
      consult(key)
    end
    for _, key in ipairs(class.closing_keys or {}) do
      consult("oneway:" .. key)
    end
    if class.overlay then
      consult(class.overlay)
    end
  end

  for _, key in ipairs({
    "access:forward", "access:backward", "vehicle:forward", "vehicle:backward",
    "access:lanes", "access:lanes:forward", "access:lanes:backward",
    "vehicle:lanes", "vehicle:lanes:forward", "vehicle:lanes:backward",
    "access:conditional", "vehicle:conditional",
    "access:forward:conditional", "access:backward:conditional",
    "vehicle:forward:conditional", "vehicle:backward:conditional",
    "maxspeed:conditional", "maxspeed:forward:conditional",
    "maxspeed:backward:conditional",
    "maxwidth", "maxwidth:physical", "maxwidth:forward", "maxwidth:backward",
    "maxheight", "maxheight:forward", "maxheight:backward", "maxlength",
    "maxlength:forward", "maxlength:backward", "maxweight", "maxweight:forward",
    "maxweight:backward", "maxaxles", "maxaxleload",
    "maxwidth:conditional", "maxwidth:forward:conditional",
    "maxwidth:backward:conditional", "maxheight:conditional",
    "maxheight:forward:conditional", "maxheight:backward:conditional",
    "maxlength:conditional", "maxlength:forward:conditional",
    "maxlength:backward:conditional", "maxweight:conditional",
    "maxweight:forward:conditional", "maxweight:backward:conditional",
    "maxaxles:conditional", "maxaxleload:conditional",
    "hazmat", "hazmat:conditional", "hazmat:forward", "hazmat:backward",
    "hazmat:forward:conditional", "hazmat:backward:conditional",
  }) do
    consult(key)
  end

  return country
end

--- Country rule modules, by ISO 3166-1 alpha-2 code.
--
-- A country appears here only once its law has been read from primary sources
-- and cited. Everything else is forbidden.
local here = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"

local function load_country(name)
  return M.prepare(assert(loadfile(here .. "countries/" .. name .. ".lua"))())
end

M.COUNTRIES = {
  NL = load_country("nl"),
}

--- Which verified country's rules apply to this complete way.
--
-- infra/official_access.py writes this from the official land boundary.
-- Missing, foreign and border-crossing ways all return nil and therefore get
-- no amgraph carrier access at all.
function M.country_for(tags)
  return M.COUNTRIES[tags["amgraph:country"]]
end

--- Every OSM key the rules read for this country.
--
-- Exists so the exhaustive audit in test_access_rules.py can enumerate tag
-- combinations without a regular expression over this source. Deriving the key
-- families made that regex under-report, and an audit that silently stops being
-- exhaustive is worse than no audit.
function M.consulted_keys(country)
  local keys = {}
  for key in pairs(country.consulted) do
    keys[#keys + 1] = key
  end
  table.sort(keys)
  return keys
end

--- True when one of the way's traffic_sign tags carries the sign `wanted`.
--
-- Values look like "NL:G12a", sometimes as a semicolon list with subplates.
-- `prefix` is the country namespace; matching is on the whole token so that G11
-- does not also match G110.
function M.has_sign_in(tags, keys, wanted, prefix, accept_value)
  for _, key in ipairs(keys) do
    local value = tags[key]
    if value ~= nil then
      -- A semicolon separates independent signs; a comma attaches a subplate
      -- to its main sign. Both are token boundaries for exact code matching.
      for token in string.gmatch(value, "[^;,]+") do
        token = token:gsub("^%s*(.-)%s*$", "%1")
        local namespaced = prefix and prefix .. ":" .. wanted or nil
        if token == wanted
          or (namespaced and token == namespaced)
          or (accept_value and string.sub(token, 1, #wanted + 1) == wanted .. "[")
          or (accept_value and string.sub(token, 1, #wanted + 1) == wanted .. "-")
          or (accept_value and namespaced
            and string.sub(token, 1, #namespaced + 1) == namespaced .. "[")
          or (accept_value and namespaced
            and string.sub(token, 1, #namespaced + 1) == namespaced .. "-") then
          return true
        end
      end
    end
  end
  return false
end

function M.has_sign(tags, wanted, prefix, accept_value)
  return M.has_sign_in(tags,
    { "traffic_sign", "traffic_sign:forward", "traffic_sign:backward" },
    wanted, prefix, accept_value)
end

--- The first of `keys` that carries a meaningful access value.
-- Returns true, false, or nil when the way says nothing about this class.
function M.access_value(tags, keys)
  for _, key in ipairs(keys) do
    local value = tags[key]
    if value ~= nil then
      if ALLOW[value] then
        return true
      elseif DENY[value] then
        return false
      end
      -- A present value is a restriction unless this router has verified its
      -- public meaning. Treating `private`, `permit`, `customers` or a typo as
      -- absence silently turns conditional permission into public access.
      return false
    end
  end
  return nil
end

--- Which directions a class may travel, from the one-way tags.
--
-- `exceptions` holds the class-specific one-way keys, most specific last, so
-- `oneway:mofa` beats `oneway:vehicle` on the same way.
function M.directions(tags, exceptions)
  local forward, backward = true, true

  local oneway = tags["oneway"]
  if oneway == "yes" or oneway == "true" or oneway == "1" then
    backward = false
  elseif oneway == "-1" or oneway == "reverse" then
    forward = false
  elseif oneway ~= nil and oneway ~= "no" and oneway ~= "false"
    and oneway ~= "0" then
    -- Alternating, reversible and unknown direction control cannot be
    -- resolved in a static graph. Leaving both directions true can send a
    -- rider against the control in force.
    forward, backward = false, false
  end

  -- A roundabout is one-way whether or not it says so.
  local junction = tags["junction"]
  if junction == "roundabout" or junction == "circular" then
    backward = false
  end

  for _, key in ipairs(exceptions or {}) do
    local value = tags[key]
    if value == "no" then
      -- The Dutch "uitgezonderd" subplate: the one-way does not bind this class.
      forward, backward = true, true
    elseif value == "yes" or value == "true" or value == "1" then
      forward, backward = true, false
    elseif value == "-1" or value == "reverse" then
      forward, backward = false, true
    elseif value ~= nil and value ~= "false" and value ~= "0" then
      forward, backward = false, false
    end
  end

  return forward, backward
end

--- Is this way part of the cycle network rather than a roadway?
function M.is_cycle_infrastructure(tags, country)
  local highway = tags["highway"]
  if highway == "cycleway" then
    return true
  end
  if highway == "path" then
    -- A path is cycle infrastructure only when signed or designated for
    -- bicycles. Otherwise it is a track across a field.
    if tags["bicycle"] == "designated" then
      return true
    end
    for _, entry in ipairs(country.cycle_signs) do
      if M.has_sign(tags, entry.sign, country.sign_prefix) then
        return true
      end
    end
  end
  return false
end

--- What a sign admits for one class.
--
-- `true` and `false` are the ordinary answers. A function is for the rules that
-- turn on something else about the way: Belgian art. 9.1.2 admits a klasse B
-- bromfiets to a marked cycle path only where the road's own limit is above 50
-- km/h, so the sign alone does not settle it.
local function admits(entry, code, tags)
  local rule = entry.admits[code]
  if type(rule) == "function" then
    return rule(tags) and true or false
  end
  return rule and true or false
end

--- The classes a country's law reaches, all closed.
local function all_closed(country)
  local out = {}
  for index = 1, #country.classes do
    out[index] = false
  end
  return out
end

local function set_all(classes, value)
  for index = 1, #classes do
    classes[index] = value
  end
end

--- May each class use this way at all? Returns one boolean per class.
-- Direction is handled separately by M.directions.
local function classes_from_tags(tags, country)
  local highway = tags["highway"]
  local classes = all_closed(country)

  -- Roads this class is barred from outright, whatever else is tagged. The
  -- article behind this differs by country; see the country module.
  if country.forbidden_highways[highway] then
    return classes
  end
  if country.forbidden_when_motorroad and tags["motorroad"] == "yes" then
    return classes
  end

  if highway == nil or NEVER[highway] then
    return classes
  end

  local on_cycle_infrastructure = M.is_cycle_infrastructure(tags, country)

  -- A blanket prohibition, unless a class-specific tag lifts it.
  if M.access_value(tags, { "access" }) == false
    or M.access_value(tags, { "vehicle" }) == false then
    -- NL-ACC-05 binds here too. A class-specific tag may lift a blanket ban for
    -- the two-wheelers, but nothing lifts a brommobiel onto cycle
    -- infrastructure: art. 6 lid 3 puts it on the rijbaan and is mandatory, not
    -- permissive. Without this, `highway=cycleway` + `access=no` +
    -- `motor_vehicle=yes` returned the path as open to a four-wheeler.
    --
    -- Six ways in the Netherlands do that, which is why only the exhaustive
    -- pass in test_access_rules.py found it: no sampled route ever touched one.
    for index, class in ipairs(country.classes) do
      local lifted = M.access_value(tags, class.access_keys) == true
      classes[index] = lifted
        and (class.cycle_infrastructure or not on_cycle_infrastructure)
    end
    return classes
  end

  if on_cycle_infrastructure then
    -- What the local sign on this path admits. Signs are ordered most specific
    -- first in the country module, and the first one present wins.
    local signed = false
    for index, class in ipairs(country.classes) do
      classes[index] = country.unsigned_cycleway[class.code] and true or false
    end
    for _, entry in ipairs(country.cycle_signs) do
      -- Only an unscoped sign may grant both directions. A directional cycle
      -- sign cannot be represented as undirected class access here, so it
      -- remains closed rather than opening the opposite direction too.
      if M.has_sign_in(tags, { "traffic_sign" }, entry.sign, country.sign_prefix) then
        for index, class in ipairs(country.classes) do
          classes[index] = admits(entry, class.code, tags)
        end
        signed = true
        break
      end
    end

    -- Where the mapper wrote no sign, the road authority's own sign register
    -- can still say one stands here. infra/official_access.py matches it to
    -- the way; the country's unsigned default, which is a guess, applies only
    -- when neither source speaks.
    --
    -- This is the one place the authority may *open* anything, it reaches
    -- cycle infrastructure alone, and it reaches only a class that has said it
    -- may. The asymmetry is the whole reason it is safe. A snorfiets follows
    -- bicycle rules, so RVV art. 5 lid 1 admits it to a G11 and a G12a alike:
    -- the register need only establish that one of the two stands here, and
    -- confusing them costs nothing. For a bromfiets the same two signs are
    -- opposites — G11 bars it, G12a admits it — so a geometric match would be
    -- deciding a coin flip, and losing it puts the vehicle on a verplicht
    -- fietspad. It also gains nothing: art. 6 lid 2 puts a bromfiets on the
    -- rijbaan wherever no fiets/bromfietspad is established, which is exactly
    -- the case here, and the roadway is where the closure gating below leaves
    -- it. Measured against the ways where OSM does state a sign, the register
    -- disagrees on 0.47% of snorfiets openings and 3.00% of bromfiets ones.
    if not signed then
      for index, class in ipairs(country.classes) do
        if class.overlay_opens_cycle_infrastructure
          and tags[class.overlay] == "yes" then
          classes[index] = true
        end
      end
    end

    -- An explicit access tag is better evidence than an inferred sign.
    for index, class in ipairs(country.classes) do
      local stated = M.access_value(tags, class.access_keys)
      if stated ~= nil then
        classes[index] = stated
      end
      -- A class that follows bicycle rules (RVV art. 2b) is barred from a
      -- cycle path barred to bicycles.
      if class.bicycle_rules and M.access_value(tags, { "bicycle" }) == false then
        classes[index] = false
      end
      -- NL-ACC-05. A brommobiel is four-wheeled and belongs on the roadway.
      if not class.cycle_infrastructure then
        classes[index] = false
      end
    end

    return classes
  end

  -- A path, service way, track or unclassified `road` value may be public, but
  -- it may equally be a private driveway or farm track. Only public permission
  -- on the way or a permission naming the carrier can establish access.
  if UNCERTAIN_ROADWAY[highway] then
    local general = M.access_value(tags, { "access", "vehicle" }) == true
    for index, class in ipairs(country.classes) do
      classes[index] = general or M.access_value(tags, class.access_keys) == true
    end
    return classes
  end

  if not ROADWAY[highway] then
    return classes
  end

  -- An ordinary roadway. Open to every class unless something says otherwise.
  set_all(classes, true)

  -- NL-ACC-02, the mandatory-use rule. Where a parallel path is compulsory the
  -- roadway is not an option. Stock Valhalla ignores use_sidepath and routes
  -- riders along the roadway illegally; this is the fix.
  --
  -- The rule has a second half, and leaving it out is what made whole regions
  -- unroutable. Art. 5 lid 2 and art. 6 lid 2 are not silent about the case
  -- where no path exists: "Zij gebruiken de rijbaan indien een verplicht
  -- fietspad of een fiets/bromfietspad ontbreekt." The roadway is then
  -- *mandatory*, so refusing it as well is not the cautious reading — it
  -- asserts two contradictory facts about one place and leaves the rider
  -- nowhere lawful at all. The overlay value `on_roadway` is
  -- infra/official_access.py reporting that it looked and found no path this
  -- class may use beside this carriageway. It lifts a mandatory-use closure and
  -- nothing else: it cannot open a motorway, a signed prohibition, or a way an
  -- explicit access tag shuts, all of which are decided above and below this
  -- branch.
  --
  -- `use_sidepath` is a refusal in DENY like any other, so the lift works by
  -- hiding that one value from the class's access lookup rather than by
  -- overriding its result. Any *other* refusal on the same key still lands.
  for index, class in ipairs(country.classes) do
    local lifted = class.overlay ~= nil and tags[class.overlay] == "on_roadway"

    -- A class that follows bicycle rules is bound by a bicycle sidepath
    -- obligation too, and the same lift releases it.
    if class.bicycle_rules and tags["bicycle"] == "use_sidepath" and not lifted then
      classes[index] = false
    end

    local stated
    for _, key in ipairs(class.access_keys) do
      local value = tags[key]
      if value ~= nil then
        if not (value == "use_sidepath" and lifted) then
          stated = M.access_value(tags, { key })
        end
        break
      end
    end
    if stated ~= nil then
      classes[index] = stated
    end
  end

  return classes
end

--- May each class use this way at all, the road authority's verdict included.
function M.classes(tags, country)
  country = country or M.country_for(tags)
  if country == nil then
    return {}
  end
  local classes = classes_from_tags(tags, country)

  -- The road authority's own decision, written into the extract by
  -- infra/official_access.py. Applied last so it overrides every branch above,
  -- and only ever closes: there is deliberately no path here that sets a class
  -- to true.
  --
  -- This supplements the mandatory-use rule, art. 6 lid 1, which OSM states
  -- on only part of the network it binds. The authority dataset carries its
  -- own per-section access decision.
  --
  -- A class with no overlay is untouched on purpose. WKD models snorfiets and
  -- bromfiets; a brommobiel is neither. Art. 6 lid 3 puts it on the rijbaan, so
  -- a bromfiets closure caused by a compulsory sidepath does not reach it, and
  -- borrowing that verdict would shut roads it may lawfully use.
  --
  -- It does not reach a cycle path OSM has already answered for, and that
  -- exception is load-bearing. The overlay exists for mandatory use, which is
  -- a statement about carriageways: OSM under-states `use_sidepath`, so on a
  -- roadway its silence is expected and the authority adds real evidence. On a
  -- cycle path the position reverses. A mapper who wrote `traffic_sign=NL:G12a`
  -- with `moped=designated` has recorded the sign on the ground, which is the
  -- thing the law turns on, while the overlay reached this way by running a
  -- geometric match against a dataset whose own documentation warns that
  -- sign-to-road coupling is often wrong. Letting the match win closed
  -- fiets/bromfietspaden that the statute positively sends riders onto — the
  -- Utrecht to Amsterdam corridor lost most of its length that way, on ways
  -- signed G12a and tagged designated for both classes.
  local on_cycle_infrastructure = M.is_cycle_infrastructure(tags, country)
  local signed = false
  if on_cycle_infrastructure then
    for _, entry in ipairs(country.cycle_signs) do
      if M.has_sign_in(tags, { "traffic_sign" }, entry.sign, country.sign_prefix) then
        signed = true
        break
      end
    end
  end

  for index, class in ipairs(country.classes) do
    if class.overlay then
      local decided_by_osm = on_cycle_infrastructure
        and (signed or M.access_value(tags, class.access_keys) ~= nil)
      if tags[class.overlay] == "no" and not decided_by_osm then
        classes[index] = false
      end

      -- `roadway_only` is the one refusal that *must* beat an OSM cycle sign,
      -- and it is the only one whose whole content is that the sign does not
      -- mean what it usually means. RVV art. 5 lid 8 lets a municipality hang
      -- an onderbord on a verplicht fietspad and send snorfietsen to the
      -- rijbaan; Amsterdam and Utrecht have both done it across most of their
      -- central network. Deferring to the G11 here would put the class exactly
      -- where the verkeersbesluit takes it off. See docs/rules.md §5 NL-ACC-04.
      if tags[class.overlay] == "roadway_only" then
        classes[index] = false
      end
    end

    -- A closing key names a vehicle that shares this class's carrier because
    -- its statutory routing rules are the same. A tag naming it may close that
    -- shared bit, but may never open a way the class's own rules refused.
    for _, key in ipairs(class.closing_keys or {}) do
      if tags[key] ~= nil and M.access_value(tags, { key }) ~= true then
        classes[index] = false
      end
    end
  end

  -- This graph is not time- or credential-aware. Any conditional access tag
  -- therefore closes the affected class for the whole graph. That can refuse
  -- a legal trip outside the restricted hours; ignoring it can issue an
  -- illegal trip during them.
  if tags["access:conditional"] ~= nil or tags["vehicle:conditional"] ~= nil then
    set_all(classes, false)
  end

  -- Directional and lane-level access cannot be represented by the class-wide
  -- access decision below. A whole-way refusal is conservative; ignoring the
  -- tag can permit the forbidden direction or put the class in a barred lane.
  for _, key in ipairs({
    "access:forward", "access:backward", "vehicle:forward", "vehicle:backward",
    "access:lanes", "access:lanes:forward", "access:lanes:backward",
    "vehicle:lanes", "vehicle:lanes:forward", "vehicle:lanes:backward",
    "access:forward:conditional", "access:backward:conditional",
    "vehicle:forward:conditional", "vehicle:backward:conditional",
  }) do
    if tags[key] ~= nil then
      set_all(classes, false)
    end
  end

  for index, class in ipairs(country.classes) do
    for _, key in ipairs(class.closes_class_keys) do
      if tags[key] ~= nil then
        classes[index] = false
      end
    end
  end

  -- A1 carries the binding speed. OSM normally duplicates its value into
  -- maxspeed, which Valhalla exposes to the API. If that duplicate is absent,
  -- the API cannot tell the rider the signed limit. A3 is electronic and can
  -- change after the graph build, so no static value can verify it.
  local unscoped_a1 = M.has_sign_in(tags,
    { "traffic_sign" }, "A1", country.sign_prefix, true)
  local forward_a1 = M.has_sign_in(tags,
    { "traffic_sign:forward" }, "A1", country.sign_prefix, true)
  local backward_a1 = M.has_sign_in(tags,
    { "traffic_sign:backward" }, "A1", country.sign_prefix, true)
  if (unscoped_a1 and tags["maxspeed"] == nil)
    or (forward_a1 and tags["maxspeed"] == nil and tags["maxspeed:forward"] == nil)
    or (backward_a1 and tags["maxspeed"] == nil and tags["maxspeed:backward"] == nil)
    or M.has_sign(tags, "A3", country.sign_prefix, true) then
    set_all(classes, false)
  end

  local function speed_is_readable(value)
    if value == nil or value == "none" then
      return true
    end
    local trimmed = value:gsub("^%s*(.-)%s*$", "%1")
    local number_text = string.match(trimmed, "^(%d+%.?%d*)$")
      or string.match(trimmed, "^(%d+%.?%d*)%s+km/h$")
      or string.match(trimmed, "^(%d+%.?%d*)%s+kph$")
      or string.match(trimmed, "^(%d+%.?%d*)%s+mph$")
    local number = tonumber(number_text)
    -- Valhalla deliberately drops values below 10, which would otherwise make
    -- the API substitute the much higher class cap. Its parser also accepts
    -- only the numeric prefix of malformed/composite values; rejecting the
    -- remainder prevents `50;30` from being reported as a verified 50.
    return number ~= nil and number >= 10
  end
  if not speed_is_readable(tags["maxspeed"])
    or not speed_is_readable(tags["maxspeed:forward"])
    or not speed_is_readable(tags["maxspeed:backward"]) then
    set_all(classes, false)
  end

  -- A mapped zone/source says a statutory speed exists, but only maxspeed is
  -- carried back on Valhalla's exact route edge. Without the numeric companion
  -- the API would substitute a class cap that can be higher than a 30 zone.
  for _, key in ipairs({
    "zone:maxspeed", "source:maxspeed", "maxspeed:type",
    "zone:maxspeed:forward", "source:maxspeed:forward", "maxspeed:type:forward",
    "zone:maxspeed:backward", "source:maxspeed:backward", "maxspeed:type:backward",
  }) do
    if tags[key] ~= nil then
      local suffix = string.match(key, ":(%a+)$")
      local directional = suffix == "forward" or suffix == "backward"
      local numeric_key = directional and "maxspeed:" .. suffix or "maxspeed"
      if tags[numeric_key] == nil then
        set_all(classes, false)
      end
    end
  end

  -- A conditional speed schedule closes every class. See CONDITIONAL_MAXSPEED.
  for _, key in ipairs({
    "maxspeed:conditional", "maxspeed:forward:conditional",
    "maxspeed:backward:conditional",
  }) do
    if tags[key] ~= nil then
      set_all(classes, false)
    end
  end
  for _, class in ipairs(country.classes) do
    for _, key in ipairs(class.bound_keys) do
      for _, suffix in ipairs(CONDITIONAL_MAXSPEED) do
        if tags["maxspeed:" .. key .. suffix] ~= nil then
          set_all(classes, false)
        end
      end
    end
  end

  -- The request has no dimensions, load or trailer facts for two-wheelers.
  -- A static C17-C21-derived tag may therefore bind the actual vehicle even
  -- when its borrowed Valhalla costing has no dimension fields. Refuse the way
  -- for every class instead of assuming a representative vehicle fits.
  for _, key in ipairs({
    "maxwidth", "maxwidth:physical", "maxwidth:forward", "maxwidth:backward",
    "maxheight", "maxheight:forward", "maxheight:backward", "maxlength",
    "maxlength:forward", "maxlength:backward", "maxweight", "maxweight:forward",
    "maxweight:backward", "maxaxles", "maxaxleload",
  }) do
    if limits(tags[key]) then
      set_all(classes, false)
    end
  end

  -- C22 and OSM's hazmat family depend on the actual cargo. The request has no
  -- dangerous-goods declaration, so it cannot prove that a restriction does
  -- not bind this rider.
  for _, key in ipairs({
    "hazmat", "hazmat:conditional", "hazmat:forward", "hazmat:backward",
    "hazmat:forward:conditional", "hazmat:backward:conditional",
  }) do
    if limits(tags[key]) then
      set_all(classes, false)
    end
  end

  -- Valhalla 3.8.3 recognises only a tiny destination-only subset of
  -- conditional truck restrictions. A class riding the truck carrier inherits
  -- that gap, so a timed or state-dependent dimensional control must not be
  -- silently ignored.
  for index, class in ipairs(country.classes) do
    if class.carrier == "truck" then
      for _, key in ipairs({
        "maxwidth:conditional", "maxwidth:forward:conditional",
        "maxwidth:backward:conditional", "maxheight:conditional",
        "maxheight:forward:conditional", "maxheight:backward:conditional",
        "maxlength:conditional", "maxlength:forward:conditional",
        "maxlength:backward:conditional", "maxweight:conditional",
        "maxweight:forward:conditional", "maxweight:backward:conditional",
        "maxaxles:conditional", "maxaxleload:conditional",
      }) do
        if tags[key] ~= nil then
          classes[index] = false
        end
      end
    end
  end

  -- Static prohibition signs. Directional signs are applied in carrier_flags so
  -- they cannot accidentally close or open the opposite direction.
  for _, entry in ipairs(country.closed_signs or {}) do
    if M.has_sign_in(tags, { "traffic_sign" }, entry.sign,
      country.sign_prefix, entry.valued) then
      for index, class in ipairs(country.classes) do
        classes[index] = classes[index] and not entry.bars[class.code]
      end
    end
  end

  return classes
end

--- May each class pass an access-control node?
--
-- Valhalla parses node access separately from ways. Its stock parser reads
-- `motorcycle` for the motorcycle bit and `hgv` for the truck bit, but amgraph
-- borrows those bits for classes of its own. Reusing the stock result would
-- therefore ignore a `moped=no` or `motorcar=no` placed on a gate.
function M.node_classes(tags, country)
  if country == nil then
    return {}
  end

  local blanket = M.access_value(tags, { "access", "vehicle" })
  local classes = {}
  for index, class in ipairs(country.classes) do
    local keys = {}
    for _, key in ipairs(class.access_keys) do
      keys[#keys + 1] = key
    end
    if class.bicycle_rules then
      keys[#keys + 1] = "bicycle"
    end
    local specific = M.access_value(tags, keys)
    if specific ~= nil then
      classes[index] = specific
    elseif blanket ~= nil then
      classes[index] = blanket
    else
      classes[index] = true
    end
  end

  -- A barrier gets no extra refusal here, and demanding an explicit permission
  -- at one would be wrong twice over. No Dutch rule says an untagged bollard
  -- forbids passage: whether a rider may be there is decided by the road's own
  -- access, which is read above, and whether they can physically get past is
  -- decided by the upstream parser, whose mask amgraph.lua intersects with this
  -- result and which already models a bollard, a wall and a gate per travel
  -- mode.
  --
  -- It would also be, by a wide margin, the largest thing closing the network:
  -- 192,800 nodes nationwide against ~13,000 for every access tag combined. It
  -- bites our classes alone because nodes_proc clears only the borrowed bits,
  -- so plain `auto` keeps routing across a graph where a bromfiets cannot
  -- cross 500 metres of Utrecht.
  --
  -- AGENTS.md's own rule decides it: never state a legal rule without a
  -- primary source. There is none for this one, so the conservative-looking
  -- branch is itself an invention.

  if tags["access:conditional"] ~= nil or tags["vehicle:conditional"] ~= nil then
    set_all(classes, false)
  end

  for index, class in ipairs(country.classes) do
    for _, key in ipairs(class.bound_keys) do
      if tags[key .. ":conditional"] ~= nil then
        classes[index] = false
      end
    end
    for _, key in ipairs(class.closing_keys or {}) do
      if tags[key] ~= nil and M.access_value(tags, { key }) ~= true then
        classes[index] = false
      end
    end
  end

  for _, key in ipairs({
    "access:forward", "access:backward", "vehicle:forward", "vehicle:backward",
    "access:lanes", "access:lanes:forward", "access:lanes:backward",
    "vehicle:lanes", "vehicle:lanes:forward", "vehicle:lanes:backward",
    "access:forward:conditional", "access:backward:conditional",
    "vehicle:forward:conditional", "vehicle:backward:conditional",
  }) do
    if tags[key] ~= nil then
      set_all(classes, false)
    end
  end

  -- On a node a directional or lane-level tag for *any* class closes every
  -- class, not just the one named. A node is a point: there is no per-class
  -- geometry to attach the refusal to, so the whole junction goes.
  for _, class in ipairs(country.classes) do
    for _, key in ipairs(class.bound_keys) do
      for _, suffix in ipairs(UNREPRESENTABLE) do
        if suffix ~= ":conditional" and tags[key .. suffix] ~= nil then
          set_all(classes, false)
        end
      end
    end
  end

  -- Deliberately no maxspeed handling here, and the omission is the rule.
  -- On a *way*, an unreadable or unrepresentable speed closes the way, because
  -- the API promises a legal speed for every metre of returned geometry and it
  -- cannot keep that promise without a number. A node has no length: no
  -- segment is drawn for it and no speed is ever reported for it, so there is
  -- no promise to break. Treating a speed tag or an A1 sign on a node as a
  -- refusal closed every point where a limit changes, which in the Netherlands
  -- is the entrance to every built-up area.

  for _, key in ipairs({
    "hazmat", "hazmat:conditional", "hazmat:forward", "hazmat:backward",
    "hazmat:forward:conditional", "hazmat:backward:conditional",
  }) do
    if limits(tags[key]) then
      set_all(classes, false)
    end
  end

  -- A dimensional control at a node is normally a signed or physical narrow
  -- point. The request lacks the facts needed to prove any actual vehicle fits.
  for _, key in ipairs({
    "maxwidth", "maxwidth:physical", "maxwidth:forward", "maxwidth:backward",
    "maxheight", "maxheight:forward", "maxheight:backward", "maxlength",
    "maxlength:forward", "maxlength:backward", "maxweight", "maxweight:forward",
    "maxweight:backward", "maxaxles", "maxaxleload", "maxwidth:conditional",
    "maxwidth:forward:conditional", "maxwidth:backward:conditional",
    "maxheight:conditional", "maxheight:forward:conditional",
    "maxheight:backward:conditional", "maxlength:conditional",
    "maxlength:forward:conditional", "maxlength:backward:conditional",
    "maxweight:conditional", "maxweight:forward:conditional",
    "maxweight:backward:conditional", "maxaxles:conditional",
    "maxaxleload:conditional",
  }) do
    if limits(tags[key]) then
      set_all(classes, false)
    end
  end

  -- Only a sign that forbids *being on the road* may close a junction. A sign
  -- that prescribes a movement does not, and applying those here shut every
  -- roundabout in the country: see the D-series note in countries/nl.lua.
  -- Where a prescribed movement matters it is a turn restriction, which the
  -- graph already carries, not an impassable point.
  for _, entry in ipairs(country.closed_signs or {}) do
    if entry.bars_entry
      and M.has_sign(tags, entry.sign, country.sign_prefix, entry.valued) then
      for index, class in ipairs(country.classes) do
        classes[index] = classes[index] and not entry.bars[class.code]
      end
    end
  end

  -- C2 is a geslotenverklaring for the direction it faces. A node has no
  -- per-edge direction in Valhalla's access mask, so the direction cannot be
  -- recovered and no passage through it is verified.
  --
  -- C3 and C4 are deliberately absent. They mark a one-way road, which is a
  -- statement about direction and not a prohibition on being there, so on a
  -- node — where both directions would go — they would close a junction the
  -- law leaves open. The way's own `oneway` handling carries that rule.
  if country.all_directions_sign
    and M.has_sign(tags, country.all_directions_sign, country.sign_prefix) then
    set_all(classes, false)
  end

  return classes
end

local function close_from_directional_signs(tags, country, code, forward, backward)
  for _, entry in ipairs(country.closed_signs or {}) do
    if entry.bars[code] then
      if M.has_sign_in(tags, { "traffic_sign:forward" }, entry.sign,
        country.sign_prefix, entry.valued) then
        forward = false
      end
      if M.has_sign_in(tags, { "traffic_sign:backward" }, entry.sign,
        country.sign_prefix, entry.valued) then
        backward = false
      end
    end
  end

  -- The all-vehicle entry prohibition marks the direction in which entry is
  -- forbidden. If OSM stored it without a direction, closing only the way's
  -- arbitrary forward geometry would guess which approach carries the sign.
  local entry_sign = country.all_directions_sign
  if entry_sign then
    if M.has_sign_in(tags, { "traffic_sign:forward" }, entry_sign, country.sign_prefix) then
      forward = false
    end
    if M.has_sign_in(tags, { "traffic_sign:backward" }, entry_sign, country.sign_prefix) then
      backward = false
    end
    if M.has_sign_in(tags, { "traffic_sign" }, entry_sign, country.sign_prefix) then
      forward, backward = false, false
    end
  end

  -- The one-way signs designate a one-way road. A scoped sign tells us its
  -- permitted direction; an unscoped sign without an OSM oneway value has lost
  -- that direction, so neither direction is verified.
  for _, sign in ipairs(country.oneway_signs or {}) do
    if M.has_sign_in(tags, { "traffic_sign:forward" }, sign, country.sign_prefix) then
      backward = false
    end
    if M.has_sign_in(tags, { "traffic_sign:backward" }, sign, country.sign_prefix) then
      forward = false
    end
    if tags["oneway"] == nil
      and M.has_sign_in(tags, { "traffic_sign" }, sign, country.sign_prefix) then
      forward, backward = false, false
    end
  end

  return forward, backward
end

local function close_conditional_directions(tags, keys, forward, backward)
  for _, key in ipairs(keys) do
    if tags[key] ~= nil then
      return false, false
    end
  end
  return forward, backward
end

--- The carrier-mode flags for a way, as Valhalla's string booleans.
--
-- Every carrier is named on every way, including the ones this country does not
-- use. A carrier left unmentioned would keep whatever upstream decided, which
-- for `taxi` and `bus` is ordinary road access and would hand a class its
-- neighbour's rights the day a country starts using that carrier.
function M.carrier_flags(tags, country)
  country = country or M.country_for(tags)

  local flags = {}
  for _, carrier in ipairs(M.CARRIER_ORDER) do
    flags[M.CARRIERS[carrier].forward] = "false"
    flags[M.CARRIERS[carrier].backward] = "false"
  end

  -- Country attribution is the outer legal boundary. Return before any
  -- country-specific sign parsing so an unsupported or border-crossing way is
  -- both closed and safe to import without a country module.
  if country == nil then
    return flags
  end

  local classes = M.classes(tags, country)

  for index, class in ipairs(country.classes) do
    -- A class that follows bicycle rules does NOT inherit the cyclist's
    -- one-way exception, which is why `oneway_keys` is derived from the class's
    -- own access keys and never from `bicycle`. RVV art. 2b extends "de regels
    -- van dit besluit" — the rules of the decree — and an "uitgezonderd
    -- fietsers" onderbord is a sign placed under a verkeersbesluit, not a rule
    -- of the decree. Whether the exception reaches a snorfiets is genuinely
    -- contested in Dutch traffic-law commentary and no primary source settles
    -- it, so the conservative branch applies: see NL-ACC-07. Getting this wrong
    -- the other way sends a rider the wrong way down a one-way street; getting
    -- it this way costs them a longer ride.
    local forward, backward = M.directions(tags, class.oneway_keys)

    -- Time-dependent direction cannot be represented in the graph. Closing both
    -- directions for the affected class is the only answer that is valid at
    -- every time of day.
    forward, backward = close_conditional_directions(tags,
      class.oneway_conditional_keys, forward, backward)

    forward, backward = close_from_directional_signs(tags, country, class.code,
      forward, backward)

    -- The shared carrier cannot express a direction that applies to the
    -- sharing vehicle but not to the class it rides with. Refuse it rather
    -- than choosing one profile's answer for the other.
    for _, key in ipairs(class.closing_keys or {}) do
      if tags["oneway:" .. key] ~= nil then
        forward, backward = false, false
      end
    end

    local open = classes[index]
    local carrier = M.CARRIERS[class.carrier]
    flags[carrier.forward] = (open and forward) and "true" or "false"
    flags[carrier.backward] = (open and backward) and "true" or "false"
  end

  return flags
end

return M
