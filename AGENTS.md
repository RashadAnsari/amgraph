# Working on amgraph

Read this before touching anything. This file is how to work here.
[docs/rules.md](docs/rules.md) is what the rules are: every rule with its
verbatim quote, its link and the date it was read.

amgraph builds a routing graph for Dutch AM-licence vehicles: mopeds, speed
pedelecs and microcars. Its entire reason to exist is that **a rider must never
be routed onto infrastructure their vehicle class is legally barred from.**
Every other requirement is subordinate to that one.

That single fact decides almost everything below.

---

## The one rule

**Never state a legal rule without a primary source and a date.**

Not "generally", not "typically", not from memory, not from a blog post, not
from a plausible-looking table. If you cannot quote the statute and link where
you read it, the rule does not exist and the graph must take the conservative
branch.

Guessing a country's moped law is a day's work and produces a document
indistinguishable from a researched one. The result is a rider fined in a
country whose rules we invented. There is no recovering from that, and no test
catches it.

Every rule in `docs/rules.md` carries a verbatim quote, a link and a retrieval
date. Match that standard or do not write the rule.

## Non-negotiables

1. **Unknown resolves to forbidden.** Every unmodelled rule, ambiguous tag and
   unverified country takes the conservative branch. Longer routes are an
   acceptable cost. Illegal ones are not.

   **But "forbidden" is a claim, and two of them can contradict each other.**
   Closing a carriageway because the rider is obliged onto the path beside it,
   *and* closing that path because it carries no sign, is not caution twice
   over: it asserts that the rider must be somewhere they may not be, and it is
   always wrong, because RVV art. 5 lid 2 and art. 6 lid 2 say the rijbaan is
   mandatory precisely when no path is established. That pair alone made 96% of
   ordinary snorfiets city pairs unroutable. Before adding a closure, ask what
   it leaves open. A rule that can leave a rider nowhere lawful is a bug however
   conservative each half looks.

2. **Where the law cannot be read from the data, choose the slower answer.**
   Telling a rider to do 30 where 40 was allowed wastes nothing that matters.
3. **A graph that fails a gate is never published.** A stale graph that obeys
   the law beats a fresh one that does not.

## The four vehicles

Learn them before writing access code. What each may ride is in
`docs/rules.md`: `snorfiets` (blue plate, 25 km/h) follows bicycle rules,
`bromfiets` and `speed_pedelec` (yellow, 45) may use a fiets/bromfietspad and
nothing else in that family, `brommobiel` (yellow, 45) uses the roadway only.

**The identifiers stay in the country's own language.** `snorfiets` in code.
They are statutory terms and the rules are written against them, so a translated
identifier would put guesswork between the code and the law. Anything rendering
a label for a rider translates it there.

**Adding a country is a change here and nowhere else.** A country states its own
classes — how many, what OSM calls them, which carrier each borrows, what each
may do — in `valhalla/lua/countries/<cc>.lua` and
`rules/src/amgraph_rules/countries/<cc>.py`, and nowhere else.

**Five access classes is the ceiling**, being the stock Valhalla travel modes
that read an access bit of their own. Three would not survive the first country
anybody would add. Belgium clears three on its first article: art. 9.1.2 of the
Code van de openbare weg gives a klasse A moped, a klasse B moped, a speed
pedelec and a light quadricycle four different sets of road rights, because the
pedelec and the klasse B differ on a cycle path where the limit is 50 km/h or
less.

## The two files that must agree

`valhalla/lua/countries/<cc>.lua` names the carrier each access class borrows,
and `access.lua` writes it into that stock Valhalla travel mode at graph build
time. `rules/src/amgraph_rules/countries/<cc>.py` names the same carrier per
class, and whatever serves the graph maps a carrier to the costing model that
reads its bit. For the Netherlands: snorfiets on moped, bromfiets and speed
pedelec on motorcycle, brommobiel on truck.

Change one without the other and routes stay plausible while becoming illegal.
It is the only failure in this codebase that does not announce itself, and it is
why both halves live in one repository.

**They can still drift across a version.** `rules/` is installable on its own
and consumers pin it by tag, so a deployment can be running older rules than the
graph it serves was built under. That is what `RULES_VERSION` and
`infra/manifest.py` are for: every release records the version its tiles were
built under, so a mismatch is detectable rather than silent. **Bump
`RULES_VERSION` on any change to the rules**, and tag `rules-v<version>` when
consumers need to see it.

## How this repository is laid out

```
rules/            amgraph-rules. Installable on its own, pinned by tag
  src/amgraph_rules/countries/   a country's classes, carriers, limits, by-laws
valhalla/
  build.sh        upstream Valhalla, pinned by digest, with our Lua transform
  lua/            the access rules. The most important code in the project
infra/            extracts, the authority overlay, the manifest. work/ is
                  gitignored and large
tests/            the gates
docs/rules.md     the law, cited
```

## How to work

- **Small, reviewable steps.** One change per commit, with the reasoning in the
  message. The commit message is the review: it has to explain why to someone
  who will have forgotten.
- **Research before design.** Read the code, then the official docs, then the
  source. A confident guess is still a guess. Look up the current version of any
  dependency rather than recalling one.
- **Tests alongside code**, and for legal rules, tests **first**. Every access
  assertion names the rule it pins.
- **Measure before believing.** The two largest defects of 2026-08-15 were
  invisible to reading the code and obvious the moment something was counted. If
  a claim about the network can be turned into a number, turn it into a number.
- **Match the surrounding style.** Comments here explain *why*, never *what*. If
  a comment restates the code, delete it. If a line took an afternoon to get
  right, say what the afternoon taught you.
- **Do not add abstraction for a consumer that does not exist.** A spec line is
  a hypothesis.
- **Documentation describes the system as it is**, never how it got that way. A
  lesson worth keeping is written as the constraint it imposes, not as the story
  of the day it was learned.

## Before you call anything done

```sh
make verify      # the Lua rules, lint, format and the unit tests. No network.
make test-audit  # every access-tag combination in the country, against the extract
```

`test-audit` is the strongest gate here: it reads the extract rather than
sampling routes, so a pass means no way in the country can be offered to a class
the law bars from it.

**It cannot see an outage.** A legality gate treats "no lawful path" as a pass,
so a graph that has stopped routing entirely clears every check above. Before
tagging a rules change that could plausibly reduce what is reachable, route
against the built graph and count how many answers come back, not only whether
the illegal ones are refused.

Never finish on failing lint or unformatted code.

## Git

- **The main branch is `master`.** Not `main`.
- Every push to `master` publishes a release, so a commit here is a graph.
- Commit messages explain why, in prose, in the same voice as the code comments.

## Language

Comments and documentation are in English. Vehicle identifiers stay Dutch, for
the reason above.
