# Netherlands rules

Primary sources last reviewed **2026-11-14**. The country module declares
`nl-2026-11-14.1`.

[Documentation](../README.md) · [Shared country rules](../country-rules.md)

## Vehicle classes

| Profile | Plate | Max | Cycle infrastructure |
| --- | --- | --- | --- |
| `snorfiets` | light blue | 25 | Follows **bicycle** rules. Must use G11 and G12a. May use G13 if electric |
| `bromfiets` | yellow | 45 | Must use **G12a only**. G11 and G13 are closed |
| `brommobiel` | yellow | 45 | **None.** Roadway only |

The enum values stay Dutch; the labels riders see are English. `snorfiets` in
code, "Light moped" on screen. The identifiers are statutory terms and the
rules are written against them, so a translated identifier would put guesswork
between the code and the law.

**NL-DEF-01 — snorfiets** `VERIFIED`
> "bromfiets die blijkens de gegevens in het kentekenregister is geconstrueerd
> voor een maximumsnelheid die niet meer bedraagt dan 25 km per uur, met
> uitzondering van de speed-pedelec"

**NL-DEF-02 — brommobiel** `VERIFIED`
> "bromfiets op meer dan twee wielen, die is voorzien van een carrosserie"

Both build on the bromfiets of WVW 1994 art. 1(1)(e): a motorrijtuig "met een
door de constructie bepaalde maximumsnelheid van niet meer dan 45 km/h"
(<https://wetten.overheid.nl/BWBR0006622/2026-09-01>, read 2026-11-14).

**Adopted, not yet in force.** Stb. 2023, 377 replaces that definition with
"voertuig als bedoeld in artikel 4 van verordening (EU) 168/2013 met de
voertuigclassificatie L1e, L2e of L6e", and enters into force "met ingang van
een bij koninklijk besluit te bepalen tijdstip". No decree has set the date.
The three classes stand on the current text until one does, and are
re-researched against the new text that day.
<https://zoek.officielebekendmakingen.nl/stb-2023-377.html>, read 2026-11-14.

**NL-DEF-04 — autosnelweg / autoweg** `VERIFIED` — defined **by their sign**:
"weg, aangeduid door bord G1 / G3 van bijlage I". Not by road class.

**NL-DEF-05 — motorvoertuig excludes bromfietsen** `VERIFIED`
> "alle gemotoriseerde voertuigen behalve bromfietsen, fietsen met
> trapondersteuning en gehandicaptenvoertuigen"

Consequence: rules written for *motorvoertuigen* do not apply to the snorfiets
or the bromfiets. They do apply to the brommobiel, by RVV art. 2a:

> "De regels van dit besluit betreffende motorvoertuigen en bestuurders en
> passagiers van motorvoertuigen zijn, in plaats van de regels betreffende
> bromfietsen, bromfietsers en passagiers van bromfietsen, mede van toepassing
> op brommobielen en bestuurders en passagiers van brommobielen, tenzij anders
> is bepaald."

That changes no answer: art. 22 caps the brommobiel at 45 below the art. 20
urban 50, and art. 42 admits to the autosnelweg and autoweg only a vehicle that
"mag en kan" reach 60 and 50, which a brommobiel cannot.

**NL-DEF-06 — plate colours** `VERIFIED`. Regeling kentekens en kentekenplaten
art. 3 gives every bromfiets plate a yellow background:

> lid 1: "De kleur van de achtergrond is geel voor de modellen 27.1A tot en met
> 27.2H, 27.10A tot en met 27.10E en 30.1A tot en met 30.2D"

except a bromfiets built for 25 km/h, which is the snorfiets:

> lid 7: "In afwijking van de voorgaande leden moeten kentekens welke zijn
> opgegeven voor bromfietsen die geconstrueerd zijn voor een maximumsnelheid
> van ten hoogste 25 km/h niet zijnde speed-pedelecs"

whose plate background "is lichtblauw". A brommobiel is a bromfiets, so it
carries the yellow plate. Source:
<https://wetten.overheid.nl/BWBR0009071/2026-01-01>, read 2026-11-14.

All RVV citations: <https://wetten.overheid.nl/BWBR0004825/2026-07-01>,
read 2026-11-14.

## Access rules

### NL-ACC-01 — No autosnelweg, no autoweg, for any class `VERIFIED`

> lid 1: "Het gebruik van de autosnelweg is slechts toegestaan voor bestuurders
> van een motorvoertuig waarmee met een snelheid van ten minste 60 km per uur
> mag en kan worden gereden."
> lid 2: "Het gebruik van de autoweg is slechts toegestaan voor bestuurders van
> een motorvoertuig waarmee met een snelheid van ten minste 50 km per uur mag
> en kan worden gereden."

RVV 1990 **art. 42**. Source:
<https://wetten.overheid.nl/BWBR0004825/2026-07-01>, read 2026-11-14.

The article works as a **permission, not a prohibition**, and reading it that
way is what makes it airtight for us. Use of an autosnelweg or autoweg is
allowed only to a *motorvoertuig*, and NL-DEF-05 puts every bromfiets outside
that word. All three profiles are bromfietsen, so none of them is inside the
permission at all — and separately, none can do 60 or even 50 km/h, so none
would qualify even if it were.

Art. 43 is **not** the authority here, and it is the article a reader expects:
it covers U-turns, reversing, stopping and the hard shoulder, and the
often-quoted sentence barring bromfietsen from autosnelwegen by name is not in
the consolidated text in force.

**Router:** hard exclusion. `highway=motorway`, `motorway_link` and any
`motorroad=yes` are forbidden for every profile in both directions, with no
cost-based escape.

### NL-ACC-02 — Bromfiets `VERIFIED`

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
rider to the rijbaan. Read 2026-11-14.

**G13 is closed to both powertrains.** Art. 5 lid 3 admits a snorfiets, but a
combustion one only with the engine off, and the graph is built before the
rider picks a powertrain. Stricter than the statute for an electric snorfiets,
but it cannot produce an illegal route. Opening it only for electric needs a
distinct graph access class, not an API switch.

**A cycle path open to the bromfiets admits the snorfiets.** The G12a is the
only sign that admits a bromfiets to the cycle network (NL-ACC-02), and it
admits a snorfiets. Art. 5 lid 8 reaches the G11 alone, so no municipality's
measure takes the snorfiets off it. Where a mapper permits `moped` on a cycle
path with no mapped sign, the path is therefore open to the snorfiets as well,
unless the same way refuses bicycles or the snorfiets, which a G12a would
admit.

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

"Every carriageway" is meant literally. Whether a way lies inside the boundary
is not a geometric match, so the length floor that guards the matcher's
judgements does not apply to it: a junction stub or a bridge a few metres long
carries the stamp like the road it joins, because any one of them left out
closes that road. The stamp also lifts a sidepath obligation mapped for one
direction (`mofa:forward=use_sidepath`, or `bicycle:*` read through bicycle
rules), which is the same obligation for half the carriageway; any other
directional value still closes the class. `REQUIRED_ROUTE_CHECKS` routes every
class into and across both city centres on each release, and one failure stops
it.

**Limit of the measure:** lid 8 reaches "het verkeersteken dat het verplichte
fietspad aangeeft", which is the **G11 alone**. A fiets/bromfietspad is outside
its scope, so a snorfiets on an Amsterdam G12a is lawful.

**An onderbord anywhere.** Lid 8 needs the onderbord on the G11, and the
onderbord is what a rider sees. Wherever the mapper wrote one naming the
snorfiets into the G11's `traffic_sign`, or the register G11 nearest the path
carries one, the snorfiets comes off that path in any municipality, not only
in Amsterdam and Utrecht. Searching every
published decision for the measure on 2026-11-13 found it taken only by
Amsterdam and Utrecht; elsewhere the register holds such plates without a
decision behind them that the search found, and the plate decides.

**Utrecht names its roads.** Gmb. 2021, 212045,
<https://zoek.officielebekendmakingen.nl/gmb-2021-212045.html>, read
2026-11-13, puts the onderbord on "de volgende locaties waar een verplicht
fietspad aanwezig is" and lists each road and solitary path, and later
decisions add Biltstraat, Vleutenseweg, Jutfaseweg, Paardenveld and Croeselaan.
`ART5_LID8_LISTED` holds those names. Inside Utrecht a G11 loses the snorfiets
only on a listed road, on an unnamed path (the list's solitary paths have no
street of their own, so one may be listed), or where an onderbord is mapped or
in the register. Every other Utrecht G11 admits and obliges it under art. 5
lid 1, and only listed carriageways are stamped `on_roadway`.

**Roads Amsterdam left out.** The Amsterdam decision does not reach its main
through-routes:

> "Echter op de belangrijkste doorstromingswegen voor auto en voor openbaar
> vervoer wordt de maatregel voorlopig niet ingevoerd."

Stcrt. 2018, 71559, p. 8,
<https://zoek.officielebekendmakingen.nl/stcrt-2018-71559.pdf>, read
2026-11-13. It lists Prins Hendrikkade between Centraal Station and the
IJ-tunnel; Nieuwe Leeuwarderweg – IJ-tunnel – Valkenburgerstraat –
Weesperstraat – Wibautstraat – Gooiseweg; Transformatorweg – Spaarndammerdijk –
Tasmanstraat – Van Diemenstraat – Westerdoksdijk – De Ruijterkade – Piet
Heinkade – Piet Heintunnel – IJburglaan; the S100 (Houtmankade – Nassaukade –
Stadhouderskade – Mauritskade – Zeeburgerdijk – Panamalaan); Kattenburgerstraat
and Prins Hendrikkade between the IJ-tunnel and Kattenburgerstraat; and the
Schellingwouderbrug and Amsterdamsebrug. The exception still stands in 2025:

> "de gemeente Amsterdam in 2019 diverse verkeersbesluiten heeft genomen
> waarbij snorfietsen niet zijn toegestaan op verplichte fietspaden en zij
> moeten rijden op de autorijbaan met helmplicht, met uitzondering van de De
> Ruijterkade"

Gmb. 2025, 474758, <https://zoek.officielebekendmakingen.nl/gmb-2025-474758.html>,
read 2026-11-13. One road has since been brought under the measure:

> "Door het plaatsen van verkeersborden conform model G11 van Bijlage I van het
> RVV 1990, met onderborden met de tekst: “snorfietsen niet toegestaan”, te
> bepalen dat snorfietsen op de hoofdrijbaan moeten rijden op de
> Kattenburgerstraat."

Gmb. 2023, 51567, <https://zoek.officielebekendmakingen.nl/gmb-2023-51567.html>,
read 2026-11-13. Every Amsterdam verkeersbesluit after 2018-12-17 that
repository.overheid.nl returns for a listed road together with the snorfiets
was read on 2026-11-13, and none other puts the onderbord on a listed road.

On these roads art. 5 lid 1 holds: the G11 admits the snorfiets and obliges it.
`ART5_LID8_EXEMPT_ROADS` in the country module holds the list, each road with
the box it applies in: Prins Hendrikkade only east of the station, the rest
within Amsterdam, Kattenburgerstraat left out. `official_access.py` keeps the
snorfiets on a G11 named for one of them, or running beside one, and stamps no
`on_roadway` on their carriageways. A register G11 beside the path whose
onderbord names the snorfiets still wins, because that plate is the measure.

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
signs apply to a snorfiets. A brommobiel is a bromfiets (WVW art. 1), and
whether art. 2a's swap to motor-vehicle rules lifts a caption that names
bromfietsen is the question NL-ACC-07 leaves open for the snorfiets: no primary
source says a sign is one of "de regels van dit besluit". So C13 and C15 close
the brommobiel too.

| Sign | Statutory description | Closed |
| --- | --- | --- |
| C1 | "Gesloten in beide richtingen voor voertuigen, ruiters en geleiders van rij- of trekdieren of vee" | all three |
| C2 | "Eenrichtingsweg, in deze richting gesloten voor voertuigen…" | all three, indicated direction |
| C3/C4 | "Eenrichtingsweg" | reverse direction |
| C6 | "Gesloten voor motorvoertuigen op meer dan twee wielen" | brommobiel (art. 2a) |
| C9 | "Gesloten voor ruiters, vee, wagens, landbouw- en bosbouwtrekkers, motorrijtuigen met beperkte snelheid, mobiele machines, brommobielen, fietsen, snorfietsen, bromfietsen en gehandicaptenvoertuigen" | all three |
| C10 | "Gesloten voor motorvoertuigen met aanhangwagen" | brommobiel, trailer status unknown |
| C12 | "Gesloten voor alle motorvoertuigen" | brommobiel (art. 2a) |
| C13 | "Gesloten voor bromfietsen, snorfietsen en gehandicaptenvoertuigen, met in werking zijnde motor" | all three |
| C14 | "Gesloten voor fietsen en voor gehandicaptenvoertuigen zonder motor" | snorfiets (art. 2b) |
| C15 | "Gesloten voor fietsen, bromfietsen en gehandicaptenvoertuigen" | all three |
| C17 | "Gesloten voor voertuigen en samenstellen van voertuigen die, met inbegrip van de lading, langer zijn dan op het bord is aangegeven" | all three below 6.5 m; none from 6.5 m |
| C18 | "Gesloten voor voertuigen die, met inbegrip van de lading, breder zijn dan op het bord is aangegeven" | all three below 2.0 m; none from 2.0 m |
| C19 | "Gesloten voor voertuigen die, met inbegrip van de lading, hoger zijn dan op het bord is aangegeven" | all three below 2.5 m; none from 2.5 m |
| C20 | "Gesloten voor voertuigen waarvan de aslast hoger is dan op het bord is aangegeven" | all three below 1 t; none from 1 t |
| C21 | "Gesloten voor voertuigen en samenstellen van voertuigen, waarvan de totaalmassa of de som van de aslasten hoger is dan op het bord is aangegeven" | all three below 1 t; none from 1 t |
| C22 | "Gesloten voor voertuigen met bepaalde gevaarlijke stoffen" | all three, while cargo is unknown |

**Router:** an unscoped prohibition closes both directions when its physical
direction cannot be recovered. `traffic_sign:forward` and `:backward` close only
the named direction. C3/C4 without either a scope or an OSM `oneway` value close
both rather than guessing which way the road runs.

The request carries no trailer, cargo, width, height, length or axle load, so
C10 closes the brommobiel, C22 closes every profile, and C17–C21 close every
profile unless the value is one no class can exceed. Stricter than
necessary when a particular vehicle fits; assuming it fits can issue a route
barred by the value on the sign.

C17–C21 bind only a vehicle larger than the sign, and the largest each class can
be is written down:

- Regulation (EU) 168/2013 Annex I, for every L-category vehicle: "length ≤ 4 000
  mm or ≤ 3 000 mm for a L6e-B vehicle", "height ≤ 2 500
  mm", "width ≤ 2 000 mm, or ≤ 1 000 mm for a L1e vehicle, or ≤ 1 500 mm for a
  L6e-B or a L7e-C vehicle", and for L6e "the mass in running order ≤ 425 kg".
  <https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32013R0168>
- Regeling voertuigen art. 5.18.27, the trailer a C21 counts with its
  "samenstellen": behind a two-wheeler "de breedte … niet meer bedragen dan
  1,00 m", "de hoogte … niet meer bedragen dan 1,00 m" and "de afstand van de
  achteras van de trekkende bromfiets tot de achterzijde van de aanhangwagen met
  inbegrip van de lading mag niet meer bedragen dan 2,00 m"; behind a moped on
  more than two wheels 2,00 m, 1,50 m and 2,50 m; in both cases "de totale massa van het
  voertuig mag niet meer bedragen dan de helft van de ledige massa van de
  trekkende bromfiets".
  <https://wetten.overheid.nl/BWBR0025798/2026-07-01>

A width from 2.0 m, a height from 2.5 m and a length from 6.5 m (4 m of vehicle
and 2.5 m of trailer behind its rear axle) therefore bind no L-category class. No
law caps the mass of an L1e two-wheeler; 1 t for mass and axle load is the
maintainer's decision of 2026-11-08 that none of the three comes near, a brommobiel with its trailer included. `unbound_from` in
`countries/nl.lua` holds these values for the tags and for the value on a
mapped sign, such as `NL:C19[3.9]`. A sign without a value, an unreadable value
or another unit still closes the way. RVV 1990 bijlage 1 and both regulations
read 2026-11-08.

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
a contradictory generic highway tag from opening it. An onderbord can still
admit a class to a G7; see NL-ACC-12.

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
can only refuse a lawful trip and never permit an unlawful one. All read
2026-11-14.

| Municipality | The by-law | What we do |
| --- | --- | --- |
| Amsterdam | A current brom- and snorfiets milieuzone | Whole municipality closed to combustion |
| Den Haag | DET before 2011-01-01: "U mag met een brom- of snorfiets van vóór 1 januari 2011 niet in de milieuzone rijden. Met oude elektrische brom- en snorfietsen en met brommobielen mag dit wel." A pre-2011 four-stroke may ride after an inspection and with an ontheffing | Whole municipality closed to combustion, four-stroke included |
| Nijmegen | Build year 2010 or older, in **three areas** — Nijmegen centrum, Hof van Holland, Heijendaal. 2028: "bouwjaar van 2018 of ouder … niet in de bebouwde kom". 2030: electric only | Whole municipality closed to combustion, which already contains both later steps |
| Utrecht | **From 2028-01-01**: "brom- en snorfietsen op benzine, diesel of gas met een datum eerste toelating (DET) tot en met 31-12-2017 niet meer in Utrecht rijden", for "heel de gemeente Utrecht". **From 2030**: all must be uitstootvrij | Recorded with `valid_from`, refusing nothing until the date arrives |

Sources: <https://www.milieuzones.nl/locaties-milieuzones>,
<https://www.denhaag.nl/nl/verkeer-en-vervoer/milieuzone-oude-brom-en-snorfietsen/>,
<https://www.nijmegen.nl/verkeer-en-vervoer/milieuzone-bromfietsen/>,
<https://www.utrecht.nl/wonen-en-leven/gezonde-leefomgeving/luchtkwaliteit/brom-en-snorfietsen-uitstootvrij>.

**A dated measure is easy to miss.** Utrecht's rule starts three years out, so
the national index does not list it among the municipalities that *have* a moped
zone. `valid_from` exists so an announced measure can be written down when it is
published rather than remembered when it bites. Brommobielen are
deliberately absent from the Utrecht entry: the same page says they "mogen
waarschijnlijk in Utrecht blijven rijden" with a decision due in 2026, and a
rule still being decided is not one this router may act on.

**There is no national source for these.** NDW publishes emission zones at
`https://data.ndw.nu/api/rest/static-road-data/emission-zones/v1/map`, but it
covers cars, vans, lorries and buses only: no zone names a moped, and every
exemption is `{vehicleType: CAR|VAN|TRUCK|BUS}`. Using it here would either lose
the moped zones or apply lorry rules to mopeds.

A missing or malformed zone file returns 503 rather than skipping the check, and
a malformed validity date is a hard error rather than an ignored field: dropping
it silently would make a dated rule bind immediately, or never.

### NL-ACC-11 — A bus lane closes its own lane `VERIFIED`

> "busstrook : door doorgetrokken of onderbroken strepen gemarkeerd gedeelte
> van de rijbaan waarop het woord «BUS» of «LIJNBUS» is aangebracht"

> "Busbanen en busstroken waarop het woord «BUS» is aangebracht mogen slechts
> worden gebruikt door bestuurders van een lijnbus, een autobus of een tram.
> Busbanen en busstroken waarop het woord «LIJNBUS» is aangebracht mogen slechts
> worden gebruikt door bestuurders van een lijnbus of een tram."

RVV art. 1 and art. 81, <https://wetten.overheid.nl/BWBR0004825/2026-07-01>,
retrieved 2026-10-17. Bijlage I describes F13, F17 and F19 the same way:
"Rijbaan of -strook uitsluitend ten behoeve van" lijnbussen, lijnbussen en
trams, and vrachtauto's en lijnbussen.

A busstrook is a *part* of the rijbaan and art. 81 reserves that part alone. The
lanes beside it are ordinary rijbaan, where every other rule in this document
decides who rides. Closing the whole road for its bus lane closes the rijbaan
that NL-ACC-05 makes mandatory for a brommobiel and that art. 5 lid 2 and art. 6
lid 2 make mandatory for the two-wheelers where no path is established.

**Turning across the bus lane.** Art. 81 forbids using the lane, not crossing
it, but art. 76 lid 1 forbids crossing a solid line: "Een doorgetrokken streep
die zich niet langs de rand van de rijbaanverharding bevindt, mag niet worden
overschreden", unless lid 2(b) applies, "indien aan de zijde vanwaar men de
streep overschrijdt een onderbroken streep is aangebracht". No source says
which bus-lane lines are solid. The Uitvoeringsvoorschriften BABW inzake
verkeerstekens (<https://wetten.overheid.nl/BWBR0009104>, version 2023-10-01,
read 2026-10-17) set only a 20 m minimum length for that line; WKD Rijstroken
counts bus lanes per section (`BUUSSTRK`) and records no line type; the BGT
holds a bus lane only where it is physically separated. A turn across a bus
lane therefore cannot be shown lawful, so a road where one could be made stays
closed.

**Router:** the general lane keys are read, and stop closing the way, only when
all of these hold:

- each lane's direction is known: `access:lanes` and `vehicle:lanes` on a
  forward one-way (`oneway=yes` or a roundabout), or `:lanes:forward` and
  `:lanes:backward` on a two-way road with no unscoped lane key. OSM lists the
  values "in left-to-right order as viewed in the respective driving direction
  of those lanes" (<https://wiki.openstreetmap.org/wiki/Lanes>, read
  2026-11-08), so each direction is read in its own travel order;
- each family of lane keys carries exactly one of `bus:lanes` and `psv:lanes`
  with the same suffix, with the same lane count as every general key;
- every lane a general key does not open (`yes`, `designated`, `permissive`) is
  marked `yes` or `designated` for buses or psv;
- at least one lane is open under every general key;
- the way carries `amgraph:bus_lane_turns=none`, which `infra/bus_lanes.py`
  writes only where no road a class could enter joins on a closed lane's side
  at any node. On a one-way road a lane on the right is crossed by a right turn,
  one on the left by a left turn, one between open lanes by both. On a two-way
  road a bus lane at its own direction's kerb is crossed by turns to that side
  of the road, and any other bus lane by turns to both sides, because the
  oncoming traffic turns across it too. At the first and last node the
  one way within 25° of straight on is the road carrying on; every other join
  is a turn, and one within 5° of the road's line, which cannot be put on a
  side, closes the way.

The way is then decided as if the lane tags were absent, so a moped refusal, a
sign or the authority overlay closes it exactly as it would anywhere else.
Everything else keeps the whole-way closure: unscoped lane keys on a two-way
road, directional lane keys on a one-way road, a reversed one-way road, a
directional `access:forward` or `access:backward`, a lane closed for anything
but a bus, any lane tag naming a class (`moped:lanes`,
`motor_vehicle:lanes`), and every cycle path.

Turn restrictions would reopen more and are not used. Valhalla 3.8.3
(`CreateSimpleTurnRestriction` in `src/mjolnir/graphbuilder.cc`) blocks only the
first edge whose way matches a restriction's `to` way, so where a side street
runs through the junction it can block the lawful half and leave the turn
across the bus lane open.

Two examples. The Jaagweg in Purmerend, beside the old Amsterdam–Purmerend
tram path, has its bus lane on the right and no road joining it, so it is
reopened. The Zeeweg (N200) towards Bloemendaal aan Zee is reopened where its
bus lane is on the left and nothing joins, and stays closed where the bus lane
runs between two open lanes and a turning lane leaves beyond it. On the
two-way stretch of the Jaagweg (way 740662887) and on the Willemsbrug in
Rotterdam the bus lane is at the kerb with no road joining on its side, so both
reopen; on Alexanderplein in Amsterdam it runs beside the centre line and stays
closed.

### NL-ACC-12 — A voetpad whose onderbord admits bromfietsen `VERIFIED`

> "Verkeerstekens gaan boven verkeersregels, voor zover deze regels
> onverenigbaar zijn met deze tekens."

> "Indien het beoogde verkeersgedrag wordt aangegeven door middel van teksten of
> tekens al dan niet in combinatie met symbolen, blijkt het beoogde
> verkeersgedrag uit het onderbord."

RVV arts. 63 and 67 lid 2, text in force from 2026-07-01, read 2026-11-13 at
<https://wetten.overheid.nl/BWBR0004825/2026-07-01>. A G7 bars these classes
(NL-ACC-08), but an onderbord reading "brom-fietsen toegestaan" admits
bromfietsen to that voetpad, and a snorfiets is a bromfiets (NL-DEF-01). The
square at the Centraal Station ferries is one: Stcrt. 2015, 6116 makes the
pontsteiger area a voetgebied where "(brom)fietsen is toegestaan", the
register photographs the plate at both ends, and the city's panorama of
2025-06-17 shows it with an A1 of 15. Gmb. 2022, 27963 does the same south of
the IJplein ferry landing ("met onderborden met de tekst: “(brom)fietsen
toegestaan”").

**Two sources, always.** `official_access.py` writes `footpath_onderbord` on a
footway or pedestrian way for a class only when the mapper put a G7 on it, or no sign at all, and
permits the class (`moped` or `mofa` `yes`, `designated` or `permissive`), and
a placed register G7 within 20 m carries a plate from a closed list of
admitting texts and no other plate. A G7 and its onderbord govern the voetpad behind them until the next sign, so the confirmation is carried over connected footways and pedestrian ways that carry no other sign and on which the mapper permits the class, with the register's A1, up to `SPREAD_METRES` from the confirmed way. Either source alone opens nothing: OSM
carries moped permissions on voetpaden where no such plate stands, and the
register's onderbord text is sometimes missing. A plate with hours or any
other condition is not on the list, because this graph cannot hold one.
`lifted_by_plate` on the G7 entry in
`countries/nl.lua` lets the confirmed plate lift that sign's bar for the class
it admits.

**A G12a drawn as a footpath.** A G12a makes a fiets/bromfietspad (NL-ACC-03)
whatever highway value the mapper chose. Where the mapper's G12a on a footway
or pedestrian way is confirmed by the register's own G12a for it,
`footpath_g12a` makes the way cycle infrastructure and the G12a rules apply in
full.

**Speed.** No article sets a bromfiets limit on a voetpad, so a posted A1
binds. Where the register has an A1 within 20 m of an opened way and OSM has no
lower `maxspeed`, its figure is written as `maxspeed`, because that is the only
place the API reads a posted limit. Art. 20(c) does not reach an ordinary
snorfiets here: its 6 km/h binds, besides motorised vehicles for the disabled,
only "snorfietsen als bedoeld in artikel 1, eerste lid, onderdeel e,
subonderdeel d, van de wet", and WVW 1994 art. 1(1)(e)(d) is a light electric
vehicle "met een door de constructie bepaalde maximumsnelheid van niet meer
dan 25 km/h" that needs no EU type approval
(<https://wetten.overheid.nl/BWBR0006622/2026-09-01>, read 2026-11-14). A
type-approved blue-plate snorfiets falls under subonderdeel a.

**Who stays out.** The brommobiel: art. 6 lid 3 puts it on the rijbaan, and
GVB's rules for the ferries these squares serve say "Brommobielen mogen niet
mee op onze IJ-veerponten"
(<https://www.gvb.nl/reisinformatie/reisregels-en-voorwaarden>, read
2026-11-13). Stcrt. 2015, 40478 does admit it to the (brom)fietspad east of the
pontsteiger, but no plate on the square names it, so it is not admitted there.

### NL-ACC-13 — A ferry carries what its operator admits `VERIFIED`

No article of the RVV governs who boards a ferry; that is the operator's
condition of carriage. The map's explicit permission for a class is the only
trace of it the graph has, so a `route=ferry` way is open to a class exactly
where `mofa`, `moped` or `motorcar`/`motor_vehicle` says `yes`, `designated`
or `permissive`, and closed where the map is silent. For the IJ ferries the map
agrees with GVB's own rules:

> "Op onze IJ-veerponten mogen voetgangers, (brom)fietsers en
> […] mee."

> "Brommobielen mogen niet mee op onze IJ-veerponten."

> "Op veerpont F9 Sporenburg – Zeeburgereiland zijn alleen voetgangers en
> fietsers toegestaan."

<https://www.gvb.nl/reisinformatie/reisregels-en-voorwaarden>, read 2026-11-13.
The way onto a ferry is decided like any other way: a landing reached only
over a voetpad without an admitting onderbord stays out of reach.

## Signs

| Code | Caption | Meaning for us |
| --- | --- | --- |
| **G1 / G3** | Autosnelweg / Autoweg | Barred to all three: art. 42 admits only motorvoertuigen |
| **G7 / G9** | Voetpad / Ruiterpad | Barred to all three. A confirmed "brom-fietsen toegestaan" onderbord admits the two-wheelers; see NL-ACC-12 |
| **G11** | Verplicht fietspad | Snorfiets yes, bromfiets no. Snorfiets no where an art. 5 lid 8 measure reaches it |
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
| **H1 / H2** | Bebouwde kom begin / einde | Not usable: almost never mapped in OSM. See [Speeds](#speeds) |

An unsigned path is **none** of G11/G12a/G13, because those terms exist only as
sign captions (NL-ACC-03). The country's `unsigned_cycleway` default is
`false` for every class.

`designated`, not `yes`, is how the Netherlands marks a bromfietspad, so an
access table missing `designated` locks bromfietsen out of the cycle network.

## Speeds

RVV arts. 20, 21 and 22. Not the road's signed limit: the limit that binds
*this* vehicle.

> Art. 20: "Binnen de bebouwde kom gelden de volgende maximumsnelheden: …
> b. voor bromfietsen en gehandicaptenvoertuigen, uitgerust met een motor:
> 1. op het fiets/bromfietspad 30 km per uur; 2. op de rijbaan 45 km per uur"

> Art. 21: "Buiten de bebouwde kom gelden de volgende maximumsnelheden: …
> b. voor bromfietsen en gehandicaptenvoertuigen, uitgerust met een motor:
> 1. op het fiets/bromfietspad 40 km per uur; 2. op de rijbaan 45 km per uur"

> Art. 22: "c. voor brommobielen 45 km per uur; d. voor snorfietsen 25 km per
> uur"

> Art. 45: "Bestuurders mogen binnen een erf niet sneller rijden dan 15 km per
> uur."

| Profile | Roadway | Cycle path, built-up | Cycle path, rural |
| --- | --- | --- | --- |
| snorfiets | 25 | 25 | 25 |
| bromfiets | 45 | 30 | 40 |
| brommobiel | 45 | — | — |

A posted limit lower than the class limit binds too: a 30 zone is 30 for a
bromfiets as much as for a car. Inside an *erf* (`highway=living_street`) art.
45 caps every bestuurder at 15.

**The bebouwde kom is not derivable from OpenStreetMap**, which maps almost no
H1 sign. So on a cycle path the built-up figure, 30 rather than 40, is the cap.

Unlike access, a speed is **not** baked into the tiles. It depends on the road
as well as the vehicle, so it is decided per request by whatever serves the
graph, and a speed correction does not need a rebuild. What lives here is the
table itself, as `ClassSpeeds` in the country module.

A consumer applying it should take the country's table as a **required**
argument with no default: substituting one country's limits for another is
exactly the mistake that requirement exists to make impossible. It should also
say when it does not know: where no posted limit is mapped, an unmapped sign may
set one below the class cap, so the cap is not a known limit there. An erf's 15
is known without a sign.

## Authority overlay

`infra/official_access.py` writes six values into the extract, under keys
`amgraph:snorfiets` and `amgraph:bromfiets`. Each has exactly one job.

| Value | Meaning | Where it may appear |
| --- | --- | --- |
| `no` | The class may not be here | Anywhere |
| `on_roadway` | Nothing lawful runs beside this carriageway, so lid 2 keeps it open | Carriageways only |
| `roadway_only` | Art. 5 lid 8: this verplicht fietspad does not admit a snorfiets | Cycle paths, snorfiets key only |
| `yes` | The register says a G12a stands on this unsigned path | Cycle paths, snorfiets key only |
| `footpath_onderbord` | The register's G7 beside this voetpad has an onderbord admitting the class, and the mapper permits it | Footway and pedestrian ways with a mapped G7 |
| `footpath_g12a` | The register confirms the G12a mapped on this voetpad | Footway and pedestrian ways with a mapped G12a |

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

### The sign register

Register cycle signs are matched to OSM ways within 20 m, and only where no
different cycle sign stands within 30 m. What decides the policy is the
direction of a mix-up. A G11/G12a confusion is free for a snorfiets, because
art. 5 lid 1 admits it to both, and opens a verplicht fietspad to a bromfiets,
because G11 bars it and G12a admits it. So the register opens a path for the
snorfiets only, and only on a G12a; a bromfiets gets the rijbaan from art. 6
lid 2 instead.

The register's `validated` field is `n` on every sign, so it is not read.

## Data limitations

| Not handled | Why | Effect on a rider |
| --- | --- | --- |
| Temporary or newly placed restrictions | No verified live closure feed is integrated | The graph cannot know it |
| Mandatory use where OSM and WKD are both silent | OSM states only part of the obligation | A rider may be routed on the carriageway where the sidepath was compulsory |
| A combustion vehicle's year, engine cycle or exemption | Not in the request | Emission-zone municipalities closed conservatively |
| Actual vehicle dimensions, load or trailer | Not in the request | Dimension-controlled ways closed; C10 closes the brommobiel |
| G13 for an electric snorfiets | One access bit, built before powertrain is chosen | Detours. Needs a distinct access class |
| The bebouwde kom | Almost no H1 is mapped | 30 is the cap on a cycle path |
| Untagged cycle paths the register cannot resolve | Ambiguous between opposite answers | Treated as forbidden; longer routes |
| Zeeland / Walcheren | The crossings are motorway, C9 or the Westerscheldetunnel, and whether a lawful moped route exists **has not been established from primary sources** | Middelburg is unreachable for every class |

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
| NDW verkeersborden v4 (open data, no dataset licence named) | The signs actually on the ground | ~1.9M of >3M physical signs; coordinates sometimes mark the photo position; `validated` is `n` on every cycle sign |
| RWS WKD Verkeerstypen and Komgrenzen (CC0) | Per-section class access, i.e. mandatory use, and which sections lie inside the bebouwde kom | NDW warns sign-to-NWB coupling is often wrong; monthly |
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
