# Adding a country

[Documentation](README.md) · [Shared country rules](country-rules.md) · [Architecture](architecture.md)

The mechanism is finished; the research is the work. Roughly five days per
country, and it does not compress.

A country states its own facts in exactly two modules and one document, and
names itself in two registries. Nothing else in the shared code learns the
country's name, and no existing country is edited to make room for a new one.

Both registries are written by hand and stay that way. A module that is not
named in one of them is not loaded, so the country's territory builds as
unsupported and every way in it closes:

| Registry | Add |
| --- | --- |
| `rules/src/amgraph_rules/countries/__init__.py` | the import and an entry in `_MODELLED` |
| `valhalla/lua/access.lua` | an entry in `M.COUNTRIES`, keyed by ISO code |

## The procedure

1. Read the country's traffic code from a primary source: class definitions,
   cycle-infrastructure rules, the motorway prohibition, the speed articles.
2. Write the rules into `docs/countries/<cc>.md`, in the same shape as the
   countries already there: verbatim quotes, links, retrieval dates, a status
   and a stable identifier per rule. The
   [evidence standard](country-rules.md#evidence-standard) is the bar.
3. Map each rule to OSM tags and **measure the tag coverage** on the country's
   own extract before trusting the mapping. The Dutch measurement is what
   revealed that `designated`, not `yes`, marks a bromfietspad.
4. Add `valhalla/lua/countries/<cc>.lua`: the access classes and the carrier
   each borrows, the OSM keys that name them, the sign vocabulary, the
   unsigned-path assumption, the roads barred outright, and which signs bar
   entry. Name it in `M.COUNTRIES` in `access.lua`, and add assertions to
   `valhalla/lua/spec/access_spec.lua`.
5. Add `rules/src/amgraph_rules/countries/<cc>.py` and name it in `_MODELLED` in
   `countries/__init__.py`. It declares the same classes with the same carriers,
   and the runtime half of the law (see below).
6. Declare the country's data sources and verification fixtures in the same
   module (see below). Then build and audit the combined graph containing every
   registered country.
7. Add the country to the tables in [README.md](../README.md) and
   [docs/README.md](README.md), and link its document.

Steps 1 to 3 are where a country is won or lost. Steps 4 to 7 are an afternoon.

## What the Python module declares

Legal facts, read at run time as well as build time:

| Symbol | Holds |
| --- | --- |
| `RULES_VERSION` | `<cc>-YYYY-MM-DD.N`. The date is when the law was last read |
| `CLASSES` | One `VehicleClass` per class: code, carrier, construction limit, `ClassSpeeds`, statutory `Plate` colours, map marker, whether powertrain matters, and names per language |
| `CountryRules.default_class` | `None` where no class's rights are a subset of the others |
| `MUNICIPAL_ZONES` | Powertrain-dependent and class-blocking by-laws, with `valid_from` / `valid_to` |
| `CountryRules.address_search_bounds` | `SearchBounds` for address lookup |
| `CountryRules.boundary` | `BoundaryDocument`: the properties that identify the official national feature, and the geocoder it wants |
| `CountryRules.source` | The statute the rules were read from |
| `CountryRules.valid_until` | An exclusive deadline where a future legal regime is already published |

Data and fixtures, read by the build:

| Symbol | Holds |
| --- | --- |
| `EXTRACT_URL` | The OSM extract covering the country |
| `BOUNDARY_URL`, `BOUNDARY_LAYER`, `BOUNDARY_FILENAME` | The official territory export, its layer, and the name it takes in the release ZIP |
| `ZONE_LAYER`, `ZONE_ID_KEY` | The official sub-national layer a `MunicipalZone` resolves against |
| `PREPARE_TARGETS` | Optional. Extra `infra/Makefile` targets where the country enriches its extract from its own authority data |
| `AUDIT_TESTS` | Optional. Country-specific test modules the audit runs |
| `SOURCE_RELEASE_FILES` | Optional. Authority release identifiers recorded in the manifest |
| `ROUTE_CHECKS` | Domestic coordinate pairs the running router must answer |
| `REQUIRED_ROUTE_CHECKS` | Optional. Pairs every class must answer, where `ROUTE_CHECKS` asks 80%. For places where a country knows a deadlock would show first |
| `BORDER_ROUTE_CHECKS` | Optional. Pairs per neighbouring country code, crossing the official boundary in both directions |
| `ACCESS_PROBES` | Class pairs whose carrier separation is checked on real cycle edges in the built tiles |

Coordinates in `ROUTE_CHECKS` and `BORDER_ROUTE_CHECKS` are verification
fixtures, not legal boundaries.

## Enrichment, and whether the Lua may trust raw OSM

A country decides how much of its answer it derives before the graph is built,
and the two already here sit at opposite ends.

The Netherlands reads raw OSM tags in the Lua and treats its authority overlay
as extra evidence: a way with no overlay value is still decided, conservatively,
from what the mapper wrote. Belgium does the opposite. Its Python enrichment
resolves speeds and sidepath obligations, then stamps `amgraph:rules` with its
`RULES_VERSION`, and `countries/be.lua` closes any way whose stamp does not
match. Raw OSM is never enough for a Belgian way, and an enriched way built
under older rules closes rather than being believed.

Stamp the version if the Lua depends on a value the enrichment computed. Without
it, an extract prepared under one version and built under another produces
plausible access from stale arithmetic, and nothing downstream can tell.

## What must hold before it builds

- The Lua and Python modules must name the same carrier for the same class.
  `prepare_country.py` refuses the country at load when they disagree, because
  nothing downstream would notice.
- Two classes may not share a carrier. They would be indistinguishable in the
  graph, so `access.prepare` refuses the country rather than letting the router
  answer for whichever it happened to ask about.
- Five access classes is the ceiling, being the stock Valhalla travel modes that
  read an access bit of their own. See
  [classes and carriers](architecture.md#classes-and-carriers).
- `RULES_VERSION` must be within the 90-day review window, and `valid_until`
  must not have arrived. Both abort the build rather than warning.
- The official boundary must identify the national feature by the properties the
  module declares. An invalid polygon aborts rather than being repaired into
  different territory.

## Verifying it

```sh
make verify                            # rules, Lua, lint, format, unit tests. No network
make country-prepare                   # download and enrich every registered country
make test-audit                        # every observed access-tag combination, per country
uv run python infra/collect_probes.py  # select real cycle edges for runtime checks
make country-graph                     # merge all countries into one graph
uv run python infra/verify_routes.py   # every class, plus the declared border fixtures
```

The new country's gates and every existing country's gates run on the same
build. A failure in any of them blocks the whole release, so adding a country
cannot be finished by weakening a check that another country depends on.
