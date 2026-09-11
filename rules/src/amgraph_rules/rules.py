"""The shapes a country's rules are written in.

Types only, and deliberately no data: every value lives in a country module
under ``countries/``. Splitting them this way is what makes "add a country" a
matter of adding one file rather than editing five.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from amgraph_rules.profiles import Carrier, Powertrain

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _relative_luminance(colour: str) -> float:
    """WCAG 2.2 relative luminance of an ``#RRGGBB`` colour."""

    def channel(byte: int) -> float:
        value = byte / 255
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4

    red, green, blue = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * channel(red) + 0.7152 * channel(green) + 0.0722 * channel(blue)


def contrast_ratio(one: str, two: str) -> float:
    """WCAG 2.2 contrast between two ``#RRGGBB`` colours, 1.0 to 21.0."""
    first, second = _relative_luminance(one), _relative_luminance(two)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


@dataclass(frozen=True)
class Plate:
    """The licence plate a class carries, as the two colours it is made of.

    Colours rather than a key into a palette a client happened to ship, because
    the plate is a statutory fact of the country and not a palette choice: a
    country introducing a different combination would otherwise need a client
    release before it could be drawn correctly.

    Serving a colour does not mean choosing one by eye, which is a standing rule
    here. The pair below is checked on the way out: a plate whose own ink does
    not read on it is refused at import, so a country module cannot be
    registered carrying one. That is only half the check, because contrast is a
    property of a pair against a surface and only the client drawing it knows
    its surfaces. A client is expected to measure what it receives against its
    own chrome and text thresholds and substitute a plate it has measured when
    one fails, so a colour reaches a rider only after somebody has measured it.
    """

    #: The plate face, as ``#RRGGBB``.
    background: str

    #: The characters on it, and every piece of text drawn on the plate.
    foreground: str

    def __post_init__(self) -> None:
        for role, colour in (("background", self.background), ("foreground", self.foreground)):
            if not _HEX.match(colour):
                raise ValueError(f"plate {role} {colour!r} is not an #RRGGBB colour")
        # 3:1 is the WCAG 2.2 bar for large text, which is what the plate
        # carries: the instruction, the speed and the class name are all set
        # large and heavy. A client that measures would refuse such a pair
        # anyway; failing at import names the country module instead.
        measured = contrast_ratio(self.foreground, self.background)
        if measured < 3:
            raise ValueError(
                f"plate ink {self.foreground} measures {measured:.2f}:1 on "
                f"{self.background}, below the 3:1 a rider needs at speed"
            )


@dataclass(frozen=True)
class ClassSpeeds:
    """Legal maxima for one vehicle class, in km/h.

    ``None`` means the class may not be on a cycle path at all, so no
    cycle-path speed applies to it.
    """

    roadway: int
    cycle_path_built_up: int | None
    cycle_path_rural: int | None


@dataclass(frozen=True)
class VehicleClass:
    """A vehicle a rider can pick, and the access class it rides on.

    Each class names the carrier its country writes into the combined graph.
    A vehicle crossing a supported border must retain that carrier; matching
    rights within one country are not enough to merge identities that another
    country's law distinguishes.

    ``code`` is the identifier a client stores and sends back. It is a statutory
    term in the country's own language — ``snorfiets``, not ``light_moped`` —
    because the rules in ``docs/countries/<cc>.md`` are written against those words and a
    translated identifier would put guesswork between the code and the law.

    ``plate`` carries the country's own colours; see :class:`Plate` for why they
    are values rather than a key. ``marker`` stays a **key**, because it names a
    glyph rather than carrying one, and a drawing cannot be sent. A country whose
    classes need a shape a client does not have gets the nearest one it does,
    which costs an icon beside a name and a speed that both say what the class
    is. Nothing legal is carried by the drawing.
    """

    code: str
    carrier: Carrier

    #: What the plate on the back announces, in km/h.
    construction_limit_kph: int

    speeds: ClassSpeeds

    plate: Plate

    #: Which glyph stands for the class in a list: "scooter", "pedelec",
    #: "microcar", "motorcycle" or "bicycle". A key into a client's own shapes.
    marker: str

    #: Whether electric or combustion changes where this class may legally ride.
    powertrain_matters: bool

    #: What a rider calls it, by language tag. English is required, because it
    #: is what any language a client does not ship falls back to.
    names: Mapping[str, str]

    def name(self, language: str) -> str:
        return self.names.get(language) or self.names["en"]


@dataclass(frozen=True)
class MunicipalZone:
    """A municipality with a rule of its own that the national rules do not carry.

    ``powertrain_classes`` are the class codes an emission rule reaches, and
    ``allowed_powertrains`` the powertrains it lets through. ``blocked_classes``
    refuses a class outright, which is the heaviest gate available and is for
    rules that cannot be expressed on an edge at all.

    All three may be empty, and that is a real state rather than a mistake: a
    municipality can appear here purely to carry its polygon for a rule applied
    somewhere else. ``roadway_only_classes`` is the one such rule today — RVV
    art. 5 lid 8, which is applied per edge at graph build time by
    infra/official_access.py and never as an API gate.

    ``valid_from`` and ``valid_to`` bound the period the rule is in force, so a
    measure announced for a future date can be written down now and start
    binding on the day it takes effect rather than being remembered. ``None``
    means unbounded on that side.
    """

    municipality_id: str
    powertrain_classes: frozenset[str]
    allowed_powertrains: frozenset[Powertrain]
    blocked_classes: frozenset[str]

    #: Classes this municipality has moved off the cycle path and onto the
    #: carriageway. Read by infra/official_access.py, not by the API.
    roadway_only_classes: frozenset[str] = frozenset()

    #: Inclusive, and ``valid_to`` exclusive, which is how a measure that starts
    #: or ends on a date reads.
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass(frozen=True)
class SearchBounds:
    """The rectangle an address geocoder serves.

    Saves requests and is emphatically not a border: any rectangle around one
    country contains parts of its neighbours. Served so that adding a country
    does not need an app release.
    """

    south: float
    north: float
    west: float
    east: float


@dataclass(frozen=True)
class BoundaryDocument:
    """How to recognise the official file that carries a country's border.

    A boundary is the outer legal gate — outside it the service returns no
    geometry at all — so loading the wrong file is not a configuration slip but
    a claim about where the law applies. Each country states what its own
    authority's export looks like, and ``supported_area`` refuses anything that
    does not match rather than trusting the filename.

    ``properties`` are the feature properties that must be present and equal.
    For the Netherlands that is the BRK land area's ``identificatie`` and
    ``naam``; another country's cadastre will name its own.
    """

    properties: Mapping[str, str]

    #: Which address register a country wants its addresses read from. Naming
    #: one is all this package can do: the register, its URL and its bounds
    #: travel together, but parsing its answers is code somebody has to write,
    #: so a country naming a register nobody has written a client for gets
    #: place search rather than wrong addresses.
    geocoder: str = ""


@dataclass(frozen=True)
class CountryRules:
    """Everything this service knows about routing lawfully in one country."""

    code: str
    name: str

    #: The vehicles a rider may pick here, in the order they are offered.
    classes: tuple[VehicleClass, ...]

    #: What to route as before the rider has chosen anything.
    #:
    #: Stated rather than left to list order, because it is a safety choice and
    #: not a presentation one. It must be the class with the most restrictive
    #: access of those on offer: guessing a snorfiets for somebody actually on a
    #: bromfiets would route them onto a verplicht fietspad a bromfiets may not
    #: use, which is precisely the mistake this product exists to prevent.
    #: Guessing the other way only costs a longer ride.
    #: ``None`` requires the rider to choose: some countries have no class
    #: whose routes are lawful for every other class.
    default_class: str | None

    municipal_zones: Mapping[str, MunicipalZone]

    #: Where the address geocoder is worth asking. See SearchBounds.
    address_search_bounds: SearchBounds

    #: How to recognise this country's official boundary export.
    boundary: BoundaryDocument

    #: Bumped by hand when the country module changes, and checked for age by
    #: tests/test_rules_freshness.py so stale law cannot report as verified.
    rules_version: str

    #: Where the rules were read from, for a support case that has to name it.
    source: str

    #: Exclusive end of the researched legal regime. A graph build after this
    #: date requires a new review even if its quarterly freshness check passes.
    valid_until: date | None = None

    def __post_init__(self) -> None:
        if not self.classes:
            raise ValueError(f"{self.code} declares no vehicle classes")
        codes = [vehicle.code for vehicle in self.classes]
        if len(codes) != len(set(codes)):
            raise ValueError(f"{self.code} declares a vehicle class code twice")
        if self.default_class is not None and self.default_class not in set(codes):
            raise ValueError(f"{self.code} defaults to a class it does not offer")
        carriers = {vehicle.carrier for vehicle in self.classes}
        if len(carriers) > len(Carrier):
            raise ValueError(f"{self.code} needs more carriers than Valhalla has bits")

    @property
    def class_codes(self) -> frozenset[str]:
        return frozenset(vehicle.code for vehicle in self.classes)

    def vehicle(self, code: str) -> VehicleClass:
        for candidate in self.classes:
            if candidate.code == code:
                return candidate
        raise UnknownVehicleClassError(f"{self.code} does not offer the class {code!r}")


class UnknownVehicleClassError(ValueError):
    """Raised instead of substituting a class the rider did not ask for."""
