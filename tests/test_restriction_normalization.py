from __future__ import annotations

import sys
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[1] / "infra"
sys.path.insert(0, str(INFRA))

from restrictions import conservative_restriction_tags  # noqa: E402


def test_general_exceptions_cannot_exempt_borrowed_carrier_modes() -> None:
    assert conservative_restriction_tags(
        {
            "type": "restriction",
            "restriction": "no_left_turn",
            "except": "motorcycle;hgv",
        }
    ) == {"type": "restriction", "restriction": "no_left_turn"}


@pytest.mark.parametrize("key", ["restriction:moped", "restriction:mofa"])
def test_vehicle_specific_restrictions_become_general(key: str) -> None:
    assert conservative_restriction_tags({"type": "restriction", key: "no_right_turn"}) == {
        "type": "restriction",
        "restriction": "no_right_turn",
    }


def test_a_conditional_turn_is_forbidden_at_all_times() -> None:
    assert conservative_restriction_tags(
        {
            "type": "restriction",
            "restriction:conditional": "no_straight_on @ (Mo-Fr 07:00-19:00)",
        }
    ) == {"type": "restriction", "restriction": "no_straight_on"}


def test_a_conditional_key_missing_its_condition_is_still_forbidden() -> None:
    assert conservative_restriction_tags(
        {"type": "restriction", "restriction:hgv:conditional": "only_straight_on"}
    ) == {"type": "restriction", "restriction": "only_straight_on"}


def test_a_scoped_none_relaxation_cannot_cancel_the_concrete_restriction() -> None:
    assert conservative_restriction_tags(
        {
            "type": "restriction",
            "restriction:hgv": "only_right_turn",
            "restriction:hgv:conditional": "none @ destination",
        }
    ) == {"type": "restriction", "restriction": "only_right_turn"}


def test_restriction_metadata_is_not_mistaken_for_a_turn_type() -> None:
    assert conservative_restriction_tags(
        {
            "type": "restriction",
            "restriction": "no_u_turn",
            "restriction:type": "NL:motorroad",
        }
    ) == {"type": "restriction", "restriction": "no_u_turn"}


def test_only_u_turn_uses_valhallas_equivalent_only_to_member_semantics() -> None:
    assert conservative_restriction_tags({"type": "restriction", "restriction": "only_u_turn"}) == {
        "type": "restriction",
        "restriction": "only_straight_on",
    }


def test_unknown_or_conflicting_restrictions_stop_the_build() -> None:
    with pytest.raises(ValueError, match="no concrete"):
        conservative_restriction_tags({"type": "restriction"})
    with pytest.raises(ValueError, match="no concrete"):
        conservative_restriction_tags({"type": "restriction", "restriction:moped": "none"})
    with pytest.raises(ValueError, match="unrecognised"):
        conservative_restriction_tags(
            {"type": "restriction", "restriction:moped": "sometimes_left"}
        )
    with pytest.raises(ValueError, match="conflicting"):
        conservative_restriction_tags(
            {
                "type": "restriction",
                "restriction": "no_left_turn",
                "restriction:moped": "only_right_turn",
            }
        )
    with pytest.raises(ValueError, match="conflicting"):
        conservative_restriction_tags(
            {
                "type": "restriction",
                "restriction:conditional": ("no_left_turn @ (Mo-Fr); only_right_turn @ (Sa-Su)"),
            }
        )


def test_non_restriction_relations_are_untouched() -> None:
    tags = {"type": "route", "route": "bicycle", "except": "motorcycle"}
    assert conservative_restriction_tags(tags) == tags
