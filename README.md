# amgraph

[![Graph](https://github.com/RashadAnsari/amgraph/actions/workflows/graph.yml/badge.svg?branch=master)](https://github.com/RashadAnsari/amgraph/actions/workflows/graph.yml?query=branch%3Amaster)
[![Check](https://github.com/RashadAnsari/amgraph/actions/workflows/check.yml/badge.svg?branch=master)](https://github.com/RashadAnsari/amgraph/actions/workflows/check.yml?query=branch%3Amaster)
[![Latest graph](https://img.shields.io/github/v/release/RashadAnsari/amgraph?label=graph&sort=semver&display_name=release)](https://github.com/RashadAnsari/amgraph/releases/latest)

A routing graph for Dutch AM-licence vehicles: mopeds, speed pedelecs and
microcars.

These classes follow their own access rules. A bromfiets must use the
fiets/bromfietspad where one exists, may not use an ordinary fietspad, and may
never use an autosnelweg or an autoweg. A snorfiets follows bicycle rules
instead. A brommobiel uses the roadway only. General-purpose routing engines
model none of this, so the whole project is the access rules and the evidence
that they hold.

The result is a [Valhalla](https://valhalla.github.io/valhalla/) graph in which
a road a class may not use is not merely expensive: it is **absent**. Serve it
with `valhalla_service` and route with the `moped`, `motorcycle` or `truck`
costing, and the answers are ones a Dutch rider can lawfully follow.

```
OpenStreetMap extract ─┐
Rijkswaterstaat WKD   ─┼─▶ infra/official_access.py ─▶ enriched .osm.pbf
BRK boundaries        ─┘         the authority's own                │
                                 access decisions,                  ▼
                                 matched onto OSM ways      valhalla/build.sh
                                                            with valhalla/lua/
                                                                    │
                                                                    ▼
                                                                Release N
```

## Which class rides where

| Class | Plate | Limit | Carrier | May use |
| --- | --- | --- | --- | --- |
| `snorfiets` | Blue | 25 km/h | `moped` | Bicycle infrastructure, under bicycle rules |
| `bromfiets` | Yellow | 45 km/h | `motorcycle` | The fiets/bromfietspad, and the roadway |
| `speed_pedelec` | Yellow | 45 km/h | `motorcycle` | The same as a bromfiets |
| `brommobiel` | Yellow | 45 km/h | `truck` | The roadway only |

Each class borrows a stock Valhalla travel mode to carry its access bit, which
is how a graph built here routes on an unmodified Valhalla. Five is the ceiling,
being the stock modes that read an access bit of their own.

The identifiers stay Dutch. They are statutory terms and the rules are written
against them, so a translated identifier would put guesswork between the code
and the law.

## Releases

Every push to `master` and every Monday, the graph is rebuilt from a fresh
extract, gated, and published as **Release N** with one zip attached:

```
manifest.json                     what this graph is, and the rules version it was built under
valhalla.json                     the engine config the tiles were built with
valhalla/tiles.tar                the graph itself
valhalla/admin.sqlite             admin areas, for the country-specific rules
boundaries/netherlands.geojson    the official BRK boundary these tiles cover
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
| Proves | The rules behave as the statute says | No tag combination in the country breaks them |
| Costs | About a minute, no network | About an hour, and 2.3 GB of downloads |
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
make                        # every target, with descriptions
make verify                 # everything CI checks before it spends an hour on tiles
make infra-extract          # an OpenStreetMap extract (1.4 GB)
make infra-official-data    # the road authority's access decisions
make infra-official-access  # match them onto OSM ways
make infra-graph            # build the routing graph (a few minutes)
make test-audit             # every access-tag combination in the country
```

`make verify` needs nothing built and no network. `make test-audit` needs the
enriched extract, and it is the strongest gate here: it reads the extract rather
than sampling routes, so a pass means no way in the country can be offered to a
class the law bars from it. It cannot tell you a graph has stopped routing,
though, because "no lawful path" is a legitimate answer — route against a build
and count the answers before trusting it.

## The rules package

`rules/` is installable on its own as `amgraph-rules`, pinned by tag:

```toml
[tool.uv.sources]
amgraph-rules = { git = "https://github.com/RashadAnsari/amgraph",
                  subdirectory = "rules", tag = "rules-v1.0.0" }
```

It holds the half of the access rules that has to be readable at run time as
well as at build time: the vehicle classes, their carriers, their speed limits
and the municipal by-laws. `valhalla/lua/countries/nl.lua` holds the half that
is baked into the tiles. `manifest.json` records which version of the package a
given release was built under, so a service running a different one can tell.

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

<!-- ci filter probe -->
