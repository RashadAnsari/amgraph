---
name: legal-review
description: Run the periodic legal review of a country's rules in amgraph, re-reading the law in force against every rule, quote and date in docs/countries/<cc>.md. Use when asked to do or start a legal review, re-check or reconfirm the law, when tests/test_rules_freshness.py fails or the 90-day window is near (day 75 or later), when a date in a country module arrives, or when an amendment, a new municipal zone or a rider's report suggests a rule may be out of date.
---

# Legal review

The procedure is [docs/legal-review.md](../../../docs/legal-review.md). Read it
first, then [AGENTS.md](../../../AGENTS.md) "The one rule". This skill is how to
carry the procedure out without skipping a step.

**The standard does not bend for a review.** Every quote is copied from the
primary text you downloaded today, never from memory, a search summary or a
fetch tool that paraphrases. If a source cannot be read, say so and leave the
rule on its conservative branch. A review that finds nothing is a valid result;
a review that assumes nothing changed is not a review.

## 1. Set up

- Ask which country if it is not clear. Default: every country in
  `rules/src/amgraph_rules/countries/__init__.py` `_MODELLED`.
- Work on a branch, never on `master`: every push to `master` publishes a graph.
- Note today's date. It becomes the new `RULES_VERSION` date only if the whole
  review below is done.

## 2. The mechanical check

```sh
uv run python .claude/skills/legal-review/check_statutes.py <cc>
```

It reads every wetten.overheid.nl act and official publication the country
document links, and prints:

| Line | Meaning | What to do |
| --- | --- | --- |
| `same` | The act's version in force is the one the document cites | Nothing for the act; the quotes are still checked below |
| `CHANGED` | A newer consolidated version is in force | Step 3 |
| `PENDING` | The act carries amendments adopted without a commencement date | Step 4 |
| `NOT FOUND` | A quote is in no current text the document links | Either the law changed or the quote comes from a source the script does not read; step 5 decides which |

It is the floor, not the review. A quote can survive inside an article whose
meaning changed around it, and pages that are not statutes (Rijksoverheid,
RDW, municipalities) are not checked by it at all.

## 3. A changed act

Download both versions as text and diff them (`curl --http1.1` reaches
wetten.overheid.nl from the session container). For every changed passage, ask
whether any rule in the country document cites that article, the sign annex, or
a definition it depends on. Record the result either way: a change to an
article no rule cites is still worth one line in the commit message.

## 4. A pending amendment

On the act's page, find the articles marked "Wijziging(en) zonder datum
inwerkingtreding aanwezig". For each that a rule cites, open its
`/informatie#tab-wijzigingenoverzicht`, find the publication (`Stb. <year>,
<number>`), download it from zoek.officielebekendmakingen.nl and read what it
does to that article.

If it touches a rule, add it to the country document under that rule as
"Adopted, not yet in force", with the new text quoted, its link and the date
read. If a decree has already fixed its date, set `CountryRules.valid_until`
to it so the build stops on that day until the class is re-researched.

## 5. Every other source

Re-open every non-statute link in the country document and its country module
(government pages, the vehicle registry, every municipal page, the national
zone index) and compare what the rule quotes against what the page says today.
Look for new municipal zones in the national index.

## 6. Open items

Re-check every rule marked `UNVERIFIED` or `UNVERIFIABLE`, and every item in
the "Open items" list of docs/legal-review.md. If a primary source now settles
one, it can be settled; if not, it stays conservative.

## 7. Change what changed

Tests first. Add or change the case in `valhalla/lua/spec/access_spec.lua` (and
the audit checks in `tests/test_access_rules.py` where a rule is about a tag
pattern) that pins the new law, watch it fail, then change
`valhalla/lua/countries/<cc>.lua` and `rules/src/amgraph_rules/countries/<cc>.py`
together. Update the quote, link and retrieval date in the country document.

When a change could make a route possible that was not before, stop and apply
AGENTS.md non-negotiable 1: unknown resolves to forbidden. Opening a road needs
a source; closing one only needs a doubt.

## 8. Date it and prove it

- `RULES_VERSION = "<cc>-<today>.1"`, the version line at the top of the country
  document, and the `version` in `rules/pyproject.toml` (major if a field or a
  class changed shape, minor if only rules changed). Then `uv lock`.
- Retrieval dates on every rule that was re-read.
- `make verify` must pass. Run `make test-audit` if the extract and authority
  data can be fetched; otherwise say it was not run.
- Commit with the list of everything read, the version of each, and what
  changed or that nothing did. Push the branch and open a pull request only when
  the user asks; its Graph workflow builds and route-checks the graph.

Never merge, never tag `rules-v<version>`. Both are the user's.

## 9. Report

Finish with a short table for the user: each source, the version or date read,
and the outcome (unchanged, changed and applied, pending and recorded, could not
be read). Then the remaining steps that are theirs: merge, tag, and in each
consumer move the pin and run its route corpus (in 45weg, `make
backend-test-legal` and `make backend-test-sweep`).
