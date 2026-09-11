"""Nothing here may go on claiming "checked" against law nobody has re-read.

Every graph published from this repository carries an implicit claim that each
country's rules were read from its statute. That claim ages: a traffic code is
amended and nothing in the code notices. `RULES_VERSION` is a string somebody
types, so left alone it will happily assert 2026 law in 2029.

The rules need re-reading on a schedule. This is the part of it that cannot be
forgotten: a test that starts failing when the rules go stale, so somebody has
to open the statute rather than the repository quietly insisting it is current.

Failing here does **not** mean the code is broken. It means that country's law
needs re-reading. The fix is to check `docs/countries/<cc>.md` against the
current consolidated statute, correct anything that changed, then bump the date.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

import pytest

from amgraph_rules.countries import modelled_countries

#: Quarterly. Long enough that
#: this is not noise, short enough that an amendment to any country's traffic
#: code cannot sit unnoticed for a riding season.
MAX_AGE_DAYS = 90


def _verified_on(rules_version: str) -> date:
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", rules_version)
    assert match, (
        f"RULES_VERSION is {rules_version!r} and carries no date. It is the only "
        "record of when the law behind a route was last read; keep the "
        "country-YYYY-MM-DD shape."
    )
    return date(*(int(part) for part in match.groups()))


@pytest.mark.parametrize("country", modelled_countries(), ids=lambda c: c.code)
def test_the_rules_carry_the_date_they_were_read(country) -> None:
    assert _verified_on(country.rules_version) <= datetime.now(UTC).date(), (
        "RULES_VERSION is dated in the future, so its age cannot be judged."
    )


@pytest.mark.parametrize("country", modelled_countries(), ids=lambda c: c.code)
def test_the_law_has_been_read_recently_enough_to_claim_it_is_checked(country) -> None:
    today = datetime.now(UTC).date()
    assert country.valid_until is None or today < country.valid_until
    age = (today - _verified_on(country.rules_version)).days
    if age > MAX_AGE_DAYS:
        pytest.fail(
            f"The {country.code} rules were last verified {age} days ago "
            f"({country.rules_version}), over the {MAX_AGE_DAYS}-day limit.\n\n"
            "This is not a code failure. Every route we return relies on "
            "these rules, and that review is now older than we "
            "are willing to stand behind.\n\n"
            f"Re-read docs/countries/{country.code.lower()}.md against the current "
            "consolidated statute, correct anything that has changed, then bump "
            "RULES_VERSION to today."
        )
