# Shared country rules

[Documentation](README.md) · [Adding a country](adding-country.md) · [Belgium](countries/be.md) · [Netherlands](countries/nl.md)

amgraph builds one routing graph for AM-licence vehicles across all supported
countries. Every country supplies its own statutory vehicle identifiers,
legal rules, official geographic evidence and verification fixtures.

## Evidence standard

Every legal rule must carry a verbatim primary-source quotation, the URL where
it was read, and its retrieval date in `docs/countries/<cc>.md`. Keep the rule
identifier stable so access assertions can name the rule they verify. Record
uncertainty explicitly and retain the conservative decision until the required
evidence is established.

Country rules are reviewed within 90 days of their version's research date.
An explicit legal-regime expiry also blocks builds at its exclusive deadline.
Changes to legal rules require matching Python and Lua `RULES_VERSION` updates.
The manifest records the versions used to build the tiles; consumers validate
them against the installed rules package for every country a route crosses.

## Access and speed

Unknown territory, unmodelled restrictions and ambiguous evidence deny access.
A prohibition removes access at build time; route preferences cannot grant it.
A mandatory-use closure must leave the rider an established lawful alternative.
Check the paired path and roadway decisions together.

When data supports several speed interpretations, use the slower verified
answer. A reported speed combines the country's vehicle limit, infrastructure
limit and readable posted limit. Consumers also apply the country's
powertrain-dependent zones and other declared runtime constraints.

## Coverage and validation

Every build includes all discovered country modules. Each needs a matching
Lua model, source extract, official boundary, successful audit and current
legal evidence. Every shared way and junction must satisfy all applicable
country rules. One country's failed gate blocks the complete release.

The source audit evaluates every observed access-tag combination. Runtime
checks measure reachability for every vehicle class and declared border route,
and prove carrier separation on actual cycle edges. The final ZIP contains
one graph, every country's boundary, combined legal zones and the manifest.

These checks establish consistency with the rules and evidence modelled by
amgraph. They cannot establish that every mapped sign is correct or detect a
new restriction absent from the source data. Country documents record specific
coverage limits. Current signs and authorised directions on the ground govern.
