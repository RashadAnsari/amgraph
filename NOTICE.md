# Licensing

Two things are published here and they are not under the same terms.

## The code

Everything in this repository — the access rules in `valhalla/lua/`, the overlay
writer in `infra/`, the `amgraph-rules` package, the build, the tests and
`docs/rules.md` — is Copyright Rashad Ansari and licensed under the
[PolyForm Noncommercial License 1.0.0](LICENSE.md).

Read it, run it, change it, build your own graph with it, publish papers about
it. What you may not do is use it for a commercial purpose. That right is not
granted to anyone, and the copyright holder keeps it. If you want it, ask.

Personal study, hobby projects, research, and use by charities, schools, public
research bodies, health and safety organisations and government institutions are
all permitted, whatever their funding. The licence says so in its own words; this
paragraph is a summary and the licence governs.

## The published graph

The `tiles.tar`, `admin.sqlite` and boundary files attached to each release are
**not** covered by that licence, and could not be.

They are derived from OpenStreetMap, which is © OpenStreetMap contributors and
licensed under the [Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/).
ODbL §3.1 grants rights that "explicitly include commercial use, and do not
exclude any field of endeavour", and §4.7(a) forbids imposing any term that
restricts the rights it grants. A Derivative Database, which is what a routing
graph built from an extract is, must be offered under ODbL when it is publicly
used.

So the released graph is offered under ODbL 1.0, and anyone may use it for
anything, commercially included, provided they attribute OpenStreetMap and
share alike. Choosing otherwise would not be enforceable and would breach the
terms the data was obtained under.

The Rijkswaterstaat Wegkenmerkendatabase and the Kadaster BRK boundaries that
also feed the graph are public domain and impose no further condition.

## What that means in practice

The graph is free for anyone to serve. Building, correcting and maintaining one
is not: that is the code, that is where the work is, and a graph a week old is a
graph that routes riders by last week's cycle paths.
