# Keeping the law current

[Documentation](README.md) · [Shared country rules](country-rules.md) · [Netherlands](countries/nl.md)

How to re-read each country's law, how often, and how to prove afterwards that
everything built on it still holds. A rule that was right when it was written
is not right forever: statutes are amended, municipalities add zones, and a
route is only lawful against the law in force on the day it is ridden.

## The schedule

| When | What | Who notices |
| --- | --- | --- |
| Every Monday 04:00 UTC | The graph is rebuilt from the newest map, sign register and authority data, and every gate runs again | The Graph workflow. Nothing to do unless it is red |
| Every 90 days per country, at the latest | The full legal review below | `tests/test_rules_freshness.py` fails, and the build refuses to prepare the country (`require_current`), so the weekly release stops |
| On an event | The legal review for the rules the event touches | You. See the list below |

**Start the 90-day review by day 75.** At day 91 the weekly release stops, and
a stale graph keeps serving riders until the review is done. The review is
the deadline, not the outage.

**Events that start a review early:**

- A new consolidated version of an act a rule cites, or a published amendment
  to one.
- A date written in a country module arriving: a `MunicipalZone.valid_from` or
  `valid_to`, or a `CountryRules.valid_until`.
- A reform a rule's document says is announced. For the Netherlands: the
  Utrecht brommobiel decision (NL-ACC-06A).
- A rider or a road authority reporting a route that contradicts a sign.
- A new municipal moped or emission zone.

## The review, for any country

Do it rule by rule from `docs/countries/<cc>.md`, never from memory or from
the code. The `legal-review` Claude skill (`.claude/skills/legal-review/`) walks
through these steps, and its `check_statutes.py` does the mechanical part of
steps 1, 2 and 4: which cited acts have a newer version or adopted amendments
waiting for a date, and whether every quote is still word for word in the text.

1. **Find the version in force.** For each act a rule cites, open the
   consolidated text in force today, not the version linked in the document.
   Note its version date.
2. **Compare every quote word for word.** If the version date is newer than the
   one the document links, compare each quoted passage against the new text. A
   changed word is a changed rule.
3. **Read the sign annex again.** Signs are where most access rules live, and an
   annex can change without the articles around it changing.
4. **Look for what is published but not yet in force.** An amendment with a
   future start date is written down now with `valid_from` or `valid_until`, not
   remembered later.
5. **Re-read every municipal source** the country module names, and look for new
   zones in the national index where the country has one.
6. **Re-check every rule marked `UNVERIFIED` or `UNVERIFIABLE`.** Each is a
   conservative branch waiting for a source. If one has appeared, the rule can
   be settled. If not, it stays conservative.
7. **Change the rules, tests first.** Where the law changed, update the quote,
   link and retrieval date in the country document, write or change the test
   that pins the rule, then change `countries/<cc>.lua` and `countries/<cc>.py`
   together.
8. **Date the review even when nothing changed.** Update the retrieval dates,
   set `RULES_VERSION` to `<cc>-<today>.1`, and bump the package version.
9. **Write down what was read.** The commit message lists every act and page
   re-read, its version date, and what changed, or that nothing did.

## Proving it still holds

A review is finished only when these pass on the new rules:

- `make verify`: the Lua rule tests, lint and unit tests.
- `make test-audit`: every access-tag combination in the country, run against the
  current extract.
- The Graph workflow on the pull request: the graph build, the per-class route
  checks and the carrier probes.
- After merging and tagging `rules-v<version>`, in each consumer: move the pin to
  the new tag, fetch the new release, and run its own route corpus.

The release manifest records the rules version every graph was built under,
and a consumer refuses a graph built under rules other than the ones it pins.
So a skipped consumer step shows up as a refused deploy, not as a silent
mismatch.

## The Netherlands

What the last review read, and where to read it next time. Every rule's own
link and date are in [countries/nl.md](countries/nl.md).

**How to see whether a Dutch act changed:** open its undated link below. It
redirects to the version in force, whose date is in the URL and in the page
header ("Geldend van 01-09-2026 t/m heden" for the Wegenverkeerswet on 2026-11-14). If that date is newer
than the one the country document links, compare the quotes (step 2).

| Source | What it carries | Where |
| --- | --- | --- |
| RVV 1990 | Definitions (art. 1), where each class rides (arts. 2a, 2b, 5 to 7, 10), speeds (arts. 20 to 22, 45), motorways (art. 42), sub-signs (art. 66), emission zones (arts. 86c to 86e), the sign annex (bijlage 1) | <https://wetten.overheid.nl/BWBR0004825>, read at version 2026-07-01 |
| Wegenverkeerswet 1994 | Which vehicle is a bromfiets (art. 1), registration (arts. 36, 37), licence (arts. 107, 108). Stb. 2023, 377 redefines the bromfiets from a date not yet set | <https://wetten.overheid.nl/BWBR0006622>, read at version 2026-09-01 |
| Regeling kentekens en kentekenplaten | Plate colours (art. 3) | <https://wetten.overheid.nl/BWBR0009071>, read at version 2026-01-01 |
| Municipal moped zones | Amsterdam, Den Haag, Nijmegen, Utrecht | The four pages linked in NL-ACC-06A, and <https://www.milieuzones.nl/locaties-milieuzones> for new ones |
| Art. 5 lid 8 decisions | Snorfiets on the roadway in Amsterdam and Utrecht | The two Staatscourant and Gemeenteblad links in NL-ACC-04 |

The sources the weekly build downloads (the OSM extract, the NDW sign register,
the RWS WKD release, the PDOK boundaries) are data, not law. They are refreshed
by the build itself, and the gates decide whether the result may ship.

Open items to look at in every Dutch review until they are settled:

- **NL-ACC-06A**: Utrecht's brommobiel decision.
- **NL-ACC-07**: the cyclist one-way exemption for a snorfiets (`UNVERIFIABLE`,
  by design permanent unless a primary source appears).
- **NL-ACC-06**: whether RVV art. 2a lifts a sign caption naming bromfietsen
  (C13, C15) for the brommobiel. Closed until a primary source settles it.
- **Stb. 2023, 377**: the redefinition of the bromfiets, once a royal decree
  sets its date.
