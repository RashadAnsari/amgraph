# Multi-country graph architecture

[Documentation](README.md) · [The access model](access-model.md) · [Adding a country](adding-country.md)

Every supported country contributes to the same routing graph. The Python
country registry discovers country modules, and the Lua adapter loads their
matching access modules by ISO code. Preparation, audits, merge, route checks,
manifest creation and ZIP packaging all consume the complete registry.

## Where a country's facts live

`valhalla/lua/access.lua` evaluates tags using the applicable country module.
Each module defines its classes, carriers, sign vocabulary, infrastructure
permissions and enrichment evidence. Ways and junctions receive geographic
country attribution from official boundaries. The evaluation order, the meaning
of each tag value and the node rules are in
[the access model](access-model.md); they are the same in every country.

## Classes and carriers

A class is a set of road rights tied to a stable carrier throughout the graph.
Dutch bromfietsen and speed pedelecs both follow RVV art. 6 (NL-ACC-02), but
Belgian law distinguishes them. They therefore use motorcycle and taxi carriers
in both countries. The Dutch pedelec retains the same conservative intersection
of moped and pedelec access tags as the bromfiets.

**Five is the ceiling**, being the stock Valhalla travel modes that read an
access bit of their own: `moped` (512), `motorcycle` (1024), `truck` (8),
`taxi` (32) and `bus` (64), from `baldr/graphconstants.h`. `TaxiCost` and
`BusCost` both derive from `AutoCost` with those masks, so a class riding either
gets auto-family costing and the dimension handling that goes with it. `auto` is
deliberately left alone: it is what the rest of the toolchain reaches for when
it wants to know whether a road exists at all.

The adapter marks every carrier decision with Valhalla's corresponding
`*_tag` flag, including refusals and unassigned carriers. Without these flags,
the enhance stage can replace our audited access bits with its stock country
defaults. Verified against Valhalla 3.8.3's
[parser](https://github.com/valhalla/valhalla/blob/3.8.3/src/mjolnir/pbfgraphparser.cc)
and [country-access pass](https://github.com/valhalla/valhalla/blob/3.8.3/src/mjolnir/countryaccess.cc),
retrieved 2026-09-10. Runtime cycle-edge probes verify the resulting tiles.

Belgium needs a separate carrier for the speed pedelec: D9 admits it but
not a tweewielige bromfiets klasse B. D7 admits both. The distinction is
permission versus mandatory use, not permission below versus above 50 km/h;
see [BE-ACC-02 and BE-ACC-03](countries/be.md) for primary sources and retrieval dates.

A `cycle_signs` entry's `admits` value may also be a function of the way's tags.
The invented second-country fixture tests that mechanism; it is not Belgian law.

Two classes may not share a carrier in the Lua. They would be indistinguishable
in the graph, so the router would answer for whichever it happened to ask about;
`access.prepare` refuses the country at load rather than letting that happen.

A fourth access class is not an exception, because the ceiling is five.
`valhalla/lua/spec/second_country_spec.lua` pins all of this against an invented
country that exists nowhere else, so a change that quietly moves a country's
facts back into shared code fails rather than waits to be noticed.

## Combined-graph invariants

- Every build includes every registered country. Missing input, boundary, audit
  or rules-version evidence aborts the build; there is no preferred country.
- The merger streams sorted OSM identities and rejects conflicting object
  versions. Official polygons select a way's owning input, regardless of file
  order. Junctions receive the same geographic attribution.
- Before attribution, standalone building outlines without highway, route or
  railway tags are omitted. Every other way and every relation is retained;
  reference completion restores relation members and their original node tags.
  The highway count must equal the audited input's count.
- An edge wholly covered by the union of supported territories can cross a
  border. Each country's enriched tags remain separately scoped, and its
  carrier flags are intersected with the others. A shared junction likewise
  intersects the applicable node rules. Unknown territory and boundary gaps
  stay closed; polygons are never buffered to manufacture coverage. A way
  missing from any owning country's extract also stays closed, and the merge
  report counts these missing-evidence closures by geographic ownership.
- One ZIP carries one tile archive, every country's boundary, all legal zones
  and a country-indexed manifest. A rules mismatch for any covered country
  invalidates the release. The runtime gate checks every class in every country
  and the declared cross-border fixtures. Real cycle-edge probes also check
  allowed and barred carriers against the running tiles.
