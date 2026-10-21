# Licensing

Three kinds of thing are published here, and they are not under the same terms.
Only the first is ours to restrict, so only the first forbids commercial use.

## The code

Everything in this repository — the access rules in `valhalla/lua/`, the overlay
writer in `infra/`, the `amgraph-rules` package, the build, the tests and
everything under `docs/` — is Copyright Rashad Ansari and licensed under the
[PolyForm Noncommercial License 1.0.0](LICENSE.md).

Read it, run it, change it, build your own graph with it, publish papers about
it, for any noncommercial purpose. Charities, schools, public research bodies
and government institutions may use it whatever their funding. Commercial use
needs a separate licence from the copyright holder. Anyone you pass a copy to
must get the licence terms and its `Required Notice:` line with it.

Commits up to and including `ace894b`, and `amgraph-rules` up to and including
`rules-v5.0.2`, were released under the MIT License. Copies of those remain
under it; the change applies to everything after.

This section is a summary and the licence governs.

## The published graph

The `valhalla/tiles.tar` and `valhalla/admin.sqlite` attached to each release
are **not** covered by the code licence, and could not be.

They are derived from OpenStreetMap, which is © OpenStreetMap contributors and
licensed under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
A routing graph built from an extract is a Derivative Database, and §4.4
requires one that is publicly used to be offered only under ODbL. §3.1 of that
licence grants rights that "explicitly include commercial use", and §4.8 forbids
adding any further restriction, so the graph cannot be offered for
noncommercial use only.

So the graph is offered under ODbL 1.0, commercial use included, to anyone who
attributes OpenStreetMap and shares alike.

Two official Dutch sources also feed the access decisions written into it:

- Rijkswaterstaat's Wegkenmerkendatabase, Verkeerstypen and Komgrenzen,
  published under [CC0 1.0](https://data.overheid.nl/dataset/73747-wegkenmerkendatabase-voor-verkeerstypen),
  which imposes no condition.
- NDW's national traffic-sign register, which NDW publishes on
  <https://opendata.ndw.nu/> as open data without naming a licence for the
  register itself. NDW's copyright statement, <https://www.ndw.nu/copyright>,
  applies CC0 to its content unless stated otherwise.

## The boundary files

`boundaries/nl.geojson` and `boundaries/legal-zones.geojson` in each release are
geometry from Kadaster's Basisregistratie Kadaster (BRK) Bestuurlijke Gebieden,
© Kadaster, licensed under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) and retrieved from
<https://api.pdok.nl/kadaster/brk-bestuurlijke-gebieden/ogc/v1>.

`boundaries/nl.geojson` is the Kadaster landgebied unmodified.
`boundaries/legal-zones.geojson` is modified: it keeps the Kadaster municipal
boundaries of the municipalities with their own moped rules and adds the rules
that apply inside each. CC BY 4.0 forbids restricting the licensed material
further, so these files carry Kadaster's terms, commercial use included.

## What that means in practice

The code may not be used commercially without a licence from its author. The
graph and the boundary files may, under the terms of their sources: ship them,
ship this `NOTICE.md` with them, because it carries the OpenStreetMap and
Kadaster attribution those terms require.

What is not free is the work: building, correcting and maintaining a graph, and
a graph a week old is a graph that routes riders by last week's cycle paths.
