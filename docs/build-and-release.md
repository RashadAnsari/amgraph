# Build, verification and releases

[Documentation](README.md) · [Architecture](architecture.md) · [Shared country rules](country-rules.md)

## Releases

Every push to `master` and every Monday, the graph is rebuilt from a fresh
extract for every supported country, gated, and published as **Release N** with one zip attached:

```
manifest.json                     country-indexed rules versions, inputs and graph hashes
valhalla.json                     the engine config the tiles were built with
valhalla/tiles.tar                the graph itself
valhalla/admin.sqlite             engine administrative metadata
boundaries/<cc>.geojson           official territory for each supported country
boundaries/legal-zones.geojson    municipal vehicle rules, as polygons
NOTICE.md                         the licence the tiles carry, and its attribution
```

`NOTICE.md` travels inside the ZIP because the graph is an OpenStreetMap
derivative database: the attribution has to reach whoever holds the tiles, not
only whoever reads the repository.

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
                  subdirectory = "rules", tag = "rules-v2.1.0" }
```

It holds the half of the access rules that has to be readable at run time as
well as at build time: the vehicle classes, their carriers, their speed limits
and the municipal by-laws. `valhalla/lua/countries/<cc>.lua` holds the matching graph rules. Manifest
schema 2 records every country under `countries`, including its rules version,
class-to-carrier mapping and boundary path. A consumer must reject a mismatch for
any country the route crosses.

It also carries the one check a consumer cannot skip, `legal_zones.LegalZones`.
An emission zone turns on the powertrain, which the graph cannot see, so every
route is tested against `boundaries/legal-zones.geojson` after it is found. The
check is here rather than left to each consumer because a route from this graph
is not lawful without it, and it needs nothing beyond the standard library.

