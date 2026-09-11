# amgraph documentation

amgraph builds one routing graph for AM-licence vehicles across every supported
country. A rider must never be routed onto infrastructure their vehicle class is
legally barred from, and every document here serves that.

Nothing here is legal advice. Current signs and authorised directions on the
ground govern.

## How the system works

- [Multi-country architecture](architecture.md): the country registry, the Lua
  adapter, classes and carriers, and the invariants the merged graph holds.
- [The access model](access-model.md): how one way or junction is decided, what
  each tag value means, and why a node is not a short way.
- [Build, verification and releases](build-and-release.md): the gates, the two
  workflows, the release ZIP and the installable rules package.

## Country rules

- [Shared country rules](country-rules.md): what every country must supply, the
  evidence standard, and the validation each one has to pass.
- [Adding a country](adding-country.md): the procedure, in order.

Each supported country states its own law, with a verbatim quotation, a link and
a retrieval date per rule:

| Country | Rules | Classes |
| --- | --- | --- |
| Belgium | [countries/be.md](countries/be.md) | `bromfiets_klasse_a`, `bromfiets_klasse_b`, `speed_pedelec`, `lichte_vierwieler` |
| Netherlands | [countries/nl.md](countries/nl.md) | `snorfiets`, `bromfiets`, `speed_pedelec`, `brommobiel` |

No country's classes or law stand in for another country's. A rule identifier is
scoped to its country (`NL-ACC-02`, `BE-ACC-02`), and access assertions name the
identifier they pin.

## Working on this

[AGENTS.md](../AGENTS.md) is how to work in this repository.
