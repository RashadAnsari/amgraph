-- Unit tests for the Dutch access rules. Plain Lua, no framework, no Valhalla:
-- run with `valhalla/lua/spec/run.sh`.
--
-- Each case names the rule it pins from docs/rules.md. A failure here
-- means the router would offer a rider a road their vehicle is barred from, so
-- these are the most important tests in the project.

local access = assert(loadfile(arg[1] or "valhalla/lua/access.lua"))()

--- Almost every case below is about Dutch law, so it is stated once here rather
-- than depending on which extract the environment happens to name.
local NL = access.COUNTRIES.NL

--- access.classes and access.node_classes answer one boolean per class, in the
-- country's own order. Almost every case here is written against the three
-- Dutch classes by name, so they are unpacked once rather than at each call.
local function triple(classes)
  return classes[1], classes[2], classes[3]
end

local failures = 0
local checks = 0

local function classes_to_string(a, b, c)
  local function s(v)
    return v and "yes" or "no"
  end
  return string.format("snorfiets=%s bromfiets=%s brommobiel=%s", s(a), s(b), s(c))
end

--- Asserts which classes may use a way. `expected` is {A, B, C}.
local function allows(rule, description, tags, expected)
  checks = checks + 1
  local a, b, c = triple(access.classes(tags, NL))
  if a ~= expected[1] or b ~= expected[2] or c ~= expected[3] then
    failures = failures + 1
    print(string.format("FAIL [%s] %s", rule, description))
    print("       expected " .. classes_to_string(expected[1], expected[2], expected[3]))
    print("       actual   " .. classes_to_string(a, b, c))
  end
end

local function equals(rule, description, actual, expected)
  checks = checks + 1
  if actual ~= expected then
    failures = failures + 1
    print(string.format("FAIL [%s] %s: expected %s, got %s",
      rule, description, tostring(expected), tostring(actual)))
  end
end

-- NL-ACC-01 --------------------------------------------------------------
-- RVV 1990 art. 42. This is the rule the product exists for; if any of these
-- pass a class, a rider gets sent onto a motorway.

allows("NL-ACC-01", "a motorway is barred to every class",
  { highway = "motorway" }, { false, false, false })

allows("NL-ACC-01", "a motorway slip road is barred to every class",
  { highway = "motorway_link" }, { false, false, false })

allows("NL-ACC-01", "an autoweg is barred even though it is tagged as a trunk road",
  { highway = "trunk", motorroad = "yes" }, { false, false, false })

allows("NL-ACC-01", "motorroad wins over an explicit moped permission",
  { highway = "trunk", motorroad = "yes", moped = "yes" }, { false, false, false })

allows("NL-ACC-01", "a trunk road that is not an autoweg stays open",
  { highway = "trunk" }, { true, true, true })

-- NL-ACC-02 and NL-ACC-03: cycle infrastructure --------------------------
-- The pair of rules stock Valhalla cannot express, because it has one access
-- bit for both classes.

allows("NL-ACC-02", "a fiets/bromfietspad admits both two-wheeled classes",
  { highway = "cycleway", traffic_sign = "NL:G12a" }, { true, true, false })

allows("NL-ACC-03", "a verplicht fietspad admits the snorfiets but not the bromfiets",
  { highway = "cycleway", traffic_sign = "NL:G11" }, { true, false, false })

allows("NL-ACC-05", "no cycle path admits the brommobiel",
  { highway = "cycleway", traffic_sign = "NL:G12a", moped = "yes" }, { true, true, false })

allows("G13", "an onverplicht fietspad is excluded because powertrain is unknown at build time",
  { highway = "cycleway", traffic_sign = "NL:G13" }, { false, false, false })

allows("conservative", "an unsigned, untagged cycleway is closed to everyone",
  { highway = "cycleway" }, { false, false, false })

allows("NL-ACC-02", "an explicit moped tag beats an inferred sign",
  { highway = "cycleway", traffic_sign = "NL:G11", moped = "yes" }, { true, true, false })

allows("NL-ACC-04", "the art. 5 lid 8 onderbord removes the snorfiets from the fietspad",
  { highway = "cycleway", traffic_sign = "NL:G11", mofa = "no" }, { false, false, false })

allows("NL-ACC-03", "a cycle path barred to bicycles is barred to the snorfiets too",
  { highway = "cycleway", traffic_sign = "NL:G12a", bicycle = "no" }, { false, true, false })

allows("NL-ACC-02", "a bare moped=yes cycleway admits the bromfiets",
  { highway = "cycleway", moped = "yes" }, { false, true, false })

allows("NL-ACC-03", "a bare mofa=yes cycleway admits the snorfiets only",
  { highway = "cycleway", mofa = "yes" }, { true, false, false })

allows("conservative", "a designated bicycle path with no sign is still closed",
  { highway = "path", bicycle = "designated" }, { false, false, false })

allows("conservative", "a generic path has no verified motor access",
  { highway = "path" }, { false, false, false })

allows("conservative", "a generic path needs permission naming each class",
  { highway = "path", mofa = "yes", moped = "designated", motor_vehicle = "permissive" },
  { true, true, true })

allows("conservative", "blanket public access can explicitly open a generic path",
  { highway = "path", access = "yes" }, { true, true, true })

allows("conservative", "an unknown highway type is not assumed to be a roadway",
  { highway = "future_road_kind", access = "yes" }, { false, false, false })

for _, highway in ipairs({ "service", "track", "road" }) do
  allows("conservative", "an unqualified " .. highway .. " has no verified public access",
    { highway = highway }, { false, false, false })
end

allows("conservative", "a service way needs permission naming each admitted class",
  { highway = "service", mofa = "yes", moped = "designated", motorcar = "permissive" },
  { true, true, true })

allows("conservative", "blanket public access can explicitly open an uncertain track",
  { highway = "track", access = "yes" }, { true, true, true })

-- NL-ACC-02: the mandatory-use rule --------------------------------------
-- The stock Valhalla bug docs/rules.md §2 names: use_sidepath is not in upstream's
-- moped value table, so it falls through to "allowed" and produces exactly the
-- illegal route this rule forbids.

allows("NL-ACC-02", "a roadway with a compulsory moped sidepath is closed to the bromfiets",
  { highway = "secondary", moped = "use_sidepath" }, { true, false, true })

allows("NL-ACC-03", "a roadway with a compulsory cycle sidepath is closed to the snorfiets",
  { highway = "secondary", bicycle = "use_sidepath" }, { false, true, true })

allows("NL-ACC-03", "mofa=use_sidepath closes the roadway to the snorfiets",
  { highway = "secondary", mofa = "use_sidepath" }, { false, true, true })

allows("NL-ACC-02", "both sidepath obligations together leave only the brommobiel",
  { highway = "secondary", moped = "use_sidepath", bicycle = "use_sidepath" },
  { false, false, true })

-- Ordinary roadways and blanket prohibitions -----------------------------

allows("NL-ACC-02", "a residential street is open to all three",
  { highway = "residential" }, { true, true, true })

allows("NL-ACC-02", "a living street is open to all three",
  { highway = "living_street" }, { true, true, true })

allows("conservative", "access=no closes a road to everyone",
  { highway = "residential", access = "no" }, { false, false, false })

for _, restricted in ipairs({ "private", "destination", "delivery", "permit", "residents",
  "customers", "unknown" }) do
  allows("conservative", "access=" .. restricted .. " is not public permission",
    { highway = "residential", access = restricted }, { false, false, false })
end

allows("conservative", "an unknown class-specific value closes that class",
  { highway = "residential", moped = "u" }, { true, false, true })

allows("conservative", "a blanket conditional restriction closes every class",
  { highway = "residential", ["access:conditional"] = "no @ (sunset-sunrise)" },
  { false, false, false })

allows("conservative", "a moped conditional restriction closes only bromfiets access",
  { highway = "residential", ["moped:conditional"] = "no @ (Sa 06:00-19:00)" },
  { true, false, true })

allows("conservative", "a bicycle conditional restriction reaches the snorfiets",
  { highway = "residential", ["bicycle:conditional"] = "no @ (sunset-sunrise)" },
  { false, true, true })

allows("conservative", "a motor-vehicle conditional restriction reaches the brommobiel",
  { highway = "residential", ["motor_vehicle:conditional"] = "private @ (Mo-Fr)" },
  { true, true, false })

allows("conservative", "a directional moped restriction closes the complete static edge",
  { highway = "residential", ["moped:forward"] = "no" }, { true, false, true })

allows("conservative", "lane-specific access closes every class the graph cannot place",
  { highway = "residential", ["access:lanes"] = "yes|no" },
  { false, false, false })

allows("conservative", "a directional conditional motorcar rule closes the brommobiel",
  { highway = "residential", ["motorcar:backward:conditional"] = "no @ wet" },
  { true, true, false })

allows("conservative", "a conditional speed closes a road whose legal speed is unknowable",
  { highway = "residential", ["maxspeed:conditional"] = "30 @ (Mo-Fr 07:00-19:00)" },
  { false, false, false })

allows("conservative", "a directional conditional speed also closes the whole static edge",
  { highway = "residential", ["maxspeed:forward:conditional"] = "15 @ wet" },
  { false, false, false })

allows("conservative", "a moped-specific speed closes only the bromfiets class",
  { highway = "residential", ["maxspeed:moped"] = "30" }, { true, false, true })

allows("conservative", "a speed-pedelec-only refusal closes its shared carrier class",
  { highway = "residential", speed_pedelec = "no" }, { true, false, true })

allows("conservative", "a speed-pedelec-specific speed closes its shared carrier class",
  { highway = "residential", ["maxspeed:speed_pedelec"] = "30" },
  { true, false, true })

allows("conservative", "a bicycle-specific speed reaches the snorfiets",
  { highway = "residential", ["maxspeed:bicycle"] = "15" }, { false, true, true })

allows("conservative", "a motorcar-specific speed reaches the brommobiel",
  { highway = "residential", ["maxspeed:motorcar"] = "30" }, { true, true, false })

allows("conservative", "a conditional width restriction closes the brommobiel",
  { highway = "residential", ["maxwidth:conditional"] = "1.5 @ (Mo-Fr)" },
  { true, true, false })

allows("conservative", "a directional conditional weight restriction closes the brommobiel",
  { highway = "residential", ["maxweight:forward:conditional"] = "0.5 @ wet" },
  { true, true, false })

allows("conservative", "an unmodelled static width limit closes every class",
  { highway = "residential", maxwidth = "1.0" }, { false, false, false })

allows("speed", "an A1 sign is usable when the matching maxspeed is on the way",
  { highway = "residential", traffic_sign = "NL:A1-30", maxspeed = "30" },
  { true, true, true })

allows("conservative", "an A1 sign without its speed value closes the way",
  { highway = "residential", traffic_sign = "NL:A1-30" }, { false, false, false })

allows("conservative", "a dynamic A3 speed sign closes the static graph",
  { highway = "residential", traffic_sign = "NL:A3-30", maxspeed = "30" },
  { false, false, false })

allows("conservative", "an unreadable static speed does not become the class cap",
  { highway = "residential", maxspeed = "signals" }, { false, false, false })

allows("conservative", "a composite speed Valhalla only partially parses closes the way",
  { highway = "residential", maxspeed = "50;30" }, { false, false, false })

allows("conservative", "a zone speed without the numeric maxspeed closes the way",
  { highway = "residential", ["zone:maxspeed"] = "NL:30" },
  { false, false, false })

allows("speed", "a zone source is usable when its numeric maxspeed is present",
  { highway = "residential", ["zone:maxspeed"] = "NL:30", maxspeed = "30" },
  { true, true, true })

allows("conservative", "a low speed Valhalla discards closes the way",
  { highway = "residential", maxspeed = "5" }, { false, false, false })

allows("speed", "a numeric speed Valhalla can return leaves access unchanged",
  { highway = "residential", maxspeed = "30" }, { true, true, true })

allows("conservative", "access=no with a moped exception opens it for the bromfiets only",
  { highway = "residential", access = "no", moped = "yes" }, { false, true, false })

allows("conservative", "vehicle=no closes a road to everyone",
  { highway = "residential", vehicle = "no" }, { false, false, false })

allows("conservative", "motor_vehicle=no keeps the brommobiel out but not the two-wheelers",
  { highway = "residential", motor_vehicle = "no" }, { true, true, false })

allows("conservative", "a footway is closed to every motorised class",
  { highway = "footway" }, { false, false, false })

allows("conservative", "a busway is closed to every class",
  { highway = "busway" }, { false, false, false })

allows("conservative", "a way with no highway tag is closed",
  { name = "somewhere" }, { false, false, false })

-- Sign matching ----------------------------------------------------------

equals("NL-ACC-02", "G11 does not match G110",
  access.has_sign({ traffic_sign = "NL:G110" }, "G11", "NL"), false)

equals("NL-ACC-02", "a sign in a semicolon list is found",
  access.has_sign({ traffic_sign = "NL:G12a;NL:OB503" }, "G12a", "NL"), true)

equals("NL-SIGN", "a main sign followed by a comma-separated subplate is found",
  access.has_sign({ traffic_sign = "NL:C12,OB108" }, "C12", "NL"), true)

equals("NL-SIGN", "a sign with a bracketed statutory value is found",
  access.has_sign({ traffic_sign = "NL:C18[2.3]" }, "C18", "NL", true), true)

equals("NL-SIGN", "a Dutch speed sign with a dashed value is found",
  access.has_sign({ traffic_sign = "NL:A1-30" }, "A1", "NL", true), true)

equals("NL-ACC-02", "a directional sign tag is found",
  access.has_sign({ ["traffic_sign:forward"] = "NL:G11" }, "G11", "NL"), true)

equals("NL-ACC-02", "G12a is not confused with G11",
  access.has_sign({ traffic_sign = "NL:G12a" }, "G11", "NL"), false)

-- Direction --------------------------------------------------------------

local function dirs(tags, exceptions)
  local f, b = access.directions(tags, exceptions)
  return (f and "F" or "-") .. (b and "B" or "-")
end

equals("oneway", "a two-way street is open both ways",
  dirs({ highway = "residential" }, {}), "FB")

equals("oneway", "a one-way street is forward only",
  dirs({ highway = "residential", oneway = "yes" }, {}), "F-")

equals("oneway", "oneway=-1 is backward only",
  dirs({ highway = "residential", oneway = "-1" }, {}), "-B")

equals("conservative", "an alternating one-way has no always-legal direction",
  dirs({ highway = "residential", oneway = "alternating" }, {}), "--")

equals("conservative", "an unknown one-way value does not become two-way",
  dirs({ highway = "residential", oneway = "unknown" }, {}), "--")

equals("oneway", "a roundabout is one-way without saying so",
  dirs({ highway = "residential", junction = "roundabout" }, {}), "F-")

equals("oneway", "the uitgezonderd subplate reopens a one-way for its class",
  dirs({ highway = "residential", oneway = "yes", ["oneway:moped"] = "no" },
    { "oneway:moped" }), "FB")

equals("oneway", "a one-way exception for cyclists does not reopen it for mopeds",
  dirs({ highway = "residential", oneway = "yes", ["oneway:bicycle"] = "no" },
    { "oneway:moped" }), "F-")

equals("oneway", "the most specific exception wins",
  dirs({ highway = "cycleway", oneway = "yes", ["oneway:vehicle"] = "no", ["oneway:mofa"] = "yes" },
    { "oneway:vehicle", "oneway:mofa" }), "F-")

local conditional_flags = access.carrier_flags(
  { highway = "residential", ["oneway:moped:conditional"] = "no @ (Mo-Fr)" }, NL)
equals("conservative", "a conditional moped direction closes both bromfiets directions",
  conditional_flags.motorcycle_forward .. conditional_flags.motorcycle_backward, "falsefalse")
equals("conservative", "a conditional moped direction does not close another class",
  conditional_flags.moped_forward .. conditional_flags.moped_backward ..
    conditional_flags.truck_forward .. conditional_flags.truck_backward,
  "truetruetruetrue")

local speed_pedelec_flags = access.carrier_flags(
  { highway = "residential", ["oneway:speed_pedelec"] = "no" }, NL)
equals("conservative", "an unshareable speed-pedelec direction closes its carrier",
  speed_pedelec_flags.motorcycle_forward .. speed_pedelec_flags.motorcycle_backward,
  "falsefalse")

-- NL-ACC-06. RVV 1990 bijlage I, C-series, read 2026-08-14. These
-- prohibitions are applied from the sign itself even when OSM omitted its
-- implied access tag.
allows("NL-ACC-06", "C1 closes the way to every supported class",
  { highway = "residential", traffic_sign = "NL:C1" }, { false, false, false })

allows("NL-ACC-06", "C6 closes a brommobiel through RVV art. 2a",
  { highway = "residential", traffic_sign = "NL:C6" }, { true, true, false })

allows("NL-ACC-06", "C9 explicitly closes every supported class",
  { highway = "residential", traffic_sign = "NL:C9" }, { false, false, false })

allows("NL-ACC-06", "C12 closes a brommobiel through RVV art. 2a",
  { highway = "residential", traffic_sign = "NL:C12" }, { true, true, false })

allows("NL-ACC-06", "C13 closes snorfiets and bromfiets but not brommobiel",
  { highway = "residential", traffic_sign = "NL:C13" }, { false, false, true })

allows("NL-ACC-06", "C14 reaches the snorfiets through RVV art. 2b",
  { highway = "residential", traffic_sign = "NL:C14" }, { false, true, true })

allows("NL-ACC-06", "C15 closes snorfiets and bromfiets but not brommobiel",
  { highway = "residential", traffic_sign = "NL:C15" }, { false, false, true })

allows("NL-ACC-06", "C10 closes the unmodelled trailer case for a brommobiel",
  { highway = "residential", traffic_sign = "NL:C10" }, { true, true, false })

for _, sign in ipairs({ "G1", "G3", "G7", "G9" }) do
  allows("NL-ACC-08", sign .. " cannot be bypassed by a contradictory highway tag",
    { highway = "residential", traffic_sign = "NL:" .. sign },
    { false, false, false })
end

for _, sign in ipairs({ "D1", "D2", "D4", "D5", "D6", "D7" }) do
  allows("NL-ACC-09", sign .. " closes a way whose mandatory movement is not modelled",
    { highway = "residential", traffic_sign = "NL:" .. sign },
    { false, false, false })
end

allows("NL-ACC-09", "F7 closes a junction whose prohibited U-turn is not modelled",
  { highway = "residential", traffic_sign = "NL:F7" },
  { false, false, false })

for _, sign in ipairs({ "C17", "C18", "C19", "C20", "C21" }) do
  allows("NL-ACC-06", sign .. " closes classes whose exact dimensions are not in the request",
    { highway = "residential", traffic_sign = "NL:" .. sign .. "[2.0]" },
    { false, false, false })
end

allows("NL-ACC-06", "C22 closes vehicles whose regulated cargo is unknown",
  { highway = "residential", traffic_sign = "NL:C22" },
  { false, false, false })

allows("conservative", "a hazardous-cargo restriction closes an unmodelled load",
  { highway = "residential", hazmat = "no" }, { false, false, false })

local flags = access.carrier_flags(
  { highway = "residential", ["traffic_sign:forward"] = "NL:C2" }, NL)
equals("NL-ACC-06", "a forward C2 closes every carrier only forwards",
  flags.moped_forward .. flags.motorcycle_forward .. flags.truck_forward,
  "falsefalsefalse")
equals("NL-ACC-06", "a forward C2 leaves the reverse direction untouched",
  flags.moped_backward .. flags.motorcycle_backward .. flags.truck_backward,
  "truetruetrue")

flags = access.carrier_flags(
  { highway = "residential", traffic_sign = "NL:C2" }, NL)
equals("NL-ACC-06", "an unscoped C2 cannot guess its forbidden direction",
  flags.moped_forward .. flags.moped_backward ..
    flags.motorcycle_forward .. flags.motorcycle_backward ..
    flags.truck_forward .. flags.truck_backward,
  "falsefalsefalsefalsefalsefalse")

flags = access.carrier_flags(
  { highway = "residential", ["traffic_sign:backward"] = "NL:C12,OB108" }, NL)
equals("NL-ACC-06", "a backward C12 closes only the brommobiel backwards",
  flags.moped_backward .. flags.motorcycle_backward .. flags.truck_backward,
  "truetruefalse")
equals("NL-ACC-06", "a backward C12 leaves every carrier forwards",
  flags.moped_forward .. flags.motorcycle_forward .. flags.truck_forward,
  "truetruetrue")

flags = access.carrier_flags(
  { highway = "residential", ["traffic_sign:forward"] = "NL:F7" }, NL)
equals("NL-ACC-09", "a scoped F7 refuses only the approach with the unmodelled turn",
  flags.moped_forward .. flags.motorcycle_forward .. flags.truck_forward,
  "falsefalsefalse")
equals("NL-ACC-09", "a scoped F7 leaves the opposite approach untouched",
  flags.moped_backward .. flags.motorcycle_backward .. flags.truck_backward,
  "truetruetrue")

-- NL-ACC-07. RVV art. 2b extends the *rules of the decree*; an "uitgezonderd
-- fietsers" onderbord is a sign placed under a verkeersbesluit, not a rule.
-- Nothing in the RVV says the word carries the extension, commentary is
-- divided, and no primary source settles it — so a snorfiets does not inherit
-- it. Being wrong this way costs a longer ride; the other way sends a rider
-- the wrong way down a one-way street.
local function snorfiets_dirs(tags)
  local f, b = access.directions(tags, { "oneway:vehicle", "oneway:mofa" })
  return (f and "F" or "-") .. (b and "B" or "-")
end

equals("oneway", "a cyclist one-way exception does not reopen it for a snorfiets",
  snorfiets_dirs({ highway = "residential", oneway = "yes", ["oneway:bicycle"] = "no" }), "F-")

equals("oneway", "but an exception naming the class itself does",
  snorfiets_dirs({ highway = "residential", oneway = "yes", ["oneway:mofa"] = "no" }), "FB")

-- Carrier flags ----------------------------------------------------------
-- The classes ride on stock Valhalla travel modes; this is the mapping that
-- makes one graph serve three sets of rules.

flags = access.carrier_flags({ highway = "cycleway", traffic_sign = "NL:G11" }, NL)
equals("ADR-0001", "a verplicht fietspad opens the moped carrier", flags.moped_forward, "true")
equals("ADR-0001", "a verplicht fietspad closes the motorcycle carrier",
  flags.motorcycle_forward, "false")
equals("ADR-0001", "a verplicht fietspad closes the truck carrier", flags.truck_forward, "false")

flags = access.carrier_flags({ highway = "residential", oneway = "yes" }, NL)
equals("ADR-0001", "a one-way street closes every carrier backwards",
  flags.moped_backward .. flags.motorcycle_backward .. flags.truck_backward,
  "falsefalsefalse")
equals("ADR-0001", "a one-way street opens every carrier forwards",
  flags.moped_forward .. flags.motorcycle_forward .. flags.truck_forward,
  "truetruetrue")

-- Node access ------------------------------------------------------------
-- Valhalla parses barrier/access nodes separately from ways. Its stock
-- motorcycle and hgv meanings must never leak into the carrier bits borrowed
-- by bromfiets and brommobiel.

local function node_allows(tags)
  local a, b, c = triple(access.node_classes(tags, NL))
  return classes_to_string(a, b, c)
end

equals("conservative", "an ordinary routing node leaves every class open",
  node_allows({ highway = "crossing" }), classes_to_string(true, true, true))

-- An untagged barrier states nothing about authorisation, so these rules state
-- nothing either. Whether the rider may be here is the road's access, read
-- above; whether they can physically get past is upstream's parser, whose mask
-- amgraph.lua intersects with this answer and which already models a bollard, a
-- wall and a gate per travel mode. Demanding an explicit permission here made
-- 192,800 nodes impassable to all three classes, against ~13,000 for every
-- access tag in the country combined, and it was the single largest reason a
-- bromfiets could not cross 500 metres of Utrecht while plain `auto` could.
equals("conservative", "an untagged barrier is not itself a prohibition",
  node_allows({ barrier = "gate" }), classes_to_string(true, true, true))

equals("conservative", "but an explicit refusal on one still closes it",
  node_allows({ barrier = "gate", access = "no" }), classes_to_string(false, false, false))

equals("conservative", "and a class-specific refusal reaches only that class",
  node_allows({ barrier = "bollard", moped = "no" }), classes_to_string(true, false, true))

equals("conservative", "an explicit public gate preserves all verified classes",
  node_allows({ barrier = "gate", access = "yes" }),
  classes_to_string(true, true, true))

equals("conservative", "public permissions can name the classes admitted by a gate",
  node_allows({ barrier = "gate", mofa = "yes", moped = "designated",
    motor_vehicle = "permissive" }), classes_to_string(true, true, true))

equals("conservative", "moped=no on a node closes the bromfiets carrier",
  node_allows({ barrier = "gate", moped = "no", mofa = "yes", motor_vehicle = "yes" }),
  classes_to_string(true, false, true))

equals("conservative", "speed_pedelec=no on a node closes its shared carrier",
  node_allows({ speed_pedelec = "no" }), classes_to_string(true, false, true))

equals("NL-ACC-05", "motorcar=no on a node closes the brommobiel carrier",
  node_allows({ barrier = "gate", mofa = "yes", moped = "yes", motorcar = "no" }),
  classes_to_string(true, true, false))

equals("conservative", "an unknown node permission closes only its class",
  node_allows({ moped = "customers" }), classes_to_string(true, false, true))

equals("conservative", "conditional node access is never treated as always legal",
  node_allows({ ["access:conditional"] = "yes @ (Mo-Fr)" }),
  classes_to_string(false, false, false))

equals("conservative", "directional node access has no safe adjacent edge",
  node_allows({ ["moped:forward"] = "no" }), classes_to_string(false, false, false))

equals("NL-ACC-06", "a C13 sign mapped as a node closes both two-wheelers",
  node_allows({ traffic_sign = "NL:C13" }), classes_to_string(false, false, true))

-- A one-way sign is a statement about direction, not a prohibition on being
-- there, so on a node — where both directions meet — it closes a junction the
-- law leaves open. The way's own `oneway` handling carries the rule.
equals("NL-ACC-06", "a node-only one-way sign does not close the junction",
  node_allows({ traffic_sign = "NL:C3" }), classes_to_string(true, true, true))

equals("NL-ACC-06", "but a node-only C2 is a geslotenverklaring and does",
  node_allows({ traffic_sign = "NL:C2" }), classes_to_string(false, false, false))

-- A node has no length, so no segment is drawn for it and no speed is ever
-- reported for it. The way rule exists to keep the API's promise of a legal
-- speed per metre of geometry; at a point there is no promise to break, and
-- treating a limit as a refusal closed the entrance to every built-up area.
equals("conservative", "a speed stored on a node does not close it",
  node_allows({ maxspeed = "30" }), classes_to_string(true, true, true))

equals("conservative", "nor does a class speed on a node",
  node_allows({ ["maxspeed:moped"] = "30" }), classes_to_string(true, true, true))

equals("conservative", "nor does an A1 speed-limit sign on a node",
  node_allows({ traffic_sign = "NL:A1[30]" }), classes_to_string(true, true, true))

-- D1 is the roundabout sign and D2 is "keep right". They stand at essentially
-- every roundabout and divided-road island in the Netherlands. Closing those
-- nodes made the junctions impassable to all three classes, which is not what
-- either sign says.
equals("NL-ACC-09", "a roundabout sign on a node does not close the roundabout",
  node_allows({ traffic_sign = "NL:D1" }), classes_to_string(true, true, true))

equals("NL-ACC-09", "nor does a keep-right sign",
  node_allows({ traffic_sign = "NL:D2" }), classes_to_string(true, true, true))

-- The way rule is unchanged: there, a prescribed movement the edge cannot
-- express still closes, because accepting it can issue a forbidden manoeuvre.
allows("NL-ACC-09", "a roundabout sign on a way still closes it",
  { highway = "residential", traffic_sign = "NL:D1" }, { false, false, false })

equals("conservative", "a dimensional restriction node closes every unknown vehicle size",
  node_allows({ maxwidth = "1.4" }), classes_to_string(false, false, false))

-- Country dispatch -------------------------------------------------------
-- What a country module is for: the same tags mean different things in
-- different countries, and an unmodelled country must not inherit Dutch law.

local function country_of(tags)
  local country = access.country_for(tags)
  return country and country.code or "unsupported"
end

equals("compliance-R1", "the official boundary attributes a complete Dutch way",
  country_of({ ["amgraph:country"] = "NL" }), "NL")

equals("compliance-R1", "a foreign way does not inherit Dutch rules",
  country_of({ ["amgraph:country"] = "unsupported" }), "unsupported")

equals("compliance-R1", "a way missing boundary attribution is forbidden",
  country_of({ highway = "residential" }), "unsupported")

local function under(country, tags)
  local a, b, c = triple(access.classes(tags, country))
  return classes_to_string(a, b, c)
end

equals("compliance-R2", "a way with no supported country closes every carrier",
  under(nil, { highway = "residential" }),
  classes_to_string(false, false, false))

local unsupported_flags = access.carrier_flags({
  highway = "residential",
  traffic_sign = "NL:C2",
  ["amgraph:country"] = "unsupported",
})
equals("compliance-R2", "an unsupported way cannot reach country sign parsing",
  table.concat({
    unsupported_flags.moped_forward,
    unsupported_flags.moped_backward,
    unsupported_flags.motorcycle_forward,
    unsupported_flags.motorcycle_backward,
    unsupported_flags.truck_forward,
    unsupported_flags.truck_backward,
  }, ","),
  "false,false,false,false,false,false")

equals("compliance-R2", "a way explicitly inside the Netherlands uses Dutch rules",
  under(nil, { highway = "residential", ["amgraph:country"] = "NL" }),
  classes_to_string(true, true, true))

-- The road authority's verdict -------------------------------------------
-- infra/official_access.py writes amgraph:* tags into the extract from
-- Rijkswaterstaat's Wegkenmerkendatabase, which knows where the signs are.
-- It answers the mandatory-use rule, art. 6 lid 1, that OSM states on only a
-- fraction of the roads it binds.

allows("NL-ACC-02", "the authority can close a street to a bromfiets",
  { highway = "residential", ["amgraph:bromfiets"] = "no" }, { true, false, true })

allows("NL-ACC-03", "and to a snorfiets",
  { highway = "residential", ["amgraph:snorfiets"] = "no" }, { false, true, true })

allows("NL-ACC-02", "and to both at once",
  { highway = "residential", ["amgraph:snorfiets"] = "no",
    ["amgraph:bromfiets"] = "no" }, { false, false, true })

-- But it does not override a sign the mapper recorded on the path itself. The
-- overlay exists for mandatory use, which is a rule about carriageways, and it
-- reaches a cycle path only through a geometric match against a dataset whose
-- own documentation warns that sign-to-road coupling is often wrong. A
-- `traffic_sign=NL:G12a` is a record of the sign on the ground, which is the
-- thing the law turns on. Letting the match win closed fiets/bromfietspaden
-- the statute positively sends riders onto, and cost the Utrecht to Amsterdam
-- corridor most of its length.
allows("NL-ACC-02", "it does not override a G12a the mapper recorded",
  { highway = "cycleway", traffic_sign = "NL:G12a", ["amgraph:bromfiets"] = "no" },
  { true, true, false })

allows("NL-ACC-03", "nor an explicit class permission on a path",
  { highway = "cycleway", mofa = "designated", ["amgraph:snorfiets"] = "no" },
  { true, false, false })

allows("NL-ACC-02", "but on a carriageway, where the rule lives, it still closes",
  { highway = "residential", moped = "yes", ["amgraph:bromfiets"] = "no" },
  { true, false, true })

allows("NL-ACC-02", "and it still closes an unsigned path OSM says nothing about",
  { highway = "cycleway", traffic_sign = "NL:G12a", moped = "designated",
    ["amgraph:bromfiets"] = "no" }, { true, true, false })

-- `roadway_only` is the exception, and the only one: RVV art. 5 lid 8 is
-- precisely a rule that the G11 does not mean what it usually means, so
-- deferring to the sign would defeat it. See NL-ACC-04.
allows("NL-ACC-04", "art. 5 lid 8 does override the G11 it is written against",
  { highway = "cycleway", traffic_sign = "NL:G11", mofa = "designated",
    ["amgraph:snorfiets"] = "roadway_only" }, { false, false, false })

allows("NL-ACC-04", "and it reaches the snorfiets alone",
  { highway = "cycleway", traffic_sign = "NL:G12a",
    ["amgraph:snorfiets"] = "roadway_only" }, { false, true, false })

-- WKD is a geometric match whose own documentation warns that sign-to-road
-- coupling is often wrong, so its `no` may close a way and never open one.
-- `on_roadway` is a different statement and has to be read as one: it is
-- infra/official_access.py reporting that it looked beside this carriageway
-- and found no path this class may lawfully use. RVV art. 5 lid 2 and art. 6
-- lid 2 then *require* the rijbaan, so honouring the mandatory-use closure as
-- well would leave the rider nowhere legal at all. It lifts that one closure.

allows("NL-ACC-02", "on_roadway lifts a mandatory-use closure for a bromfiets",
  { highway = "residential", moped = "use_sidepath",
    ["amgraph:bromfiets"] = "on_roadway" }, { true, true, true })

allows("NL-ACC-03", "and for a snorfiets",
  { highway = "residential", mofa = "use_sidepath",
    ["amgraph:snorfiets"] = "on_roadway" }, { true, true, true })

allows("NL-ACC-02", "but only for the class it names",
  { highway = "residential", moped = "use_sidepath", mofa = "use_sidepath",
    ["amgraph:bromfiets"] = "on_roadway" }, { false, true, true })

allows("NL-ACC-01", "and it cannot reach an autoweg",
  { highway = "trunk", motorroad = "yes", ["amgraph:bromfiets"] = "on_roadway" },
  { false, false, false })

allows("NL-ACC-02", "nor open an unsigned cycleway",
  { highway = "cycleway", ["amgraph:snorfiets"] = "on_roadway",
    ["amgraph:bromfiets"] = "on_roadway" }, { false, false, false })

allows("NL-ACC-02", "nor overrule an explicit refusal in OSM",
  { highway = "residential", moped = "no", ["amgraph:bromfiets"] = "on_roadway" },
  { true, false, true })

allows("NL-ACC-06", "nor a signed prohibition",
  { highway = "residential", moped = "use_sidepath", traffic_sign = "NL:C13",
    ["amgraph:bromfiets"] = "on_roadway" }, { false, false, true })

-- The overlay is matched onto OSM geometrically, so some of it lands on the
-- wrong way. Every opening it can express is therefore bounded to the one case
-- the law leaves no discretion in. Outside a mandatory-use closure on a
-- carriageway, and an unsigned path for a snorfiets, no value may open a way
-- that was closed for any other reason.
for _, closed in ipairs({
  { highway = "motorway" },                                  -- art. 42
  { highway = "trunk", motorroad = "yes" },                  -- art. 42
  { highway = "residential", moped = "no", mofa = "no" },    -- its own tags
  { highway = "cycleway", traffic_sign = "NL:G11" },         -- signed G11
  { highway = "footway" },                                   -- never motorised
}) do
  local base_a, base_b, base_c = triple(access.classes(closed, NL))
  for _, key in ipairs({ "amgraph:snorfiets", "amgraph:bromfiets" }) do
    for _, value in ipairs({ "no", "yes", "on_roadway", "designated", "" }) do
      local tags = {}
      for k, v in pairs(closed) do
        tags[k] = v
      end
      tags[key] = value
      local a, b, c = triple(access.classes(tags, NL))
      equals("NL-ACC-02",
        string.format("%s=%s never opens a closed %s", key, value, closed.highway),
        classes_to_string(a and base_a, b and base_b, c and base_c),
        classes_to_string(a, b, c))
    end
  end
end

-- A brommobiel is on none of these paths and takes none of these lifts: art. 6
-- lid 3 puts it on the rijbaan, so it is never subject to a mandatory-use
-- closure in the first place.
for _, value in ipairs({ "no", "yes", "on_roadway" }) do
  local _, _, plain = triple(access.classes({ highway = "residential" }, NL))
  local _, _, overlaid = triple(access.classes(
    { highway = "residential", ["amgraph:snorfiets"] = value,
      ["amgraph:bromfiets"] = value }, NL))
  equals("NL-ACC-05", "a brommobiel ignores the overlay value " .. value,
    tostring(overlaid), tostring(plain))
end

-- NL-ACC-05. WKD models snorfiets and bromfiets, and art. 6 lid 3 keeps a
-- brommobiel on the rijbaan: a closure that exists because a compulsory
-- sidepath runs alongside does not reach a class that may not use that path.
for _, highway in ipairs({ "residential", "tertiary", "unclassified" }) do
  local _, _, plain = triple(access.classes({ highway = highway }, NL))
  local _, _, overlaid = triple(access.classes(
    { highway = highway, ["amgraph:snorfiets"] = "no",
      ["amgraph:bromfiets"] = "no" }, NL))
  equals("NL-ACC-05", "the overlay leaves a brommobiel on a " .. highway,
    tostring(overlaid), tostring(plain))
end

-- A blanket ban plus a class-specific permission must not return before the
-- cycle-infrastructure branch, or it hands a four-wheeler a fietspad. Six ways
-- in the country are tagged this way, so no sampled route reaches it; only the
-- exhaustive pass in api/tests/test_access_rules.py does.
allows("NL-ACC-05", "a blanket ban cannot lift a brommobiel onto a fietspad",
  { highway = "cycleway", access = "no", motor_vehicle = "yes" }, { false, false, false })

-- The register's own sign, on a path the mapper left unsigned. `yes` means
-- infra/official_access.py found a G11 or a G12a standing on this path in
-- Rijkswaterstaat's sign register.
--
-- It reaches the snorfiets and nothing else, and the asymmetry is the reason
-- it is safe rather than a caution. Art. 5 lid 1 admits a snorfiets to a
-- verplicht fietspad and a fiets/bromfietspad alike, so the register only has
-- to establish that one of the two is here and confusing them costs nothing;
-- measured against the ways OSM does sign, it disagrees on 0.47% of these. For
-- a bromfiets the same two signs are opposite answers, the measured
-- disagreement is 3.00%, and losing that coin flip puts the vehicle on a
-- verplicht fietspad. Art. 6 lid 2 gives it the rijbaan instead, for free.
allows("NL-ACC-03", "the register opens an unsigned path for a snorfiets",
  { highway = "cycleway", ["amgraph:snorfiets"] = "yes" },
  { true, false, false })

allows("NL-ACC-02", "but never for a bromfiets, whose answer it cannot settle",
  { highway = "cycleway", ["amgraph:bromfiets"] = "yes" }, { false, false, false })

allows("NL-ACC-05", "and never for a brommobiel",
  { highway = "cycleway", ["amgraph:snorfiets"] = "yes",
    ["amgraph:bromfiets"] = "yes" }, { true, false, false })

allows("NL-ACC-03", "a sign on the way still wins over it",
  { highway = "cycleway", traffic_sign = "NL:G13",
    ["amgraph:snorfiets"] = "yes" }, { false, false, false })

allows("NL-ACC-03", "and an explicit refusal in OSM still wins",
  { highway = "cycleway", mofa = "no", ["amgraph:snorfiets"] = "yes" },
  { false, false, false })

allows("NL-ACC-01", "it cannot reach a road, let alone a motorway",
  { highway = "motorway", ["amgraph:snorfiets"] = "yes",
    ["amgraph:bromfiets"] = "yes" }, { false, false, false })

allows("NL-ACC-02", "nor open an ordinary carriageway closed by its own tag",
  { highway = "residential", moped = "no", ["amgraph:bromfiets"] = "yes" },
  { true, false, true })

allows("NL-ACC-05", "nor lift a brommobiel onto a path it may never use",
  { highway = "cycleway", access = "no", motor_vehicle = "yes",
    ["amgraph:snorfiets"] = "yes" }, { false, false, false })

-- Restriction families only restrict when the value states a limit ---------
-- `hazmat=designated` marks a road as a route *for* dangerous goods. Reading
-- the designation as a prohibition closed arterial roads to every class, and
-- with Utrecht's Ruimteweg shut a brommobiel could not leave the city.

allows("NL-ACC-06", "a designated hazmat route is not closed to anybody",
  { highway = "secondary", maxspeed = "50", hazmat = "designated" },
  { true, true, true })

allows("NL-ACC-06", "but an actual hazmat prohibition still closes every class",
  { highway = "secondary", maxspeed = "50", hazmat = "no" },
  { false, false, false })

allows("NL-ACC-06", "and so does a conditional one, whose value is a schedule",
  { highway = "secondary", maxspeed = "50", ["hazmat:conditional"] = "no @ (22:00-06:00)" },
  { false, false, false })

allows("NL-ACC-06", "maxheight=default states the ordinary maximum, not a limit",
  { highway = "secondary", maxspeed = "50", maxheight = "default" },
  { true, true, true })

allows("NL-ACC-06", "a signed height limit still closes every class",
  { highway = "secondary", maxspeed = "50", maxheight = "2.2" },
  { false, false, false })

equals("NL-ACC-06", "a designated hazmat route does not close the node either",
  node_allows({ hazmat = "designated" }), classes_to_string(true, true, true))

equals("NL-ACC-06", "but a hazmat prohibition on a node does",
  node_allows({ hazmat = "no" }), classes_to_string(false, false, false))

-- Result -----------------------------------------------------------------

print(string.format("%d checks, %d failures", checks, failures))
os.exit(failures == 0 and 0 or 1)
