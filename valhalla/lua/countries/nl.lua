-- Netherlands. Every branch cites the rule id it implements in
-- docs/countries/nl.md.
--
-- A country module answers four questions the shared core cannot: which classes
-- of road rights exist here and what OSM calls them, what the local cycle-path
-- signs mean, what an unsigned cycle path should be assumed to be, and which
-- roads a class is barred from outright.

local country = {
  code = "NL",

  -- Prefix on `traffic_sign` values, e.g. "NL:G12a". Also how the core works
  -- out which country a way is in on a multi-country extract.
  sign_prefix = "NL",

  -- NL-ACC-02. Both 45 km/h two-wheelers follow RVV art. 6, but their
  -- carriers stay distinct so a border never changes the vehicle being routed.
  classes = {
    {
      code = "snorfiets",
      carrier = "moped",
      access_keys = { "mofa" },

      -- RVV art. 2b: bicycle signs and bicycle rules apply to a snorfiets, so
      -- `bicycle=no` on a cycle path bars it and a `bicycle=use_sidepath`
      -- obligation binds it.
      bicycle_rules = true,
      cycle_infrastructure = true,

      -- The road authority's verdict, written by infra/official_access.py.
      overlay = "amgraph:snorfiets",

      -- This class alone may be *opened* on an unsigned cycle path by the sign
      -- register, because for a snorfiets a G11 and a G12a mean the same thing
      -- and confusing them costs nothing. See the long note in access.lua.
      overlay_opens_cycle_infrastructure = true,
    },
    {
      code = "bromfiets",
      carrier = "motorcycle",
      access_keys = { "moped" },
      closing_keys = { "speed_pedelec" },
      cycle_infrastructure = true,
      overlay = "amgraph:bromfiets",
    },
    {
      code = "brommobiel",
      carrier = "truck",
      access_keys = { "motorcar", "motor_vehicle" },

      -- NL-ACC-05. RVV art. 6 lid 3 puts it on the rijbaan, and that is
      -- mandatory rather than permissive: no sign and no tag admits it to a
      -- cycle path.
      cycle_infrastructure = false,
    },
    {
      -- NL-DEF-06, NL-ACC-10. Art. 7 lets it choose between the trottoir, the
      -- voetpad, the fietspad, the fiets/bromfietspad and the rijbaan, so no
      -- sidepath obligation binds it and no overlay is needed.
      code = "gehandicaptenvoertuig",
      carrier = "bus",

      -- OSM has no key for it, and borrowing `moped` would be the error this
      -- class exists to avoid: art. 1 defines it as a vehicle that "geen
      -- bromfiets is", so a road closed to traffic except bromfietsen stays
      -- closed to it. 452 Dutch ways are tagged that way, measured 2026-10-08.
      access_keys = {},

      -- Every tag below closes it where the tag could be the trace of a sign
      -- that binds it, even where the same tag usually means one that does
      -- not. Each costs a detour when it is wrong; the other reading costs a
      -- fine. See docs/countries/nl.md NL-ACC-10.
      --
      -- Off the cycle network: `moped=no` and `mofa=no` are what a C13 or C15
      -- leaves when mapped as tags. `motor_vehicle=no` and `motorcar=no` are
      -- usually a C12 or C6, which do not bind it, but OSM's motor_vehicle
      -- covers mopeds, so either tag can also be a loosely mapped C13.
      roadway_refusal_keys = { "moped", "mofa", "motor_vehicle", "motorcar" },

      -- The road authority's verdict that mopeds may not use a carriageway,
      -- which may be a prohibition binding this class as well as a sidepath
      -- obligation binding only them.
      roadway_refusal_overlays = { "amgraph:bromfiets", "amgraph:snorfiets" },

      -- Everywhere: a bicycle refusal can be a C14 or a C15, on a path as on a
      -- road, and the C15 binds it.
      refusal_keys = { "bicycle" },

      -- On a cycle path a moped permission means a G12a: NL-ACC-02 admits a
      -- bromfiets to that sign and to no other, and the Netherlands marks it
      -- `designated` 68,244 times. A G12a admits this class. `mofa` is not
      -- evidence, because a snorfiets permission is also what a G13 carries,
      -- and a refusal of a vehicle a G12a admits means the path is not one.
      cycle_evidence_keys = { "moped" },
      cycle_evidence_vetoes = { "bicycle", "mofa" },

      -- A one-way mapped for another vehicle may be the only trace of a C2,
      -- C3 or C4. Its exemption (`no`) names that vehicle and not this one.
      -- It rides the bus carrier, and upstream passes a bus where these
      -- stand. Both are built to stop everything else.
      impassable_barriers = { bus_trap = true, sump_buster = true },

      oneway_restriction_keys = {
        "oneway:bicycle", "oneway:mofa", "oneway:moped",
        "oneway:motor_vehicle", "oneway:motorcar",
      },
      cycle_infrastructure = true,
    },
  },

  -- NL-ACC-01. RVV 1990 art. 42: use of an autosnelweg or autoweg is permitted
  -- only to a *motorvoertuig* able to do 60 resp. 50 km/h. A bromfiets is not a
  -- motorvoertuig at all (NL-DEF-05), so no class here is inside the permission
  -- — and none could reach the speed anyway. Both road types are defined by
  -- their sign, reaching OSM as highway=motorway and motorroad=yes.
  --
  -- The article is a permission rather than a prohibition, which is easy to
  -- read the wrong way round. Art. 43 is not the authority and is the one a
  -- reader reaches for: it covers U-turns and the hard shoulder, and the
  -- often-quoted sentence barring bromfietsen by name is not in the
  -- consolidated text in force.
  forbidden_highways = { motorway = true, motorway_link = true },
  forbidden_when_motorroad = true,

  -- Which cycle-path signs exist here, and which classes each admits. Ordered:
  -- the first sign present on the way wins. A value may also be a function of
  -- the way's tags, for a country whose rule turns on something the sign alone
  -- does not settle; no Dutch rule needs one.
  cycle_signs = {
    -- NL-ACC-02, NL-ACC-03. A fiets/bromfietspad: both two-wheeled classes
    -- belong here, and both are obliged to use it.
    -- NL-ACC-10: art. 7 names the fiets/bromfietspad for a gehandicaptenvoertuig.
    { sign = "G12a", admits = { snorfiets = true, bromfiets = true, gehandicaptenvoertuig = true } },

    -- NL-ACC-03. A verplicht fietspad: bicycle rules, so the snorfiets belongs
    -- and the bromfiets does not. NL-ACC-10: art. 7 names the fietspad for a
    -- gehandicaptenvoertuig.
    { sign = "G11", admits = { snorfiets = true, bromfiets = false, gehandicaptenvoertuig = true } },

    -- An onverplicht fietspad. RVV art. 5 lid 3 admits a snorfiets, but a
    -- combustion-engined one only with the engine off, and the graph is built
    -- long before the rider picks a powertrain. Excluded for everyone: because
    -- using a G13 path is optional, never using it cannot make a route illegal,
    -- only longer.
    { sign = "G13", admits = { snorfiets = false, bromfiets = false, gehandicaptenvoertuig = false } },
  },

  -- No sign in the data. 84,867 of the country's 258,625 cycleways carry
  -- neither a traffic_sign nor a moped or mofa tag — 32.8%, measured
  -- 2026-08-15 — and the two readings are opposites, so the conservative
  -- branch wins. (The 38% quoted here before was a different measurement:
  -- cycleways carrying no `moped` tag, which is a larger set because a way can
  -- be signed without one.)
  unsigned_cycleway = { snorfiets = false, bromfiets = false, gehandicaptenvoertuig = false },

  -- NL-ACC-06. RVV 1990 bijlage I, current text read 2026-08-14.
  -- Art. 2a makes motor-vehicle signs apply to a brommobiel; art. 2b makes
  -- bicycle signs apply to a snorfiets.
  --
  -- `bars_entry` marks the signs that are a geslotenverklaring: a prohibition
  -- on using the road at all, in RVV art. 1's sense of "verbod de betrokken weg
  -- in te rijden of in te gaan alsmede de betrokken weg te gebruiken". Only
  -- those may close a *node*, because closing a node closes the junction in
  -- every direction, and a sign that merely prescribes a movement does not
  -- forbid being there. Without the distinction, every roundabout in the
  -- country became impassable: see the D-series note below.
  closed_signs = {
    { sign = "C1", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "C6", bars = { brommobiel = true }, bars_entry = true },
    { sign = "C9", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "C10", bars = { brommobiel = true }, bars_entry = true },
    { sign = "C12", bars = { brommobiel = true }, bars_entry = true },
    { sign = "C13", bars = { snorfiets = true, bromfiets = true }, bars_entry = true },
    { sign = "C14", bars = { snorfiets = true }, bars_entry = true },
    { sign = "C15", bars = { snorfiets = true, bromfiets = true }, bars_entry = true },
    { sign = "C17", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, valued = true, bars_entry = true },
    { sign = "C18", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, valued = true, bars_entry = true },
    { sign = "C19", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, valued = true, bars_entry = true },
    { sign = "C20", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, valued = true, bars_entry = true },
    { sign = "C21", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, valued = true, bars_entry = true },
    { sign = "C22", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, valued = true, bars_entry = true },

    -- NL-ACC-08. G1/G3 mark the autosnelweg and autoweg, which art. 42 admits
    -- only motorvoertuigen to. G7/G9 identify infrastructure which arts. 5, 6
    -- and 10 do not permit these classes to use. Reading the sign prevents a
    -- contradictory generic highway tag from opening it. These do bar entry:
    -- they mark a road type the class may not be on at all.
    { sign = "G1", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "G3", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "G7", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "G9", bars = { snorfiets = true, bromfiets = true, brommobiel = true }, bars_entry = true },

    -- NL-ACC-09. These signs mandate a movement or prohibit a U-turn. A stock
    -- edge has no way to recover the pictured movement from the sign code. If
    -- the corresponding OSM junction/turn restriction is absent, accepting
    -- the edge can issue a forbidden manoeuvre, so the sign closes the way.
    --
    -- It must not close a node, and no `bars_entry` here says so. D1 is the
    -- roundabout sign and D2 is "keep right", so they stand at essentially
    -- every roundabout and every divided-road island in the country. Applying
    -- them to nodes made those junctions impassable to all three classes,
    -- which is not what the sign says and cut the network to pieces.
    { sign = "D1", bars = { snorfiets = true, bromfiets = true, brommobiel = true } },
    { sign = "D2", bars = { snorfiets = true, bromfiets = true, brommobiel = true } },
    { sign = "D4", bars = { snorfiets = true, bromfiets = true, brommobiel = true } },
    { sign = "D5", bars = { snorfiets = true, bromfiets = true, brommobiel = true } },
    { sign = "D6", bars = { snorfiets = true, bromfiets = true, brommobiel = true } },
    { sign = "D7", bars = { snorfiets = true, bromfiets = true, brommobiel = true } },
    { sign = "F7", bars = { snorfiets = true, bromfiets = true, brommobiel = true } },
  },

  -- C2, the geslotenverklaring in one direction for every vehicle. Named apart
  -- from `closed_signs` because it is read directionally and closes a node
  -- outright, which no per-class entry may do.
  all_directions_sign = "C2",

  -- C3 and C4, which designate a one-way road. They state a direction rather
  -- than a prohibition, so they never close a node.
  oneway_signs = { "C3", "C4" },
}

-- Preserve the existing conservative intersection of moped and pedelec tags
-- while giving the pedelec its own bit throughout the combined graph.
local pedelec = {}
for key, value in pairs(country.classes[2]) do pedelec[key] = value end
pedelec.code = "speed_pedelec"
pedelec.carrier = "taxi"
country.classes[#country.classes + 1] = pedelec
for _, entry in ipairs(country.cycle_signs) do
  entry.admits.speed_pedelec = entry.admits.bromfiets
end
for _, entry in ipairs(country.closed_signs) do
  entry.bars.speed_pedelec = entry.bars.bromfiets
end
country.unsigned_cycleway.speed_pedelec = country.unsigned_cycleway.bromfiets

-- NL-ACC-06 for the gehandicaptenvoertuig, which follows neither the bromfiets
-- column nor the brommobiel one. C9, C13 and C15 name it in their captions. C1
-- names "voertuigen", which art. 1 says it is. C6, C10 and C12 bind
-- motorvoertuigen, which art. 1 says it is not, and C14 binds only one "zonder
-- motor". Every other sign bars it for the reason it bars the other classes.
--
-- Both lists are written out, and a sign in neither stops the build: a sign
-- added to closed_signs must be decided for this class, not inherited.
local gehandicapt_barred = {
  C1 = true, C9 = true, C13 = true, C15 = true,
  C17 = true, C18 = true, C19 = true, C20 = true, C21 = true, C22 = true,
  G1 = true, G3 = true, G7 = true, G9 = true,
  D1 = true, D2 = true, D4 = true, D5 = true, D6 = true, D7 = true, F7 = true,
}
local gehandicapt_not_barred = { C6 = true, C10 = true, C12 = true, C14 = true }
for _, entry in ipairs(country.closed_signs) do
  assert(gehandicapt_barred[entry.sign] or gehandicapt_not_barred[entry.sign],
    "sign " .. entry.sign .. " is not decided for the gehandicaptenvoertuig")
  entry.bars.gehandicaptenvoertuig = gehandicapt_barred[entry.sign] or false
end
return country
