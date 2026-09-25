# Licensing

Two things are published here and they are not under the same terms.

## The code

Everything in this repository — the access rules in `valhalla/lua/`, the overlay
writer in `infra/`, the `amgraph-rules` package, the build, the tests and
everything under `docs/` — is Copyright Rashad Ansari and licensed under the
[MIT License](LICENSE.md).

Read it, run it, change it, build your own graph with it, publish papers about
it. The one condition is that the copyright notice and the licence text travel
with any copy or substantial portion you pass on, and that the software comes
with no warranty.

This paragraph is a summary and the licence governs.

## The published graph

The `tiles.tar`, `admin.sqlite` and boundary files attached to each release are
**not** covered by that licence, and could not be.

They are derived from OpenStreetMap, which is © OpenStreetMap contributors and
licensed under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
A Derivative Database, which is what a routing graph built from an extract is,
must be offered under ODbL when it is publicly used.

So the released graph is offered under ODbL 1.0, and anyone may use it provided
they attribute OpenStreetMap and share alike.

The Rijkswaterstaat Wegkenmerkendatabase and the Kadaster BRK boundaries that
also feed the graph are public domain and impose no further condition.

## What that means in practice

The two licences ask different things of you when you redistribute. The code
asks only that you keep the copyright notice. The graph carries ODbL's
attribution and share-alike obligations, which come from OpenStreetMap and
cannot be dropped: ship the graph, ship `NOTICE.md` with it.

What is not free is the work: building, correcting and maintaining a graph, and
a graph a week old is a graph that routes riders by last week's cycle paths.
