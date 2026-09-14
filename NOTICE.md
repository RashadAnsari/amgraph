# Licensing

Two things are published here and they are not under the same terms.

## The code

Everything in this repository — the access rules in `valhalla/lua/`, the overlay
writer in `infra/`, the `amgraph-rules` package, the build, the tests and
everything under `docs/` — is Copyright Rashad Ansari and licensed under the
[MIT License](LICENSE.md).

Read it, run it, change it, build your own graph with it, publish papers about
it, sell it. There is no commercial restriction. The one condition is that the
copyright notice and the licence text travel with any copy or substantial
portion you pass on, and that the software comes with no warranty.

This paragraph is a summary and the licence governs.

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

Belgian national and regional boundaries are adapted from the National
Geographic Institute (NGI/IGN), **Administrative Units / AdminVector**,
retrieved 2026-09-09, under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
[Official source metadata](https://publish.geo.be/geonetwork/srv/api/records/fb1e2993-2020-428c-9188-eb5f75e284b9/formatters/xml).
The build converts the national polygon to GeoJSON and uses the Brussels
regional polygon as a conservative legal-zone boundary. These derived boundary
files retain the source attribution and licence; NGI does not endorse the graph.

## What that means in practice

Both halves are free for anyone to use, including commercially. They are free
under different licences, and the difference matters when you redistribute: the
code asks only that you keep the copyright notice, while the graph carries
ODbL's attribution and share-alike obligations, which come from OpenStreetMap
and cannot be dropped. Ship the graph, ship `NOTICE.md` with it.

What is not free is the work: building, correcting and maintaining a graph, and
a graph a week old is a graph that routes riders by last week's cycle paths.
