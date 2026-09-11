# Netherlands rules

Primary sources last reviewed **2026-08-15**. The country modules declare `nl-2026-08-16.1`.

[Documentation](../README.md) · [Shared country rules](../country-rules.md) · [Belgium](be.md)

## Vehicle classes

| Profile | Plate | Max | Cycle infrastructure |
| --- | --- | --- | --- |
| `snorfiets` | blue | 25 | Follows **bicycle** rules. Must use G11 and G12a. May use G13 if electric |
| `bromfiets` | yellow | 45 | Must use **G12a only**. G11 and G13 are closed |
| `speed_pedelec` | yellow | 45 | Identical to bromfiets for routing |
| `brommobiel` | yellow | 45 | **None.** Roadway only |

The enum values stay Dutch; the labels riders see are English. `snorfiets` in
code, "Light moped" on screen. The identifiers are statutory terms and the
rules are written against them, so a translated identifier would put guesswork
between the code and the law.

**NL-DEF-01 — snorfiets** `VERIFIED`
> "bromfiets die blijkens de gegevens in het kentekenregister is geconstrueerd
> voor een maximumsnelheid die niet meer bedraagt dan 25 km per uur, met
> uitzondering van de speed-pedelec"

The clause "met uitzondering van de speed-pedelec" is load-bearing: a speed
pedelec is never a snorfiets, so it never inherits bicycle rules.

**NL-DEF-02 — brommobiel** `VERIFIED`
> "bromfiets op meer dan twee wielen, die is voorzien van een carrosserie"

**NL-DEF-03 — speed pedelec is a bromfiets** `VERIFIED` — EU category L1e-B,
yellow plate. Source: RDW,
<https://www.rdw.nl/kopen-of-verkopen/elektrische-fiets-of-speed-pedelec>.

**NL-DEF-04 — autosnelweg / autoweg** `VERIFIED` — defined **by their sign**:
"weg, aangeduid door bord G1 / G3 van bijlage I". Not by road class.

**NL-DEF-05 — motorvoertuig excludes bromfietsen** `VERIFIED`
> "alle gemotoriseerde voertuigen behalve bromfietsen, fietsen met
> trapondersteuning en gehandicaptenvoertuigen"

Consequence: rules written for *motorvoertuigen*, including the art. 20 urban
50 limit and the art. 42 motorway rule, do **not** apply to any of our four
classes. All four are bromfietsen.

All RVV citations: <https://wetten.overheid.nl/BWBR0004825/2026-07-01>,
retrieved 2026-08-14 and 2026-08-15.

## Access rules

### NL-ACC-01 — No autosnelweg, no autoweg, for any class `VERIFIED`

> lid 1: "Het gebruik van de autosnelweg is slechts toegestaan voor bestuurders
> van een motorvoertuig waarmee met een snelheid van ten minste 60 km per uur
> mag en kan worden gereden."
> lid 2: "Het gebruik van de autoweg is slechts toegestaan voor bestuurders van
> een motorvoertuig waarmee met een snelheid van ten minste 50 km per uur mag
> en kan worden gereden."

RVV 1990 **art. 42**. Source:
<https://wetten.overheid.nl/BWBR0004825/2026-07-01>, retrieved 2026-08-15.

The article works as a **permission, not a prohibition**, and reading it that
way is what makes it airtight for us. Use of an autosnelweg or autoweg is
allowed only to a *motorvoertuig*, and NL-DEF-05 puts every bromfiets outside
that word. All four profiles are bromfietsen, so none of them is inside the
permission at all — and separately, none can do 60 or even 50 km/h, so none
would qualify even if it were.

Art. 43 is **not** the authority here, and it is the article a reader expects:
it covers U-turns, reversing, stopping and the hard shoulder, and the
often-quoted sentence barring bromfietsen from autosnelwegen by name is not in
the consolidated text in force.

**Router:** hard exclusion. `highway=motorway`, `motorway_link` and any
`motorroad=yes` are forbidden for every profile in both directions, with no
cost-based escape.

### NL-ACC-02 — Bromfiets and speed pedelec `VERIFIED`

> lid 1: "Bromfietsers gebruiken het fiets/bromfietspad."
> lid 2: "Zij gebruiken de rijbaan indien een fiets/bromfietspad ontbreekt."
> lid 3: "Bestuurders van bromfietsen op meer dan twee wielen … breder zijn dan
> 0,75 meter, gebruiken de rijbaan."

RVV art. 6. Two consequences, and the second is what general-purpose routers
get wrong:

1. A bromfiets may use a **fiets/bromfietspad (G12a)** and nothing else in the
   cycle-path family. No provision admits it to a G11 or a G13.
2. Lid 1 is an **obligation, not a permission**. Where a fiets/bromfietspad runs
   alongside, riding on the roadway is illegal. Stock Valhalla ignores
   `use_sidepath` entirely and routes riders along the roadway illegally.

**Lid 2 is the other half, and omitting it makes the country unroutable.** Where
no fiets/bromfietspad is established the rijbaan is *mandatory*, so a
mandatory-use closure is only valid if a path the class may actually use runs
alongside. See [Authority overlay](#authority-overlay).

Residual error: a rider on the carriageway where a sidepath was in fact
compulsory, which is an art. 6 lid 1 offence. Accepted, because its worst case
is a fine for staying on the road while the safety-critical half is proven.

### NL-ACC-03 — Snorfiets follows bicycle rules `VERIFIED`

> "De regels van dit besluit betreffende fietsen en fietsers zijn, in plaats van
> de regels betreffende bromfietsen en bromfietsers, mede van toepassing op
> snorfietsen en snorfietsers, tenzij anders is bepaald."

RVV art. 2b. This is the hinge for the whole profile: art. 6 does **not** apply
to a snorfiets, art. 5 does.

> lid 1: "Fietsers gebruiken het verplichte fietspad of het fiets/bromfietspad."
> lid 2: "Zij gebruiken de rijbaan indien een verplicht fietspad of een
> fiets/bromfietspad ontbreekt."
> lid 3: "Zij mogen het onverplichte fietspad gebruiken. Bestuurders van
> snorfietsen uitgerust met een verbrandingsmotor mogen het onverplichte
> fietspad slechts gebruiken met uitgeschakelde motor."

**A fietspad is defined by its sign.** Art. 1 defines `autosnelweg` and
`autoweg` by sign but gives **no definition at all** for `fietspad`, `verplicht
fietspad`, `onverplicht fietspad` or `fiets/bromfietspad`. Those four terms
appear only as the captions of G11, G12a and G13 in bijlage I hoofdstuk G. So
an unsigned path is legally none of them, and both lid-2 provisions send the
rider to the rijbaan. Verified 2026-08-15.

**G13 is closed to both powertrains.** Art. 5 lid 3 admits a snorfiets, but a
combustion one only with the engine off, and the graph is built before the
rider picks a powertrain. Stricter than the statute for an electric snorfiets,
but it cannot produce an illegal route. Opening it only for electric needs a
distinct graph access class, not an API switch.

### NL-ACC-04 — Snorfiets municipal override to the roadway `VERIFIED`

> lid 8: "Bestuurders van snorfietsen gebruiken de rijbaan indien dit bij
> verkeersbesluit … is bepaald en bij het verkeersteken dat het verplichte
> fietspad aangeeft een onderbord dit aanduidt."

RVV art. 5. Lid 8 requires **both** a verkeersbesluit **and** an onderbord on
the G11. Amsterdam and Utrecht have both taken the measure:

- Amsterdam final decision:
  <https://zoek.officielebekendmakingen.nl/stcrt-2018-71559.html>
- Utrecht final decision, effective 2021-09-30:
  <https://zoek.officielebekendmakingen.nl/gmb-2021-212045.html>

**Router:** the rule decides *which edge* a rider belongs on, so it is applied
on edges, and in **both** directions the measure works. Inside the official BRK
boundary of a municipality that has taken it, `official_access.py`

1. takes the snorfiets off every verplicht fietspad with
   `amgraph:snorfiets=roadway_only`, and
2. writes `amgraph:snorfiets=on_roadway` on every carriageway inside the
   boundary, so no `mofa=use_sidepath` can take the class off the road the
   municipality put it on.

Doing only the first is a deadlock: Utrecht's OSM data carries a pre-decision
`mofa=use_sidepath` on Amsterdamsestraatweg, Croeselaan and Vleutenseweg while
the paths beside them correctly say `mofa=no`. Honouring both traps the
snorfiets on a 1.5 km island in the city centre.

**Limit of the measure:** lid 8 reaches "het verkeersteken dat het verplichte
fietspad aangeeft", which is the **G11 alone**. A fiets/bromfietspad is outside
its scope, so a snorfiets on an Amsterdam G12a is lawful.

The rule decides which road a rider belongs on, not whether the trip may
happen, so it must never be implemented as a refusal of routes touching either
municipality.

### NL-ACC-05 — Brommobiel uses the roadway `VERIFIED`

Follows from NL-DEF-02 plus art. 6 lid 3: a brommobiel is a bromfiets on more
than two wheels with a body, hence wider than 0.75 m, hence "gebruiken de
rijbaan". It may use **no cycle infrastructure of any kind**, and combined with
NL-ACC-01 neither autosnelweg nor autoweg.

The overlay never reaches it: WKD models snorfiets and bromfiets, and a
bromfiets closure caused by a compulsory sidepath does not bind a class that
may not use that sidepath.

### NL-ACC-06 — C-series and direction signs `VERIFIED`

Art. 2a makes motor-vehicle signs apply to a brommobiel; art. 2b makes bicycle
signs apply to a snorfiets.

| Sign | Statutory description | Closed |
| --- | --- | --- |
| C1 | "Gesloten in beide richtingen voor voertuigen, ruiters en geleiders van rij- of trekdieren of vee" | all four |
| C2 | "Eenrichtingsweg, in deze richting gesloten voor voertuigen…" | all four, indicated direction |
| C3/C4 | "Eenrichtingsweg" | reverse direction |
| C6 | "Gesloten voor motorvoertuigen op meer dan twee wielen" | brommobiel (art. 2a) |
| C9 | "Gesloten voor ruiters, vee, wagens, landbouw- en bosbouwtrekkers, motorrijtuigen met beperkte snelheid, mobiele machines, brommobielen, fietsen, snorfietsen, bromfietsen en gehandicaptenvoertuigen" | all four |
| C10 | "Gesloten voor motorvoertuigen met aanhangwagen" | brommobiel, trailer status unknown |
| C12 | "Gesloten voor alle motorvoertuigen" | brommobiel (art. 2a) |
| C13 | "Gesloten voor bromfietsen, snorfietsen en gehandicaptenvoertuigen, met in werking zijnde motor" | snorfiets, bromfiets, speed pedelec |
| C14 | "Gesloten voor fietsen en voor gehandicaptenvoertuigen zonder motor" | snorfiets (art. 2b) |
| C15 | "Gesloten voor fietsen, bromfietsen en gehandicaptenvoertuigen" | snorfiets, bromfiets, speed pedelec |
| C17–C21 | Length / width / height / axle load / mass limits | all four, while actual dimensions are unknown |
| C22 | "Gesloten voor voertuigen met bepaalde gevaarlijke stoffen" | all four, while cargo is unknown |

**Router:** an unscoped prohibition closes both directions when its physical
direction cannot be recovered. `traffic_sign:forward` and `:backward` close only
the named direction. C3/C4 without either a scope or an OSM `oneway` value close
both rather than guessing which way the road runs.

The request carries no trailer, cargo, width, height, length or axle load, so
C10 closes the brommobiel and C17–C22 close every profile. Stricter than
necessary when a particular vehicle fits; assuming it fits can issue a route
barred by the value on the sign.

### NL-ACC-07 — A cyclist one-way exception does not reach a snorfiets `UNVERIFIABLE`

Art. 2b extends "de regels van dit besluit" — the rules of the decree — while an
"uitgezonderd fietsers" onderbord is a sign placed under a municipal
verkeersbesluit. Nothing in the RVV says the word *fietsers* on such a plate
carries the extension, and Dutch traffic-law commentary is openly divided with
no primary source settling it.

Marked UNVERIFIABLE rather than UNVERIFIED, which is deliberate: nobody can
verify it from the sources that exist, so it is permanent. `access.lua`
therefore does not pass `oneway:bicycle` in the snorfiets direction keys, only
`oneway:vehicle` and `oneway:mofa`. Getting this wrong the other way sends a
rider the wrong way down a one-way street; this way costs them a longer ride.

### NL-ACC-08 — Motor roads, footpaths, bridleways by sign `VERIFIED`

G1 and G3 mark the autosnelweg and autoweg, which art. 42 permits only to a
motorvoertuig. G7 and G9 identify infrastructure that
arts. 5, 6 and 10 do not permit these classes to use. Reading the sign prevents
a contradictory generic highway tag from opening it.

### NL-ACC-09 — Mandatory movements and U-turn prohibition `VERIFIED`

D1, D2, D4–D7 and F7 mandate a movement or prohibit a U-turn. A stock edge
cannot recover the pictured movement from the sign code, so if the
corresponding OSM turn restriction is absent, accepting the edge can issue a
forbidden manoeuvre. These close the **way** and, per [the access model](../access-model.md#nodes-are-not-short-ways), never a node.

### NL-ACC-06A — Municipal brom- and snorfiets zones `VERIFIED`

Four municipalities, and each by-law is narrower than what the router does. The
request states a powertrain but not a date of first registration or an engine
cycle, so for a combustion two-wheeler the only claim the API can prove is
"outside the affected municipality". Each is therefore closed as a whole, which
can only refuse a lawful trip and never permit an unlawful one. All retrieved
2026-08-15.

| Municipality | The by-law | What we do |
| --- | --- | --- |
| Amsterdam | A current brom- and snorfiets milieuzone | Whole municipality closed to combustion |
| Den Haag | DET before 2011-01-01, **two-stroke only**: "Heeft u een 4-takt brommer of 4-takt snorfiets met een DET van vóór 1 januari 2011? Dan mag u in de milieuzone rijden." Old *electric* mopeds and brommobielen admitted | Whole municipality closed to combustion, four-stroke included |
| Nijmegen | Build year 2010 or older, in **three areas** — Nijmegen centrum, Hof van Holland, Heijendaal. 2028: "bouwjaar van 2018 of ouder … niet in de bebouwde kom". 2030: electric only | Whole municipality closed to combustion, which already contains both later steps |
| Utrecht | **From 2028-01-01**: "brom- en snorfietsen op benzine, diesel of gas met een datum eerste toelating (DET) tot en met 31-12-2017 niet meer in Utrecht rijden", for "heel de gemeente Utrecht". **From 2030**: all must be uitstootvrij | Recorded with `valid_from`, refusing nothing until the date arrives |

Sources: <https://www.milieuzones.nl/locaties-milieuzones>,
<https://www.denhaag.nl/nl/verkeer-en-vervoer/milieuzone-oude-brom-en-snorfietsen/>,
<https://www.nijmegen.nl/over-de-gemeente/plannen/milieuzone-bromfietsen/>,
<https://www.utrecht.nl/wonen-en-leven/gezonde-leefomgeving/luchtkwaliteit/brom-en-snorfietsen-uitstootvrij>.

**A dated measure is easy to miss.** Utrecht's rule starts three years out, so
the national index does not list it among the municipalities that *have* a moped
zone. `valid_from` exists so an announced measure can be written down when it is
published rather than remembered when it bites. Brommobielen are
deliberately absent from the Utrecht entry: the same page says they "mogen
waarschijnlijk in Utrecht blijven rijden" with a decision due in 2026, and a
rule still being decided is not one this router may act on.

**There is no national source for these.** NDW publishes emission zones at
`https://data.ndw.nu/api/rest/static-road-data/emission-zones/v1/map` — 40 zones
across 28 municipalities, with validity dates and the regulation id — but it
covers cars, vans, lorries and buses only. Across the whole payload the strings
`brom`, `snor`, `moped`, `l1e` and `scooter` appear **zero** times, and every
exemption is `{vehicleType: CAR|VAN|TRUCK|BUS}`. Its Amsterdam and Den Haag
entries link to the diesel-car and lorry pages, not the moped ones. Using it
here would either lose the moped zones or apply lorry rules to mopeds. Measured
2026-08-15.

A missing or malformed zone file returns 503 rather than skipping the check, and
a malformed validity date is a hard error rather than an ignored field: dropping
it silently would make a dated rule bind immediately, or never.

## Signs

| Code | Caption | Meaning for us |
| --- | --- | --- |
| **G1 / G3** | Autosnelweg / Autoweg | Barred to all four: art. 42 admits only motorvoertuigen |
| **G7 / G9** | Voetpad / Ruiterpad | Barred to all four |
| **G11** | Verplicht fietspad | Snorfiets yes, bromfiets no. Snorfiets no inside an art. 5 lid 8 municipality |
| **G12** | Einde verplicht fietspad | End marker |
| **G12a** | Fiets/bromfietspad | Snorfiets yes, bromfiets yes, brommobiel no |
| **G12b** | Einde fiets/bromfietspad | End marker |
| **G13** | Onverplicht fietspad | Closed to all in the graph: optional, so never using it cannot make a route illegal |
| **G14** | Einde onverplicht fietspad | End marker |
| **A1** | Maximumsnelheid | Speed limit. Closes a **way** if OSM carries no matching `maxspeed`; never closes a node |
| **A3** | Maximumsnelheid op een electronisch signaleringsbord | Always closes a way: its display can change after the build |
| **C-series** | See NL-ACC-06 | Prohibitions. The only family that may close a node |
| **D1** | Rotonde; verplichte rijrichting | Roundabout. Closes a way, never a node |
| **D2** | Gebod voor alle bestuurders het bord voorbij te gaan aan de zijde die de pijl aangeeft | Pass on the side the arrow shows. Closes a way, never a node |
| **D4–D7** | Gebod tot rijrichting | Mandatory direction. Closes a way |
| **F7** | Keerverbod | No U-turn. Closes a way |
| **H1 / H2** | Bebouwde kom begin / einde | Not usable: only 29 nodes nationwide carry it in OSM. See [Speeds](#speeds) |

An unsigned path is **none** of G11/G12a/G13, because those terms exist only as
sign captions (NL-ACC-03). The country's `unsigned_cycleway` default is
`{false, false}`.

How much of the network that reaches, measured against the extract on
2026-08-15:

| | |
| --- | --- |
| Dutch highway ways | 2,796,046 |
| of which cycleways | 258,625 |
| cycleways with `moped=designated` (a G12a) | 68,244 |
| cycleways with `moped=no` (a G11 or G13) | 90,139 |
| cycleways with `moped=yes` | 2,711 |
| **cycleways with neither a sign nor a `moped`/`mofa` tag** | **84,867 — 32.8%** |
| ways with `moped=use_sidepath` | 44,717 |
| nodes carrying an H1 bebouwde-kom sign | **29** |
| barrier nodes | 234,649 |

`designated`, not `yes`, is how the Netherlands marks a bromfietspad — 68,244
against 2,711 — so an access table missing `designated` locks bromfietsen out
of the entire cycle network. The 29 H1 nodes are why the speed table always reports the
built-up figure.

## Speeds

RVV arts. 20, 21 and 22. Not the road's signed limit: the limit that binds
*this* vehicle.

| Profile | Roadway | Cycle path, built-up | Cycle path, rural |
| --- | --- | --- | --- |
| snorfiets | 25 | 25 | 25 |
| bromfiets | 45 | 30 | 40 |
| speed pedelec | 45 | 30 | 40 |
| brommobiel | 45 | — | — |

A posted limit lower than the class limit binds too: a 30 zone is 30 for a
bromfiets as much as for a car. Inside an *erf* (`highway=living_street`) art.
45 caps every bestuurder at 15.

**The bebouwde kom is not derivable from OpenStreetMap.** 29 nodes nationwide
carry the H1 sign; this was measured, do not look for it again. So the
built-up figure — 30 rather than 40 — is the one to report on a cycle path.
That is permanent, not a placeholder, and it can never produce a fine.

Unlike access, a speed is **not** baked into the tiles. It depends on the road
as well as the vehicle, so it is decided per request by whatever serves the
graph, and a speed correction does not need a rebuild. What lives here is the
table itself, as `ClassSpeeds` in the country module.

A consumer applying it should take the country's table as a **required**
argument with no default: substituting one country's limits for another is
exactly the mistake that requirement exists to make impossible. It should also
be able to say it does not know. A country or a future data source may be unable
to establish a limit for a particular edge, and absence must not be turned into
a made-up number; the Netherlands module returns its conservative class and
infrastructure cap when the road has no mapped posted limit, because that value
is established independently of the missing tag.

## Authority overlay

`infra/official_access.py` writes four values into the extract, under keys
`amgraph:snorfiets` and `amgraph:bromfiets`. Each has exactly one job.

| Value | Meaning | Where it may appear |
| --- | --- | --- |
| `no` | The class may not be here | Anywhere |
| `on_roadway` | Nothing lawful runs beside this carriageway, so lid 2 keeps it open | Carriageways only |
| `roadway_only` | Art. 5 lid 8: this verplicht fietspad does not admit a snorfiets | Cycle paths, snorfiets key only |
| `yes` | The register says a G12a stands on this unsigned path | Cycle paths, snorfiets key only |

A refusal is cheap to accept and an affirmation is not, so the two openings are
each bounded to a case where the law leaves no discretion, and
`tests/test_official_overlay.py` asserts those bounds rather than trusting them.

### Why `no` does not override an OSM cycle sign

The overlay exists for mandatory use, which is a statement about
**carriageways**: OSM under-states `use_sidepath`, so on a roadway its silence
is expected and the authority adds real evidence. On a cycle path the position
reverses. A mapper who wrote `traffic_sign=NL:G12a` with `moped=designated` has
recorded the sign on the ground, which is the thing the law turns on, while the
overlay reaches the way by a geometric match against a dataset whose own
documentation warns that sign-to-road coupling is often wrong.

Letting the match win closes fiets/bromfietspaden the statute positively sends
riders onto. `roadway_only` is the single exception, because its entire content
is that the sign does not mean what it usually means.

### The mandatory-use gate

For each carriageway the authority or OSM closes:

- a path runs alongside that the class **may** use → the closure is a real
  obligation and stands as `no`;
- a path runs alongside that the rules **refuse** → contradiction, lid 2
  applies, `on_roadway`;
- **no** path runs alongside → the refusal was never about mandatory use, so it
  is a prohibition in its own right and stays `no`.

Measured on the 2026-08-15 extract: 93,313 closures kept with a usable path
beside, 68,176 kept with no path beside, 19,734 deadlocks resolved to the
roadway, and 30,199 carriageways kept open for the snorfiets under art. 5 lid 8.

### The sign register

NDW's verkeersbordenbestand carries 181,765 *placed* cycle signs (G11 99,505 /
G12a 65,035 / G13 17,225). Matching them to OSM ways at 20 m, with a 30 m
no-conflicting-sign clearance, agrees with OSM on **96.1%** of the 103,094 ways
where both sources speak.

The headline accuracy is not what decides the policy — the confusion direction
is. A G11/G12a mix-up is free for a snorfiets, because art. 5 lid 1 admits it
to both, and a **3.00%** false-opening rate for a bromfiets, because G11 bars it
and G12a admits it. So the register opens a path for the snorfiets only, and
only on a G12a, where the measured disagreement is 0.47%. A bromfiets gets the
rijbaan from art. 6 lid 2 instead, at no cost.

**Gotcha:** `validated` is `n` on every one of the 181,765 signs, so filtering
on it discards the whole source.

## Data limitations

| Not handled | Why | Effect on a rider |
| --- | --- | --- |
| Temporary or newly placed restrictions | No verified live closure feed is integrated | The graph cannot know it |
| Mandatory use where OSM and WKD are both silent | Only 46.9% of the obligation is expressed in OSM | A rider may be routed on the carriageway where the sidepath was compulsory |
| A combustion vehicle's year, engine cycle or exemption | Not in the request | Emission-zone municipalities closed conservatively |
| Actual vehicle dimensions, load or trailer | Not in the request | Dimension-controlled ways closed; C10 closes the brommobiel |
| G13 for an electric snorfiets | One access bit, built before powertrain is chosen | Detours. Needs a distinct access class |
| The bebouwde kom | 29 nodes nationwide | Always reports 30 on a cycle path |
| Untagged cycle paths the register cannot resolve | Ambiguous between opposite answers | Treated as forbidden; longer routes |
| Zeeland / Walcheren | The crossings are motorway, C9 or the Westerscheldetunnel, and whether a lawful moped route exists **has not been established from primary sources** | Middelburg is currently unreachable for every class |

### Honest answer to "is every route legally valid?"

**No route this graph admits breaks a rule we know about and can read from the data**,
and that claim is stronger than a sample: the exhaustive audit puts every
distinct access-tag combination in the country through the rules, so it is a
statement about the whole network rather than about routes somebody happened to
test.

It is not the same as "every route is legally valid". Three gaps stand between
the two, all listed above and none of them hidden: the mandatory-use obligation
that OSM expresses on under half the network it binds; OSM and WKD themselves
being wrong in places we cannot detect; and anything that changed on the ground
since the last extract. The failure direction of all three is a rider on the
carriageway where they should have been on the path — a fine, not a vehicle on
a motorway.

## Data sources

| Source | Role | Caveat |
| --- | --- | --- |
| Geofabrik NL extract (OSM, ODbL) | Routable topology, paths, turn restrictions, access tags | Crowd-sourced, not a legal authority; access tags can be missing or stale |
| NDW verkeersborden v4 | The signs actually on the ground | ~1.9M of >3M physical signs; coordinates sometimes mark the photo position; `validated` is `n` on every cycle sign |
| RWS WKD Verkeerstypen | Per-section class access, i.e. mandatory use | NDW warns sign-to-NWB coupling is often wrong; monthly |
| PDOK BRK Bestuurlijke Gebieden | National and municipal boundaries (CC BY 4.0) | Municipality ≠ bebouwde kom |

Conflict stance: prefer the source that is closest to the thing the law turns
on. On a cycle path that is the sign the mapper recorded; on a carriageway's
mandatory-use question it is the authority's per-section verdict, because OSM
under-states it. Where they disagree and neither is closer, the refusal wins.

## Junction interpretation

The shared node rules are in [the access model](../access-model.md). Two of
them read on Dutch signs as follows: a `maxspeed` tag or an A1 sign never closes
a node, and only a geslotenverklaring may. `countries/nl.lua` marks those with
`bars_entry = true`, so C2 closes a node while C3/C4, D1 and D2 do not.
