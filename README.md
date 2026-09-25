# amgraph

[![Graph](https://github.com/RashadAnsari/amgraph/actions/workflows/graph.yml/badge.svg?branch=master)](https://github.com/RashadAnsari/amgraph/actions/workflows/graph.yml?query=branch%3Amaster)
[![Check](https://github.com/RashadAnsari/amgraph/actions/workflows/check.yml/badge.svg?branch=master)](https://github.com/RashadAnsari/amgraph/actions/workflows/check.yml?query=branch%3Amaster)
[![Latest graph](https://img.shields.io/github/v/release/RashadAnsari/amgraph?label=graph&sort=semver&display_name=release)](https://github.com/RashadAnsari/amgraph/releases/latest)

One routing graph for AM-licence vehicles across all supported countries.
The Netherlands is the one supported today. The build, merge, audit and release
are built for several countries on equal terms, and a second is added by the
procedure in [adding a country](docs/adding-country.md). Country-specific
rules, primary sources and retrieval dates are documented per country under
[docs/countries/](docs/README.md#country-rules).

The build enriches each country's OpenStreetMap extract with its own authority
data, audits every input, and merges the results by OSM identity and official
territory. Ways and junctions carry their own country attribution. A supported
border crossing must satisfy every applicable country's rules; territory with
no verified rules stays closed. Conflicting source versions stop the merge.

A class borrows a stock [Valhalla](https://valhalla.github.io/valhalla/) access
bit, its carrier. A class keeps its carrier across a border, so a country added
later puts each of its classes on the carrier of the class it matches:

| Carrier | Netherlands | Valhalla costing |
| --- | --- | --- |
| `moped` | `snorfiets` | `motor_scooter` |
| `motorcycle` | `bromfiets` | `motorcycle` |
| `taxi` | `speed_pedelec` | `taxi` |
| `truck` | `brommobiel` | `truck` |

Identifiers retain their statutory language. A carrier is storage for a
vehicle's access decision; it does not give that vehicle the rights of a taxi,
truck or motorcycle. Consumers must use the matching rules package for vehicle
selection, speeds and powertrain-dependent legal zones. A route is lawful only
once `amgraph_rules.legal_zones.LegalZones.blocks` has passed it against the
release's `boundaries/legal-zones.geojson`: the tiles cannot hold an emission
zone, because a combustion and an electric vehicle of one class share a carrier.
A consumer not written in Python must reproduce that check, not skip it.

## Documentation

- [Documentation index](docs/README.md)
- [Multi-country architecture](docs/architecture.md)
- [The access model](docs/access-model.md)
- [Build, verification and releases](docs/build-and-release.md)
- [Shared country rules](docs/country-rules.md) and [adding a country](docs/adding-country.md)
- Country rules: [Netherlands](docs/countries/nl.md)
- [Contributor instructions](AGENTS.md)

## Licence

The **code** is Copyright Rashad Ansari under the
[MIT License](LICENSE.md): use it, change it and redistribute it, keeping the
copyright notice with it.

The **published graph** is derived from OpenStreetMap, © OpenStreetMap
contributors, so it is offered under the
[Open Database License 1.0](https://opendatacommons.org/licenses/odbl/1-0/),
which asks for attribution and share-alike. Rijkswaterstaat's
Wegkenmerkendatabase and the Kadaster BRK boundaries are public domain.

[NOTICE.md](NOTICE.md) sets out both in full, and why they differ.
