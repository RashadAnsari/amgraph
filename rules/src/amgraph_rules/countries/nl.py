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
in ``docs/countries/nl.md``, which is the source of truth.
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
#: quietly replaced by one the client has measured, so a change to either hex
#: should be measured against the real background before it is committed.
_YELLOW = Plate(background="#F2C200", foreground="#0A0C0D")
_BLUE = Plate(background="#1256B8", foreground="#FAFAF8")

#: Bump on any change below. Kept internally rather than served, so the legal
#: freshness gate can force a periodic re-read of the primary sources without
#: the string reading to a rider as a build number.
RULES_VERSION = "nl-2026-11-14.2"

#: Separate carriers keep each vehicle identity stable across country boundaries.
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

#: The most restricted on the cycle network: a bromfiets may use a G12a and
#: nothing else. See docs/countries/nl.md NL-ACC-02 and CountryRules.
DEFAULT_CLASS = "bromfiets"

_EMISSION_CLASSES = frozenset({"snorfiets", "bromfiets"})

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
#: - **Den Haag** bars a DET before 2011-01-01 in the whole municipality: "U
#:   mag met een brom- of snorfiets van vóór 1 januari 2011 niet in de
#:   milieuzone rijden. Met oude elektrische brom- en snorfietsen en met
#:   brommobielen mag dit wel." A pre-2011 four-stroke may ride after an
#:   inspection and with an ontheffing. Read 2026-11-14 from
#:   <https://www.denhaag.nl/nl/verkeer-en-vervoer/milieuzone-oude-brom-en-snorfietsen/>
#: - **Nijmegen** bars a build year of 2010 or older in *three areas* rather
#:   than the municipality: Nijmegen centrum, Hof van Holland and Heijendaal.
#:   Its 2028 step ("bouwjaar van 2018 of ouder … niet in de bebouwde kom") and
#:   its 2030 step (electric only) both tighten inside an area this table
#:   already closes, so neither needs a dated entry. Read 2026-11-14 from
#:   <https://www.nijmegen.nl/verkeer-en-vervoer/milieuzone-bromfietsen/>
#: - **Amsterdam** has a current brom- and snorfiets milieuzone, listed in the
#:   national index at <https://www.milieuzones.nl/locaties-milieuzones>,
#:   read 2026-11-14.
#:
#: The Amsterdam and Utrecht snorfiets place-on-road rule (art. 5 lid 8) is not
#: an emission rule and gates nothing here. It is a rule about which edge a
#: rider belongs on, so it is carried as `roadway_only_classes` and applied per
#: edge at graph build time. See docs/countries/nl.md NL-ACC-04.
MUNICIPAL_ZONES: dict[str, MunicipalZone] = {
    "Amsterdam": MunicipalZone(
        municipality_id="GM0363",
        powertrain_classes=_EMISSION_CLASSES,
        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
        blocked_classes=frozenset(),
        roadway_only_classes=frozenset({"snorfiets"}),
    ),
    "Den Haag": MunicipalZone(
        municipality_id="GM0518",
        powertrain_classes=_EMISSION_CLASSES,
        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
        blocked_classes=frozenset(),
    ),
    "Nijmegen": MunicipalZone(
        municipality_id="GM0268",
        powertrain_classes=_EMISSION_CLASSES,
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
    # Read 2026-11-14 from <https://www.utrecht.nl/wonen-en-leven/
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
        powertrain_classes=_EMISSION_CLASSES,
        allowed_powertrains=frozenset({Powertrain.ELECTRIC}),
        blocked_classes=frozenset(),
        roadway_only_classes=frozenset({"snorfiets"}),
        valid_from=date(2028, 1, 1),
    ),
}

_AMSTERDAM = (52.27, 4.72, 52.44, 5.08)
_UTRECHT = (52.02, 4.97, 52.15, 5.20)

#: Roads whose bike paths a municipality's art. 5 lid 8 measure does not reach,
#: as (name, (south, west, north, east)), for the municipalities whose measure
#: the graph applies to their whole territory.
#:
#: Amsterdam. Stcrt. 2018, 71559, p. 8: "op de
#: belangrijkste doorstromingswegen voor auto en voor openbaar vervoer wordt de
#: maatregel voorlopig niet ingevoerd", and Gmb. 2025, 474758 restates it as
#: "met uitzondering van de De Ruijterkade". A snorfiets keeps art. 5 lid 1
#: there: the G11 admits it and obliges it. Both read 2026-11-13.
#:
#: Kattenburgerstraat is on the 2018 list and is not here: Gmb. 2023, 51567
#: put the onderbord on it ("snorfietsen op de hoofdrijbaan moeten rijden op de
#: Kattenburgerstraat"). Prins Hendrikkade is listed only "tussen Centraal
#: Station en IJ-tunnel" and "tussen IJ-tunnel en Kattenburgerstraat", so its
#: box starts east of the station and ends at Kattenburgerplein. The two
#: tunnels on the list carry no bike path and are left out. A search of every
#: later Amsterdam verkeersbesluit naming these roads found no other onderbord,
#: and a register plate naming snorfietsen on a G11 still overrides this list.
ART5_LID8_EXEMPT_ROADS: tuple[tuple[str, tuple[float, float, float, float]], ...] = (
    ("Prins Hendrikkade", (52.3700, 4.9025, 52.3770, 4.9160)),
    *(
        (name, _AMSTERDAM)
        for name in (
            "Nieuwe Leeuwarderweg",
            "Valkenburgerstraat",
            "Weesperstraat",
            "Wibautstraat",
            "Gooiseweg",
            "Transformatorweg",
            "Spaarndammerdijk",
            "Tasmanstraat",
            "Van Diemenstraat",
            "Westerdoksdijk",
            "De Ruijterkade",
            "Piet Heinkade",
            "IJburglaan",
            "Houtmankade",
            "Nassaukade",
            "Stadhouderskade",
            "Mauritskade",
            "Zeeburgerdijk",
            "Panamalaan",
            "Schellingwouderbrug",
            "Amsterdamsebrug",
        )
    ),
)

#: Utrecht's art. 5 lid 8 measure, which names every road it reaches rather than
#: taking the municipality: Gmb. 2021, 212045 lists "de volgende locaties waar
#: een verplicht fietspad aanwezig is", and the onderbord stands only there.
#: Later decisions put it on Biltstraat (Gmb. 2022, 579834), Vleutenseweg (Gmb.
#: 2022, 415248 and others), Jutfaseweg (Gmb. 2024, 210227), Paardenveld (Gmb.
#: 2025, 410033) and Croeselaan (Gmb. 2026, 309624). All read 2026-11-13. The
#: list's solitary paths have no street of their own, so an unnamed G11 stays
#: closed to the snorfiets unless it runs beside a road the decision does not
#: name, where art. 5 lid 1 puts the snorfiets on it. A register or mapped
#: onderbord closes any other G11 as well.
ART5_LID8_LISTED: dict[str, tuple[tuple[float, float, float, float], frozenset[str]]] = {
    "Utrecht": (
        _UTRECHT,
        frozenset(
            {
                "Amsterdamsestraatweg",
                "Catharijnesingel",
                "Daalsesingel",
                "Bleekstraat",
                "Vondellaan",
                "Ledig Erf",
                "Tolsteegsingel",
                "Royaards van den Hamkade",
                "Ahornstraat",
                "Nijenoord",
                "Omloop",
                "Anton Geesinkstraat",
                "Oudenoord",
                "Laan van Chartroise",
                "Sint-Jacobsstraat",
                "St.-Jacobsstraat",
                "Weerdsingel W.Z.",
                "Weerdsingel Westzijde",
                "Blauwkapelseweg",
                "Kleine Singel",
                "Biltstraat",
                "Kruisstraat",
                "Nobelstraat",
                "Vredenburg",
                "Lange Viestraat",
                "Potterstraat",
                "Neude",
                "Lange Jansstraat",
                "Janskerkhof",
                "Van Sijpesteijnkade",
                "Daalsetunnel",
                "Westplein",
                "Vleutenseweg",
                "Graadt van Roggenweg",
                "Croeselaan",
                "Van Zijstweg",
                "Rijnlaan",
                "Balijelaan",
                "Waalstraat",
                "Jutfaseweg",
                "Baden-Powellweg",
                "W.A. Vultostraat",
                "Constant Erzeijstraat",
                "Briljantlaan",
                "Burgemeester Fockema Andreaelaan",
                "Jacob Westerbaenstraat",
                "Laan van Kovelswade",
                "Laan van Soestbergen",
                "Oosterkade",
                "Oosterspoorbaan",
                "Neptunusstraat",
                "Mesdaglaan",
                "Veeartsenijpad",
                "Hoveniersbrug",
                "Lauwerecht",
                "Timmerstraat",
                "Moreelsebrug",
                "Van Sijpesteijntunnel",
                "Catharijnekade",
                "Wolvenstraat",
                "Westerkade",
                "Paardenveld",
            }
        ),
    ),
}

#: A rectangle around the European Netherlands, for the PDOK Locatieserver.
#: Wide enough to include Antwerp and a strip of Germany, which is why the
#: app also refuses a reverse-geocode further than 250 m from the pin.
ADDRESS_SEARCH_BOUNDS = SearchBounds(south=50.74, north=53.60, west=3.20, east=7.23)

#: The single land area in the Kadaster's BRK bestuurlijke gebieden export.
#: Named here rather than in supported_area.py so that each country brings
#: its own authority's identifiers with it instead of editing shared code.
BOUNDARY = BoundaryDocument(
    properties={"identificatie": "LND6030", "naam": "Nederland"}, geocoder="pdok"
)

NETHERLANDS = CountryRules(
    code="NL",
    name="Netherlands",
    classes=CLASSES,
    default_class=DEFAULT_CLASS,
    municipal_zones=MUNICIPAL_ZONES,
    address_search_bounds=ADDRESS_SEARCH_BOUNDS,
    boundary=BOUNDARY,
    rules_version=RULES_VERSION,
    source="RVV 1990, cited per rule in docs/countries/nl.md",
)


EXTRACT_URL = "https://download.geofabrik.de/europe/netherlands-latest.osm.pbf"
BOUNDARY_FILENAME = "netherlands.geojson"
PREPARE_TARGETS = ("extract", "official-data", "official-access")
AUDIT_TESTS = ("tests/test_access_rules.py", "tests/test_official_overlay.py")
SOURCE_RELEASE_FILES = {"wkd_release": "wkd-release.txt"}

ROUTE_CHECKS = (
    ((52.0907, 5.1214), (52.0800, 5.1300)),
    ((52.3650, 4.9000), (52.3750, 4.9150)),
    ((51.9220, 4.4790), (51.9320, 4.4890)),
    ((52.0700, 4.3000), (52.0800, 4.3150)),
    ((51.4400, 5.4800), (51.4500, 5.4900)),
    ((50.8500, 5.6900), (50.8600, 5.7000)),
    ((52.5100, 6.0950), (52.5200, 6.1100)),
    ((53.2150, 6.5600), (53.2250, 6.5800)),
    ((51.9850, 5.9150), (51.9950, 5.9300)),
    ((53.2000, 5.7900), (53.2100, 5.8050)),
)

# Routes every class must answer, where ROUTE_CHECKS only asks 80% of them.
# These two cities are where RVV art. 5 lid 8 moves the snorfiets onto the
# rijbaan (NL-ACC-04), and a deadlock there leaves the other fixtures
# untouched.
REQUIRED_ROUTE_CHECKS = (
    ((52.3390, 4.8730), (52.3791, 4.9003)),  # Amsterdam Zuid to Centraal
    ((52.1160, 5.1080), (52.0894, 5.1100)),  # Utrecht Overvecht to Centraal
    ((52.0894, 5.1100), (52.3791, 4.9003)),  # Utrecht Centraal to Amsterdam Centraal
)

ACCESS_PROBES = (
    ("snorfiets", "bromfiets"),
    ("bromfiets", "brommobiel"),
)
