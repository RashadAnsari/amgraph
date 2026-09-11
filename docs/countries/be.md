# Belgium rules

Primary sources last reviewed **2026-09-09**. The country modules declare `be-2026-09-09.3`.

[Documentation](../README.md) · [Shared country rules](../country-rules.md) · [Netherlands](nl.md)

Belgium participates in the combined input, audit, build and route gates. A
rider must select a vehicle explicitly because these classes do not have
interchangeable road rights.

## Sources and temporal scope

The quotations below are from the **Koninklijk besluit van 1 december 1975**,
[current consolidated text on Justel][be-code], retrieved **2026-09-09**.
They are statutory text; editorial amendment markers have been omitted from
quotations. Each rule below uses that source and retrieval date unless another
is given explicitly.

The [royal decree of 30 June 2026, art. 58][be-transition], retrieved
**2026-09-09**, amends the future code's commencement:

> In artikel 86 van hetzelfde besluit wordt de datum van "1 september 2026" vervangen door de datum "1 juni 2027".

The implementation therefore uses the 1975 code and the current regional
versions, with an exclusive validity deadline of **2027-06-01**. The ordinary
90-day source-review gate remains stricter. A future code is not selected from
an outdated catalogue end-date field.

## BE-DEF-01 — vehicle scope and carriers

Art. 2.17, 1 defines a bromfiets klasse A with:

> een door de constructie bepaalde maximumsnelheid van 25 km per uur

Art. 2.17, 2(a) defines the two-wheeled klasse B with:

> een door de constructie bepaalde maximumsnelheid van ten hoogste 45 km per uur

Art. 2.17, 2(b) also includes:

> elk drie- of vierwielig voertuig, met uitsluiting van de bromfietsen klasse A

subject to the construction speed, power, mass and seating conditions stated
in that article. The microcar profile is for this four-wheeled klasse B
vehicle, not any vehicle colloquially called a quad.

Art. 2.17, 3 defines the speed pedelec by assistance:

> waarvan de aandrijfkracht wordt onderbroken bij een voertuigsnelheid van maximum 45 km per uur

| Profile | Scope | Carrier | Principal OSM key |
| --- | --- | --- | --- |
| `bromfiets_klasse_a` | Two-wheeled klasse A | `moped` | `mofa` |
| `bromfiets_klasse_b` | Two-wheeled klasse B | `motorcycle` | `moped` |
| `speed_pedelec` | Art. 2.17, 3 | `taxi` | `speed_pedelec` |
| `lichte_vierwieler` | Four-wheeled klasse B | `truck` | `motorcar` |

Three-wheeled vehicles are outside this initial profile set. No bicycle-rule
inheritance is declared: sharing a path with bicycles is not evidence that all
bicycle rules apply. Carrier selection is an implementation decision, not law.
All classes also consult `motor_vehicle` as a less specific access key.
The [OSM moped vocabulary][be-osm-moped] and [Belgian sign tagging][be-osm-signs]
were read on **2026-09-09** for tag semantics only, not as legal authority.
The extract audit evaluates every observed access-tag combination, including
the quad's `motorcar` and `motor_vehicle` keys.

## BE-ACC-01 — motorways and motorroads

Art. 21.1 states “De toegang tot de autosnelwegen is verboden” and includes:

> aan de bestuurders van rijwielen, van bromfietsen en van dieren

Art. 22.1 admits motor vehicles to autowegen:

> met uitzondering van de bromfietsen

The modules close `motorway`, `motorway_link` and `motorroad=yes` for every
declared class, including the four-wheeled klasse B. Access tags cannot lift
these exclusions. F5 and F9 identify the same roads under arts. 2.3 and 2.4
and close them even when the highway classification contradicts the sign.

## BE-ACC-02 — cycle-path permission

Art. 9.1.2, 1:

> Omvat de openbare weg een berijdbaar fietspad, aangeduid door het verkeersbord D7 of D9, dan moeten de fietsers en bestuurders van tweewielige bromfietsen klasse A, dit fietspad volgen, voor zover het in de door hen gevolgde rijrichting is gesignaleerd.

Art. 9.1.2, 2 permits klasse B and speed pedelecs on D7 or marked paths at
50 km/h or less, and makes that use obligatory at higher limits when the path
is present and usable. Its additional D9 permission names speed pedelecs:

> Daarenboven mogen bestuurders van speed pedelecs in dezelfde omstandigheden het fietspad aangeduid door het verkeersbord D9 volgen.

At higher limits it adds:

> Daarenboven moeten bestuurders van speed pedelecs in dezelfde omstandigheden het fietspad aangeduid door het verkeersbord D9 volgen.

Art. 69.3 describes D10 as:

> Deel van de openbare weg voorbehouden voor het verkeer van voetgangers en fietsers.

| Sign | Klasse A (two wheels) | Klasse B (two wheels) | Speed pedelec | Light quadricycle |
| --- | --- | --- | --- | --- |
| D7 | admitted | admitted | admitted | closed |
| D9 | admitted | closed | admitted | closed |
| D10 | closed | closed | closed | closed |

The table describes basic permission, not all supplementary plates or direction
requirements. Its exclusions also close a contradictory highway/access tag.
An unsigned cycleway is unresolved and stays closed without specific access
evidence. A path's own `maxspeed` must never stand in for the adjacent road's
speed when deciding mandatory use. The tests vary it through 30, 50, 70 and 90
and also omit it, with the same permission result.

## BE-ACC-03 — carriageway and mandatory use

Art. 9.1.1:

> Wanneer de openbare weg een rijbaan omvat moeten de bestuurders deze rijbaan volgen.

Art. 9.1.2, 2 distinguishes “mogen” at 50 km/h or less from “moeten” above
that threshold, for a path “wanneer dit aanwezig en bruikbaar is.”
The module respects class-specific `use_sidepath`. The Belgian enrichment
indexes only cycle edges that its own access rules admit, and matches parallel
nearby geometry before deriving a roadway closure. Klasse A and an explicit
mandatory subplate create an obligation; for B and pedelecs, an unknown adjacent
road speed takes the above-50 branch only when a usable path is established.
The path's own speed never supplies the roadway threshold. Dutch WKD evidence
is not used to decide Belgian obligations.

`amgraph:sidepaths` retains the matched way IDs. Unknown or already closed
cycle edges cannot supply this evidence. This is a geometric approximation,
not an official Belgian road-by-road mandatory-use register; missing or
incorrect source topology remains a limitation of the routing claim.

## BE-ACC-04 — prohibition signs

Art. 68.3:

| Sign | Verbatim meaning | Graph handling |
| --- | --- | --- |
| C1 | “Verboden richting voor iedere bestuurder” | Close the signed direction; unscoped closes both |
| C3 | “Verboden toegang, in beide richtingen, voor ieder bestuurder” | Close every class |
| C5 | “Verboden toegang voor bestuurders van motorvoertuigen met meer dan twee wielen en van motorfietsen met zijspan” | Close the quad |
| C9 | “Verboden toegang voor bestuurders van bromfietsen” | Close every declared class |

Supplementary exceptions are not used to open these prohibitions. A sign-only
exception can therefore lose a lawful route. Unknown sign codes or unparsed
suffixes close access instead of being ignored.

## BE-SPD-01 — vehicle caps are not complete road limits

Art. 11.3, 4 and 5 limit klasse B to “45” km/h and klasse A to “25 km per uur”.
The Python definitions carry 25 and 45 as vehicle caps. A speed pedelec's 45
comes from the assistance cut-off in BE-DEF-01 and is an operational cap,
not a claim that art. 11.3 imposes that absolute riding limit on it.

The Walloon version of art. 11.1 says:

> De snelheid is beperkt tot 30 km/u op de voor voetgangers en fietsers bestemde gedeelten van de openbare weg, aangeduid met het sein D9 of D10.

The cycle-path caps are conservatively 25 for klasse A and 30 for klasse B and
pedelecs; the quad has no cycle-path speed. Regional and signed lower limits
are handled by BE-SPD-02.

## BE-SPD-02 — road, zone and signed limits

Brussels art. 11.1 states “30 km/u” as the built-up-area default. The Flemish
and Walloon versions of art. 11.1 state “50 km per uur” there. The graph uses
30 when no numeric limit is mapped, with these lower/special-zone constraints:

| Article | Verbatim provision | Handling |
| --- | --- | --- |
| 22bis, 3° | “is de snelheid beperkt tot 20 km per uur” | Living streets/F12a: 20 |
| 22ter.1, 1° | “met een snelheid die niet meer bedraagt dan 30 km per uur” | Raised traffic calming/A14/F87: at most 30 |
| 22quater | “Binnen de zones afgebakend door de verkeersborden F 4a en F 4b is de snelheid beperkt tot 30 km per uur.” | F4a: at most 30 |
| 22novies | “nooit hoger liggen dan 30 kilometer per uur” | Cycle zones/F111: at most 30 |
| 68.3, C43 | “verbod te rijden met een grotere snelheid dan deze die is aangeduid.” | Parse the numeric value; unresolved values close the way |

The regional hints `BE-BRU:urban`, `BE-VLG:urban` and `BE-WAL:urban`
use those respective urban limits. Regional rural and dual-carriageway hints
use a conservative 70 cap: Brussels and Flemish art. 11.2 include “70”
for other roads, while Walloon art. 11.2 includes “90” and its middle
carriageways are limited to “70”. These are read in the regional versions of
[the same decree][be-code], retrieved 2026-09-09. Numeric `zone30`/`zone:30`
variants are interpreted as their mapped limit; living-street and cycle-street
hints use the cited special-zone limits above.

Mapped lower numeric and directional limits remain binding. Numeric implicit
zone tags cannot be replaced with a faster default. Unknown speed hints and
conditional values close access. Belgian A1 is not interpreted as Dutch A1.
The 30 default is a conservative choice among researched statutory defaults,
not evidence that an unmapped lower sign does not exist.

## BE-ACC-05 — supplementary cycle-path plates

Art. 69.4, 2° says D7/M6 applies “wanneer het fietspad moet gevolgd worden door
de bestuurders van tweewielige bromfietsen klasse B”; 3° uses “niet mag gevolgd
worden” for D7/M7. Paragraphs 4°–7° state:

> het fietspad moet gevolgd worden door de bestuurders van speed pedelecs

for M13, and extend the mandatory classes to B and pedelecs for M14. M15 says:

> het fietspad niet mag gevolgd worden door de bestuurders van speed pedelecs

M16 extends that prohibition to B and pedelecs. The enrichment records the
mandatory cases; Lua enforces the prohibitions even against generic access=yes.

## BE-ACC-06 — reserved infrastructure

Art. 22quinquies.1 permits only the categories whose symbol appears:

> Op deze wegen is alleen het verkeer toegestaan van de categorieën van weggebruikers waarvan het symbool afgebeeld is op de verkeersborden die bij de toegang geplaatst zijn.

F99a/b/c alone does not establish all pictured categories. These unresolved
roads stay closed. Art. 69.3 calls D11 “Verplichte weg voor voetgangers” and
D13 “Verplichte weg voor ruiters”; neither gives an AM profile access.
Art. 22sexies.1 says pedestrian zones admit “alleen voetgangers”, subject to
listed exceptions that the graph does not assume. F103 therefore closes access.
Art. 71.2 describes F17 as “een strook voorbehouden voor autobussen” and F18 as
“voorbehouden aan het verkeer van voertuigen van geregelde diensten voor
gemeenschappelijk vervoer”. An unresolved F17/F18 way cannot borrow taxi
permission; closing the whole way can lose a legal adjacent ordinary lane.

## BE-ACC-07 — movement restrictions

Art. 69.3 calls D1 “Verplichting de door de pijl aangeduide richting te volgen”
and D3 “Verplichting een van de door de pijlen aangeduide richtingen te volgen”.
Art. 68.3 C31 prohibits the pictured turn; C33 states “Vanaf het verkeersbord
tot en met het volgend kruispunt, verbod te keren.” Unresolved way-level movements
close the edge. These are not entry bans and do not close an entire junction.
OSM turn relations are normalized for every borrowed carrier. An uninterpretable
relation closes its incident ways before the unusable relation is excluded.

## BE-ACC-08 — dimensions, freight and dangerous goods

Art. 68.3 C21 refers to vehicles whose “massa in beladen toestand hoger is dan
de aangeduide massa”; C23 to vehicles “bestemd of gebruikt voor het vervoer
van zaken”. C25/C27/C29 limit length/width/height. C24a/b/c distinguish dangerous,
flammable/explosive and water-polluting cargo. These properties are not fully
represented by the profile selection, so the signed ways stay closed rather
than guessing a cargo or dimension exemption.

## BE-LEZ-01 — powertrain-dependent zones

[Brussels decree of 25 January 2018, art. 5 §1, 1°][be-lez], retrieved
**2026-09-09**, admits zero-emission vehicles:

> de gemotoriseerde voertuigen waarvan de motor geen luchtverontreinigende stoffen uitstoot, zoals elektrische voertuigen en de voertuigen die werken op waterstof

The §1, 3° access tables distinguish diesel, petrol, Euro standard and L vehicle
category; from 2025 the L-category diesel entries state “Verboden”. The package
knows combustion versus electric, so it conservatively refuses combustion
throughout the official Brussels-Capital Region boundary. This over-approximates
both the zone and the affected vehicles; it does not claim every petrol moped
is legally forbidden. Consumers must apply the packaged zone to complete route
geometry. The graph itself does not encode fuel type.

The [Flemish LEZ decree, art. 2][be-flemish-lez], retrieved **2026-09-09**,
admits “de motorvoertuigen die niet behoren tot de motorvoertuigen van categorie
M, N of T”. The [Walloon decree of 17 January 2019, art. 4 §1, 1°][be-walloon-lez],
retrieved **2026-09-09**, admits “véhicules qui n'appartiennent pas aux catégories
M et N”. These provisions do not impose an L-category emission closure.

## BE-BOUND-01 — official geographic evidence

The [NGI administrative-vector metadata][be-boundaries], retrieved
**2026-09-09**, identifies the official national and regional boundary export
and its WGS84 download. The national feature must identify `01000`/`België`;
the Brussels regional feature must identify `04000`. Invalid polygons abort
rather than being repaired into different territory. The merger attributes
both roads and junctions from these polygons and the other supported countries'
official boundaries and applies every intersecting country’s rules.

The NGI export is licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The ZIP preserves attribution in `NOTICE.md` and records derived country and
zone polygons in the manifest.

## BE-PLATE-01 — plate presentation

[Ministerieel besluit van 23 juli 2001, art. 19 §1][be-plates], retrieved
**2026-09-09**:

> De gewone kentekenplaat heeft een witte achtergrond. Het opschrift en de boord zijn robijnrood (RAL 3003).

The Python colour pair is a screen approximation of ruby red on white, not a
statutory sRGB value or a measured physical plate sample. `Plate` measures its
contrast against the existing 3:1 minimum. Colour carries no access decision.
Powertrain remains an explicit vehicle fact for every profile because of
BE-LEZ-01.

[be-code]: https://www.ejustice.just.fgov.be/cgi_loi/change_lg.pl?cn=1975120131&la=N&language=nl&table_name=wet
[be-transition]: https://www.ejustice.just.fgov.be/cgi_loi/article.pl?language=nl&lg_txt=n&cn_search=2026063009
[be-plates]: https://www.ejustice.just.fgov.be/eli/besluit/2001/07/23/2001014154/justel
[be-osm-moped]: https://wiki.openstreetmap.org/wiki/Key:moped
[be-osm-signs]: https://wiki.openstreetmap.org/wiki/Road_signs_in_Belgium/D_Mandatory_signs

[be-lez]: https://www.ejustice.just.fgov.be/eli/besluit/2018/01/25/2018030279/justel
[be-flemish-lez]: https://codex.vlaanderen.be/PrintDocument.ashx?geannoteerd=true&id=1026568
[be-walloon-lez]: https://wallex.wallonie.be/eli/loi-decret/2019/01/17/2019200758/2024/09/26
[be-boundaries]: https://publish.geo.be/geonetwork/srv/api/records/fb1e2993-2020-428c-9188-eb5f75e284b9/formatters/xml