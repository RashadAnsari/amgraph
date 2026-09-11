# amgraph

[![Graph](https://github.com/RashadAnsari/amgraph/actions/workflows/graph.yml/badge.svg?branch=master)](https://github.com/RashadAnsari/amgraph/actions/workflows/graph.yml?query=branch%3Amaster)
[![Check](https://github.com/RashadAnsari/amgraph/actions/workflows/check.yml/badge.svg?branch=master)](https://github.com/RashadAnsari/amgraph/actions/workflows/check.yml?query=branch%3Amaster)
[![Latest graph](https://img.shields.io/github/v/release/RashadAnsari/amgraph?label=graph&sort=semver&display_name=release)](https://github.com/RashadAnsari/amgraph/releases/latest)

One routing graph for AM-licence vehicles across all supported countries.
Belgium and the Netherlands are country entries in the same build; neither is
a fallback or an optional extension of the other. Country-specific access
rules, sources and retrieval dates are in [docs/rules.md](docs/rules.md).

The build enriches each country's OpenStreetMap extract with its own authority
data, audits every input, and merges the results by OSM identity and official
territory. Ways and junctions carry their own country attribution. A supported
border crossing must satisfy every applicable country's rules; territory with
no verified rules stays closed. Conflicting source versions stop the merge.

A class borrows a stock [Valhalla](https://valhalla.github.io/valhalla/) access
bit. The carrier stays stable across these countries:

| Carrier | Belgium | Netherlands | Valhalla costing |
| --- | --- | --- | --- |
| `moped` | `bromfiets_klasse_a` | `snorfiets` | `motor_scooter` |
| `motorcycle` | `bromfiets_klasse_b` | `bromfiets` | `motorcycle` |
| `taxi` | `speed_pedelec` | `speed_pedelec` | `taxi` |
| `truck` | `lichte_vierwieler` | `brommobiel` | `truck` |

Identifiers retain their statutory language. A carrier is storage for a
vehicle's access decision; it does not give that vehicle the rights of a taxi,
truck or motorcycle. Consumers must use the matching rules package for vehicle
selection, speeds and powertrain-dependent legal zones.

## Releases

Every push to `master` and every Monday, the graph is rebuilt from a fresh
extract for every supported country, gated, and published as **Release N** with one zip attached:

```
manifest.json                     country-indexed rules versions, inputs and graph hashes
valhalla.json                     the engine config the tiles were built with
valhalla/tiles.tar                the graph itself
valhalla/admin.sqlite             admin areas, for the country-specific rules
boundaries/be.geojson             official Belgian territory
boundaries/nl.geojson             official Dutch territory
boundaries/legal-zones.geojson    municipal vehicle rules, as polygons
```

Unzip it, point `valhalla_service` at `valhalla.json`, and you are serving it.
Rolling back is picking an older release.

Nothing is published on a red build. A stale graph that obeys the law beats a
fresh one that does not.

## What runs when

Two workflows, on deliberately different budgets. The badges above are both for
`master`.

| | **Check** | **Graph** |
| --- | --- | --- |
| Proves | The rules behave as the statute says | All country inputs pass, and the combined graph routes |
| Costs | About a minute, no network | Country downloads, enrichment, audits and a graph build |
| Every push and pull request | ✅ | — |
| A pull request touching the rules, the build or the tests | ✅ | ✅ |
| Push to `master`, Monday's cron, manual dispatch | ✅ | ✅ |
| Publishes a release | — | On `master`, cron and dispatch only |

A pull request gets the same gates a release does, and publishes nothing. It is
skipped only when the change cannot reach the tiles: an hour of extract, overlay
and tile work proves nothing about a README, and Check still runs on everything.

The two never queue behind each other. Runs that can publish share one
concurrency group, because the release number is read and claimed in separate
steps and two of them in flight would claim the same one; a pull request gets a
group per branch, so it cannot stall `master` for an hour.

## Running it

```sh
make                                   # every target, with descriptions
make verify                            # everything CI checks before it spends an hour on tiles
make country-prepare                   # download and enrich every registered country
make test-audit                        # audit every complete country input; missing data fails
uv run python infra/collect_probes.py  # select real cycle edges for runtime checks
make country-graph                     # merge all countries and build one graph
uv run python infra/verify_routes.py   # check every class and border fixtures on the running router
```

`make verify` needs nothing built and no network. `make test-audit` needs the
enriched inputs for every registered country. It checks the legal invariants
against observed tags; it cannot prove that OSM matches every sign on the road.
The separate running-router gate measures successful routes for every vehicle
in every country and across supported borders.

## The rules package

`rules/` is installable on its own as `amgraph-rules`, pinned by tag:

```toml
[tool.uv.sources]
amgraph-rules = { git = "https://github.com/RashadAnsari/amgraph",
                  subdirectory = "rules", tag = "rules-v2.0.0" }
```

It holds the half of the access rules that has to be readable at run time as
well as at build time: the vehicle classes, their carriers, their speed limits
and the municipal by-laws. `valhalla/lua/countries/<cc>.lua` holds the matching graph rules. Manifest
schema 2 records every country under `countries`, including its rules version,
class-to-carrier mapping and boundary path. There is no top-level default
country or single-country rules version. A consumer must reject a mismatch for
any country the route crosses.

## Working on this

[AGENTS.md](AGENTS.md), and [docs/rules.md](docs/rules.md) for every rule with
its primary source and the date it was read.

## Licence

The **code** is Copyright Rashad Ansari under the
[PolyForm Noncommercial License 1.0.0](LICENSE.md): free for study, research,
hobby projects and noncommercial organisations, and not licensed for commercial
use by anyone else. Ask if you want that.

The **published graph** is derived from OpenStreetMap, © OpenStreetMap
contributors, so it is offered under the
[Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/) and
may be used commercially by anyone with attribution and share-alike. ODbL does
not permit a derived database to carry extra restrictions, and this does not try
to. Rijkswaterstaat's Wegkenmerkendatabase and the Kadaster BRK boundaries are
public domain.

[NOTICE.md](NOTICE.md) sets out both in full, and why they differ.
