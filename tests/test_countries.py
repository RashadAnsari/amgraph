"""An unsupported country must never inherit a fallback legal ruleset."""

from __future__ import annotations

import pytest

from amgraph_rules.countries import (
    NETHERLANDS,
    UnsupportedCountryError,
    modelled_countries,
    rules_for,
)


def test_the_netherlands_is_modelled_and_cited() -> None:
    rules = rules_for("NL")

    assert rules is NETHERLANDS
    assert "RVV 1990" in rules.source


def test_lookup_is_case_insensitive() -> None:
    assert rules_for("nl") is NETHERLANDS


@pytest.mark.parametrize("code", ["BE", "DE", "XX", ""])
def test_an_unsupported_country_has_no_rules(code: str) -> None:
    with pytest.raises(UnsupportedCountryError):
        rules_for(code)


def test_only_researched_countries_are_listed() -> None:
    assert [country.code for country in modelled_countries()] == ["NL"]
