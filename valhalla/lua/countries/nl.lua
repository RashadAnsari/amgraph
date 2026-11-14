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

  -- The two Dutch classes, each on a carrier of its own so a border never
  -- changes the vehicle being routed.
  classes = {
    {
      code = "bromfiets",
      carrier = "motorcycle",
      access_keys = { "moped" },
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
    -- NL-ACC-02. A fiets/bromfietspad: the bromfiets belongs here and is
    -- obliged to use it.
    { sign = "G12a", admits = { bromfiets = true } },

    -- NL-ACC-02. A verplicht fietspad, which the bromfiets may not use.
    { sign = "G11", admits = { bromfiets = false } },

    -- An onverplicht fietspad, which the bromfiets may not use either.
    { sign = "G13", admits = { bromfiets = false } },
  },

  -- No sign in the data. A large share of Dutch cycleways carry neither a
  -- traffic_sign nor a moped tag, and only a G12a admits the bromfiets, so the
  -- conservative branch wins.
  unsigned_cycleway = { bromfiets = false },

  -- NL-ACC-06. A C17-C21 value no class can exceed: tonnes for mass and axle
  -- load, metres for length, height and width.
  unbound_from = {
    maxweight = 1.0, maxaxleload = 1.0, maxlength = 6.5, maxheight = 2.5, maxwidth = 2.0,
  },

  -- NL-ACC-06. RVV 1990 bijlage I, current text read 2026-11-14.
  -- Art. 2a makes motor-vehicle signs apply to a brommobiel. A brommobiel is
  -- still a bromfiets, and
  -- whether art. 2a lifts a caption naming bromfietsen is unsettled, so C13
  -- and C15 close it too.
  --
  -- `bars_entry` marks the signs that are a geslotenverklaring: a prohibition
  -- on using the road at all, in RVV art. 1's sense of "verbod de betrokken weg
  -- in te rijden of in te gaan alsmede de betrokken weg te gebruiken". Only
  -- those may close a *node*, because closing a node closes the junction in
  -- every direction, and a sign that merely prescribes a movement does not
  -- forbid being there. Without the distinction, every roundabout in the
  -- country became impassable: see the D-series note below.
  closed_signs = {
    { sign = "C1", bars = { bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "C6", bars = { brommobiel = true }, bars_entry = true },
    { sign = "C9", bars = { bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "C10", bars = { brommobiel = true }, bars_entry = true },
    { sign = "C12", bars = { brommobiel = true }, bars_entry = true },
    { sign = "C13", bars = { bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "C15", bars = { bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "C17", bars = { bromfiets = true, brommobiel = true }, valued = true, bars_entry = true, unbound_by = "maxlength" },
    { sign = "C18", bars = { bromfiets = true, brommobiel = true }, valued = true, bars_entry = true, unbound_by = "maxwidth" },
    { sign = "C19", bars = { bromfiets = true, brommobiel = true }, valued = true, bars_entry = true, unbound_by = "maxheight" },
    { sign = "C20", bars = { bromfiets = true, brommobiel = true }, valued = true, bars_entry = true, unbound_by = "maxaxleload" },
    { sign = "C21", bars = { bromfiets = true, brommobiel = true }, valued = true, bars_entry = true, unbound_by = "maxweight" },
    { sign = "C22", bars = { bromfiets = true, brommobiel = true }, valued = true, bars_entry = true },

    -- NL-ACC-08. G1/G3 mark the autosnelweg and autoweg, which art. 42 admits
    -- only motorvoertuigen to. G7/G9 identify infrastructure which arts. 5, 6
    -- and 10 do not permit these classes to use. Reading the sign prevents a
    -- contradictory generic highway tag from opening it. These do bar entry:
    -- they mark a road type the class may not be on at all.
    { sign = "G1", bars = { bromfiets = true, brommobiel = true }, bars_entry = true },
    { sign = "G3", bars = { bromfiets = true, brommobiel = true }, bars_entry = true },
    -- NL-ACC-12. RVV art. 67 lid 2: an onderbord's text decides what the sign
    -- allows, so a confirmed "brom-fietsen toegestaan" lifts the G7 for the
    -- class it admits. Only the overlay can say a plate is confirmed.
    { sign = "G7", bars = { bromfiets = true, brommobiel = true }, bars_entry = true,
      lifted_by_plate = true },
    { sign = "G9", bars = { bromfiets = true, brommobiel = true }, bars_entry = true },

    -- NL-ACC-09. These signs mandate a movement or prohibit a U-turn. A stock
    -- edge has no way to recover the pictured movement from the sign code. If
    -- the corresponding OSM junction/turn restriction is absent, accepting
    -- the edge can issue a forbidden manoeuvre, so the sign closes the way.
    --
    -- It must not close a node, and no `bars_entry` here says so. D1 is the
    -- roundabout sign and D2 is "keep right", so they stand at essentially
    -- every roundabout and every divided-road island in the country, and on a
    -- node they would close the junction, which is not what the sign says.
    { sign = "D1", bars = { bromfiets = true, brommobiel = true } },
    { sign = "D2", bars = { bromfiets = true, brommobiel = true } },
    { sign = "D4", bars = { bromfiets = true, brommobiel = true } },
    { sign = "D5", bars = { bromfiets = true, brommobiel = true } },
    { sign = "D6", bars = { bromfiets = true, brommobiel = true } },
    { sign = "D7", bars = { bromfiets = true, brommobiel = true } },
    { sign = "F7", bars = { bromfiets = true, brommobiel = true } },
  },

  -- C2, the geslotenverklaring in one direction for every vehicle. Named apart
  -- from `closed_signs` because it is read directionally and closes a node
  -- outright, which no per-class entry may do.
  all_directions_sign = "C2",

  -- C3 and C4, which designate a one-way road. They state a direction rather
  -- than a prohibition, so they never close a node.
  oneway_signs = { "C3", "C4" },
}

return country
