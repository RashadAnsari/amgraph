"""Countries whose routing law has been verified from primary sources.

One module per country, and this registry. A country appears here only once its
law has been read from primary sources and cited to the standard in
``docs/rules.md``; there is deliberately no environment variable that can add
one, because an unverified country is indistinguishable from a verified one to
everything downstream.

Being in this registry is necessary but not sufficient to route somewhere. A
deployment also needs the country's official boundary configured and a graph
built from an extract that covers it — see ``supported_area`` — and `/v1/config`
advertises the countries that have both. Splitting it that way is what stops
a half-finished deployment telling riders it covers a country it has no map for.
"""

from __future__ import annotations

from amgraph_rules.countries.nl import NETHERLANDS
from amgraph_rules.rules import (
    BoundaryDocument,
    ClassSpeeds,
    CountryRules,
    MunicipalZone,
    SearchBounds,
    UnknownVehicleClassError,
    VehicleClass,
)

__all__ = [
    "BoundaryDocument",
    "ClassSpeeds",
    "CountryRules",
    "MunicipalZone",
    "SearchBounds",
    "UnknownVehicleClassError",
    "UnsupportedCountryError",
    "VehicleClass",
    "modelled_countries",
    "rules_for",
]


class UnsupportedCountryError(ValueError):
    """Raised instead of substituting rules from another country."""


_MODELLED: dict[str, CountryRules] = {NETHERLANDS.code: NETHERLANDS}


def rules_for(country_code: str) -> CountryRules:
    """Return verified rules, never a conservative or neighbouring fallback."""
    try:
        return _MODELLED[country_code.upper()]
    except (AttributeError, KeyError) as exc:
        raise UnsupportedCountryError(f"country is not supported: {country_code!r}") from exc


def modelled_countries() -> list[CountryRules]:
    return [_MODELLED[code] for code in sorted(_MODELLED)]
