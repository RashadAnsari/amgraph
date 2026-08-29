"""The app must not go on claiming "checked" against law nobody has re-read.

Every route this service returns is implicitly verified by the API contract.
That claim ages: the
RVV is amended, and nothing in the code notices. `RULES_VERSION` is a string
somebody types, so left alone it will happily assert 2026 law in 2029.

The rules need re-reading on a schedule. This is the part of it that cannot be
forgotten: a test that starts failing when the rules go
stale, so somebody has to open the statute rather than the app quietly
insisting it is current.

Failing here does **not** mean the code is broken. It means the law needs
re-reading. The fix is to check `docs/rules.md` against the current
consolidated RVV, correct anything that changed, and then bump the date.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

import pytest

from amgraph_rules.countries.nl import RULES_VERSION

#: Quarterly. Long enough that
#: this is not noise, short enough that a change to the RVV cannot sit
#: unnoticed for a riding season.
MAX_AGE_DAYS = 90


def _verified_on() -> date:
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", RULES_VERSION)
    assert match, (
        f"RULES_VERSION is {RULES_VERSION!r} and carries no date. It is the only "
        "record of when the law behind a route was last read; keep the "
        "country-YYYY-MM-DD shape."
    )
    return date(*(int(part) for part in match.groups()))


def test_the_rules_carry_the_date_they_were_read() -> None:
    assert _verified_on() <= datetime.now(UTC).date(), (
        "RULES_VERSION is dated in the future, so its age cannot be judged."
    )


def test_the_law_has_been_read_recently_enough_to_claim_it_is_checked() -> None:
    age = (datetime.now(UTC).date() - _verified_on()).days
    if age > MAX_AGE_DAYS:
        pytest.fail(
            f"The Dutch rules were last verified {age} days ago "
            f"({RULES_VERSION}), over the {MAX_AGE_DAYS}-day limit.\n\n"
            "This is not a code failure. Every route we return relies on "
            "these rules, and that review is now older than we "
            "are willing to stand behind.\n\n"
            "Re-read docs/rules.md against the current consolidated "
            "RVV, correct anything that has changed, then bump RULES_VERSION "
            "to today."
        )
