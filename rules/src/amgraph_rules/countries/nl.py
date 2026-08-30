"""The Netherlands: every rule this package carries, in one file.

Adding a country means adding a module beside this one and naming it in
``__init__``. Nothing above this package needs to change, and a client that
reads the registry rather than hard-coding a country picks the new one up
without a release of its own.

What lives here is the country's law, including which vehicle classes exist,
what they are called in each language, what they may do and which Valhalla
carrier each borrows. The *mechanisms* that apply it are country-agnostic and
live elsewhere: a speed lookup takes a class's limits as an argument rather
than knowing them, ``profiles`` knows only how a carrier reaches Valhalla, and
the graph's own access rules are the matching Lua
in ``valhalla/lua/countries/nl.lua``. That Lua and this module are the
two halves of the same law and are expected to be edited together — in
particular the ``carrier`` of each class below must match the ``carrier`` of the
class of the same name there, which AGENTS.md records as the one failure in this
codebase that does not announce itself.

Every rule cites the article it comes from; the quotes and retrieval dates are
in ``docs/rules.md``, which is the source of truth.
"""

from __future__ import annotations

from datetime import date

from amgraph_rules.profiles import Carrier, Powertrain
from amgraph_rules.rules import (
    BoundaryDocument,
    ClassSpeeds,
    CountryRules,
    MunicipalZone,
    Plate,
    SearchBounds,
    VehicleClass,
)

#: The two Dutch plates. Kenteken- en registratiebesluit: a snorfiets carries a
#: blue plate and everything else in the family a yellow one, which is how the
#: police tell them apart at a glance and exactly what decides which roads the
#: rider may use.
#:
#: The hexes are measured values, not eyeballed ones, and they belong here
#: because the plate is a fact of Dutch law rather than a palette choice.
#: `Plate` refuses a pair whose own ink does not read on it, which is the half
#: of the check that can be made here. The other half belongs to whoever draws
#: it, against surfaces this package cannot see: a colour that fails there is
#: quietly replaced by a fallback, so a change to either hex should be measured
#: against the real background before it is committed.
_YELLOW = Plate(background="#F2C200", foreground="#0A0C0D")
_BLUE = Plate(background="#1256B8", foreground="#FAFAF8")

#: Bump on any change below. Kept internally rather than served, so the legal
#: freshness gate can force a periodic re-read of the primary sources without
#: the string reading to a rider as a build number.
RULES_VERSION = "nl-2026-08-16"

#: The four vehicles a Dutch rider can pick, riding three access classes.
#:
#: Three classes rather than four because RVV art. 6 sends a bromfiets and a
#: speed pedelec to exactly the same places, so they share the motorcycle
#: carrier and route identically. They stay two entries because a rider on a
#: speed pedelec should be able to say so: the plate and the drawing differ even
#: though the roads do not. In the Lua the speed pedelec is a `closing_keys`
#: entry on the bromfiets class, which may shut the shared carrier but never
#: open it.
#:
#: The English is a description rather than a translation: there is no English
#: word for a snorfiets, and "light moped" is what a rider will recognise. The
#: identifiers stay Dutch because they are the statutory terms the rules in
#: docs/rules.md are written against, and a translated one would put guesswork
#: between the code and the law.
#:
#: Speeds are RVV 1990 art. 20, 21 and 22, quoted in docs/rules.md §7. A
#: snorfiets and a brommobiel carry a single construction-limit cap everywhere
#: (art. 22); the other two follow the road. ``None`` means the class may not be
#: on a cycle path at all, so no cycle-path speed applies.
CLASSES: tuple[VehicleClass, ...] = (
    VehicleClass(
        code="snorfiets",
        carrier=Carrier.MOPED,
        construction_limit_kph=25,
        speeds=ClassSpeeds(roadway=25, cycle_path_built_up=25, cycle_path_rural=25),
        plate=_BLUE,
        marker="scooter",
        powertrain_matters=True,
        names={"en": "Light moped", "nl": "Snorfiets"},
    ),
    VehicleClass(
        code="bromfiets",
        carrier=Carrier.MOTORCYCLE,
        construction_limit_kph=45,
        speeds=ClassSpeeds(roadway=45, cycle_path_built_up=30, cycle_path_rural=40),
        plate=_YELLOW,
        marker="scooter",
        powertrain_matters=True,
        names={"en": "Moped", "nl": "Bromfiets"},
    ),
    VehicleClass(
        code="speed_pedelec",
        carrier=Carrier.MOTORCYCLE,
        construction_limit_kph=45,
        speeds=ClassSpeeds(roadway=45, cycle_path_built_up=30, cycle_path_rural=40),
        plate=_YELLOW,
        marker="pedelec",
        powertrain_matters=False,
        names={"en": "Speed pedelec", "nl": "Speed pedelec"},
    ),
    VehicleClass(
        code="brommobiel",
        carrier=Carrier.TRUCK,
        construction_limit_kph=45,
        speeds=ClassSpeeds(roadway=45, cycle_path_built_up=None, cycle_path_rural=None),
        plate=_YELLOW,
        marker="microcar",
        powertrain_matters=False,
        names={"en": "Microcar", "nl": "Brommobiel"},
    ),
)

#: The most restricted of the four on the cycle network: a bromfiets may use a
#: G12a and nothing else. See docs/rules.md §5 NL-ACC-02 and CountryRules.
DEFAULT_CLASS = "bromfiets"

_EMISSION_TWO_WHEELERS = frozenset({"snorfiets", "bromfiets", "speed_pedelec"})

#: Municipal rules that turn on a vehicle fact the request does not carry.
#:
#: These are emission zones and nothing else. The request states a powertrain
#: but not a date of first registration or an engine cycle, so for a combustion
#: two-wheeler the only claim the API can prove is "outside the affected
#: municipality". Each is therefore closed as a whole, which is **stricter than
#: the by-law** in every case below and can only refuse a lawful trip, never
#: permit an unlawful one.
#:
#: How much stricter, so the cost is on the record rather than implied:
#:
#: - **Den Haag** bars a DET before 2011-01-01, but only a *two-stroke* one.
#:   "Heeft u een 4-takt brommer of 4-takt snorfiets met een DET van vóór
#:   1 januari 2011? Dan mag u in de milieuzone rijden." Old *electric* mopeds
#:   and brommobielen are admitted outright. Retrieved 2026-08-15 from
#:   <https://www.denhaag.nl/nl/verkeer-en-vervoer/milieuzone-oude-brom-en-snorfietsen/>
#: - **Nijmegen** bars a build year of 2010 or older in *three areas* rather
#:   than the municipality: Nijmegen centrum, Hof van Holland and Heijendaal.
#:   Its 2028 step ("bouwjaar van 2018 of ouder … niet in de bebouwde kom") and
#:   its 2030 step (electric only) both tighten inside an area this table
#:   already closes, so neither needs a dated entry. Retrieved 2026-08-15 from
#:   <https://www.nijmegen.nl/over-de-gemeente/plannen/milieuzone-bromfietsen/>
#: - **Amsterdam** has a current brom- and snorfiets milieuzone, listed in the
#:   national index at <https://www.milieuzones.nl/locaties-milieuzones>,
#:   retrieved 2026-08-15.
#:
#: The Amsterdam and Utrecht snorfiets place-on-road rule (art. 5 lid 8) is not
#: an emission rule and gates nothing here. It is a rule about which edge a
#: rider belongs on, so it is carried as `roadway_only_classes` and applied per
#: edge at graph build time. See docs/rules.md §5 NL-ACC-04.
MUNICIPAL_ZONES: dict[str, MunicipalZone] = {
    "Amsterdam": MunicipalZone(
        municipality_id="GM0363",
        powertrain_classes=_EMISSION_TWO_WHEELERS,
        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
        blocked_classes=frozenset(),
        roadway_only_classes=frozenset({"snorfiets"}),
    ),
    "Den Haag": MunicipalZone(
        municipality_id="GM0518",
        powertrain_classes=_EMISSION_TWO_WHEELERS,
        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
        blocked_classes=frozenset(),
    ),
    "Nijmegen": MunicipalZone(
        municipality_id="GM0268",
        powertrain_classes=_EMISSION_TWO_WHEELERS,
        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
        blocked_classes=frozenset(),
    ),
    # Utrecht's emission rule is announced and dated, not yet in force. Until
    # 2028-01-01 this entry gates nothing and the municipality is carried here
    # only for its art. 5 lid 8 polygon; on that date it starts refusing
    # combustion two-wheelers like the other three.
    #
    #   "Vanaf 1 januari 2028 mogen brom- en snorfietsen op benzine, diesel of
    #    gas met een datum eerste toelating (DET) tot en met 31-12-2017 niet
    #    meer in Utrecht rijden."
    #   "De regels gelden voor heel de gemeente Utrecht."
    #   "Vanaf 2030 moeten alle brom- en snorfietsen in heel Utrecht
    #    uitstootvrij zijn."
    #
    # Retrieved 2026-08-15 from <https://www.utrecht.nl/wonen-en-leven/
    # gezonde-leefomgeving/luchtkwaliteit/brom-en-snorfietsen-uitstootvrij>.
    #
    # Writing it down now rather than remembering it in 2028 is the whole point
    # of `valid_from`. The 2030 step tightens inside what this already refuses,
    # so it needs no second entry. Brommobielen are deliberately absent: the
    # same page says they "mogen waarschijnlijk in Utrecht blijven rijden" with
    # a decision due in 2026, and a rule that is still being decided is not one
    # this router may act on.
    "Utrecht": MunicipalZone(
        municipality_id="GM0344",
        powertrain_classes=_EMISSION_TWO_WHEELERS,
        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
        blocked_classes=frozenset(),
        roadway_only_classes=frozenset({"snorfiets"}),
        valid_from=date(2028, 1, 1),
    ),
}

#: A rectangle around the European Netherlands, for the PDOK Locatieserver.
#: Wide enough to include Antwerp and a strip of Germany, which is why the
#: app also refuses a reverse-geocode further than 250 m from the pin.
ADDRESS_SEARCH_BOUNDS = SearchBounds(south=50.74, north=53.60, west=3.20, east=7.23)

#: The single land area in the Kadaster's BRK bestuurlijke gebieden export.
#: Named here rather than in supported_area.py so that a second country brings
#: its own authority's identifiers with it instead of editing shared code.
BOUNDARY = BoundaryDocument(properties={"identificatie": "LND6030", "naam": "Nederland"})

NETHERLANDS = CountryRules(
    code="NL",
    name="Netherlands",
    classes=CLASSES,
    default_class=DEFAULT_CLASS,
    municipal_zones=MUNICIPAL_ZONES,
    address_search_bounds=ADDRESS_SEARCH_BOUNDS,
    boundary=BOUNDARY,
    rules_version=RULES_VERSION,
    source="RVV 1990, cited per rule in docs/rules.md",
)
