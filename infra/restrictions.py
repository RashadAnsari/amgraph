"""Make OSM turn restrictions safe for amgraph's borrowed carrier modes."""

from __future__ import annotations

import re
from collections.abc import Mapping

RESTRICTION_TYPES = frozenset(
    {
        "no_left_turn",
        "no_right_turn",
        "no_straight_on",
        "no_u_turn",
        "only_right_turn",
        "only_left_turn",
        "only_straight_on",
        "no_entry",
        "no_exit",
        "no_turn",
    }
)

# Valhalla 3.8.3 has no `only_u_turn` enum, but all three supported `only_*`
# values are implemented by allowing the relation's concrete `to` member and
# excluding every other turn. Preserving the members and using any supported
# only-type therefore has the same routing effect.
EQUIVALENT_TYPES = {"only_u_turn": "only_straight_on"}


def conservative_restriction_tags(source: Mapping[str, str]) -> dict[str, str]:
    """Return tags whose restriction binds every borrowed carrier mode.

    Valhalla 3.8.3 does not parse `restriction:moped` or `restriction:mofa`,
    and its `except=motorcycle`/`except=hgv` exemptions reach the stock bits
    that amgraph borrows for bromfiets and brommobiel. Keeping the relation as-is
    can therefore remove a restriction from the wrong legal class.

    A static graph also cannot safely evaluate a conditional turn. Every
    concrete restriction on a restriction relation is normalised to one
    unconditional general restriction and every exception is removed. This can
    forbid a legal turn. It cannot permit an illegal one.
    """
    tags = dict(source)
    if tags.get("type") != "restriction":
        return tags

    codes: set[str] = set()
    restriction_keys: list[str] = []
    for key, value in tags.items():
        if key == "restriction" or key.startswith("restriction:"):
            restriction_keys.append(key)
            if key in {"restriction:probable", "restriction:type"}:
                continue
            if key.endswith(":conditional"):
                conditional_codes = re.findall(r"(?:^|;)\s*([a-z_]+)\s*@", value)
                if conditional_codes:
                    codes.update(conditional_codes)
                elif value.strip():
                    # A relation without an `@ condition` is malformed but its
                    # stated manoeuvre can safely be enforced all the time.
                    codes.add(value.strip())
            else:
                code = value.strip()
                if code:
                    codes.add(code)

    # `none` is how OSM expresses a scoped or conditional relaxation, for
    # example `restriction:hgv:conditional=none @ destination` beside an
    # unconditional `restriction:hgv=only_right_turn`. Dropping that
    # relaxation makes the remaining concrete restriction stricter. A
    # relation containing only `none` still fails the no-concrete-rule check.
    codes.discard("none")
    codes = {EQUIVALENT_TYPES.get(code, code) for code in codes}
    unknown = codes - RESTRICTION_TYPES
    if unknown:
        raise ValueError(f"unrecognised turn restriction {sorted(unknown)}")
    if len(codes) > 1:
        raise ValueError(f"conflicting turn restrictions {sorted(codes)}")
    if not codes:
        raise ValueError("restriction relation has no concrete turn restriction")

    for key in restriction_keys:
        tags.pop(key, None)
    tags.pop("except", None)
    if codes:
        tags["restriction"] = codes.pop()
    return tags
