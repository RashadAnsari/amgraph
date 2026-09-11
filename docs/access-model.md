# The access model

[Documentation](README.md) · [Architecture](architecture.md) · [Shared country rules](country-rules.md)

`valhalla/lua/access.lua` is a pure function of a way's OSM tags. No Valhalla,
no globals, no side effects, so every rule is unit-testable against a tag table.

What is the same everywhere lives in `access.lua`: how to read an access tag,
how a one-way binds, that a footway is never open to a motor. What differs by
country lives in `valhalla/lua/countries/<cc>.lua`: the cycle-sign vocabulary,
what an *unsigned* path is assumed to be, which roads are barred outright.

The split matters because OSM access tagging is already local. A mapper writes
`moped=designated` on a Dutch bromfietspad because Dutch law puts a bromfiets
there. Reading an explicit tag needs no country. Deciding what an *absent* tag
means does.

## Order of evidence

1. **Country attribution.** A way must be wholly inside the union of verified
   territories. Every country touching it must admit the same carrier.
2. **Outright prohibitions**: motorway, motorroad, footway and friends.
3. **Blanket bans**: `access=no`, `vehicle=no`, unless a class-specific tag
   lifts them, and never lifting a bodied four-wheeler onto cycle
   infrastructure.
4. **Cycle infrastructure**: the sign the mapper wrote, then the sign the
   authority's register reports, then the country's unsigned default.
   An explicit class-specific value beats all three.
5. **Roadway**: open unless something says otherwise, with the country's
   mandatory-use rule and the provision that returns the rider to the
   carriageway when no usable path is established.
6. **The country's authority overlay**, where it has one.
7. **Conditional, directional and lane-scoped tags**, which close the affected
   class because the graph has no clock and cannot select a lane.
8. **Speed readability**, dimensions, hazmat, and the country's sign tables.

## Values

`ALLOW` is `yes`, `designated`, `permissive`. `DENY` is `no`, `use_sidepath`,
`agricultural`, `forestry`, `dismount`. Any other present value is a
restriction: treating `private`, `permit`, `customers` or a typo as absence
would silently turn conditional permission into public access.

`use_sidepath` is a **refusal** for the class it names, because the rider is
obliged onto the parallel path.

An explicit permission cannot override a statutory infrastructure prohibition.
A prohibition removes access at build time, so no downstream cost function can
be tuned into admitting it. The corollary is that a mistake here cannot be
corrected downstream either.

## Restriction families check the value, not the key

A tag in the dimension or hazmat family only restricts when its value states a
limit. `hazmat=designated` and `hazmat=yes` mark a road as a route *for*
dangerous goods, which is a permission for lorries and says nothing about
anybody else; only `hazmat=no` and the conditional forms are prohibitions.
`maxheight=default` and `maxwidth=none` say the ordinary legal maximum applies.

Reading a designation as a prohibition closes whole arterial roads to every
class. Utrecht's Ruimteweg, the western exit from the city, is tagged
`hazmat=designated`; with it shut a brommobiel cannot leave Utrecht.

Measured on the Dutch extract, 2026-08-15:

| Value that states no limit | Ways |
| --- | --- |
| `maxheight=default` | 5,340 |
| `hazmat=designated` | 206 |
| `maxheight=none` | 196 |
| **total reopened** | **5,734** |

Two things worth noticing. The hazmat case is the one that costs a city its
exit, but `maxheight=default` is twenty-six times larger: a handful of ways in
the wrong place matters more than a large number in ordinary ones. And 14,600
ways carry a dimensional value that genuinely *is* a limit and stay closed, so
the conservative behaviour is intact; that whole country contains exactly **one**
real hazmat prohibition.

## Nodes are not short ways

Node access is evaluated separately from way access. `node_classes` handles
access-control nodes, and three rules that read naturally on a way are wrong on
a point:

- **No speed handling.** A node has no length, so no segment is drawn for it
  and no speed is ever reported for it. The way rule exists to keep the API's
  promise of a legal speed per metre of geometry; at a point there is no
  promise to break. Treating a `maxspeed` tag or a speed-limit sign as a refusal
  closes the entrance to every built-up area in the country.
- **Only a prohibition of entry may close a junction.** A sign that *prescribes
  a movement* does not forbid being there. Applying a roundabout or keep-right
  sign to nodes makes those junctions impassable to every class. A country
  module marks the signs that bar entry with `bars_entry = true`, and only those
  reach a node. A one-way sign never closes a node, because it is about
  direction and closing the node kills both directions.
- **An untagged barrier is not a prohibition.** No country modelled here has a
  rule making an untagged bollard or gate forbid passage. Whether the rider may
  be there is the road's own access; whether they can physically get past is
  upstream Valhalla's parser, which models bollard, wall and gate per travel
  mode. Demanding an explicit permission here makes **192,800 nodes**
  impassable in the Netherlands alone, against ~13,000 for every access tag in
  that country combined. An explicit `access=no` or a class-specific `no` on a
  barrier still closes.

`amgraph.lua` **intersects** our node answer with upstream's physical access
mask, clearing barred and unassigned carrier bits. It can never reopen something
upstream shut. That asymmetry is also the fastest diagnostic in the project: if
plain `auto` routes and `truck`/`motorcycle` do not, the fault is in our node
rules.

A way's speed limit and its movement instructions are never node-entry
prohibitions.
