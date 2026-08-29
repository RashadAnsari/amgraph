"""How a vehicle class reaches Valhalla.

An access class rides a stock Valhalla travel mode, which is what lets one graph
serve rules that contradict each other on the cycle network. The mapping is set
in the Lua transform at build time (``valhalla/lua/access.lua``); this
module is the query-time half of the same decision, and the two must agree.

What is *not* here is any particular country's classes. Those live in
``countries/<cc>.py`` beside the rest of that country's law, because which
vehicles exist and what they may do is a statutory question and this file is a
question about Valhalla.

See AGENTS.md, the two files that must agree.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class Carrier(StrEnum):
    """A stock Valhalla travel mode borrowed to carry one access class.

    Five, and the count is the ceiling on how many access classes a country may
    have. Three would not reach Belgium: art. 9.1.2 of the Code van de openbare
    weg splits into four sets of rights, because a speed pedelec and a klasse B
    bromfiets differ on a cycle path where the limit is 50 km/h or less.

    ``TAXI`` and ``BUS`` are the two remaining Valhalla costings that read an
    access bit of their own: ``TaxiCost`` and ``BusCost`` both derive from
    ``AutoCost`` with ``kTaxiAccess`` and ``kBusAccess``, verified against the
    3.8.3 source. ``auto`` is deliberately not here — it is the mode the rest of
    the toolchain assumes when it wants to know whether a road exists at all,
    and borrowing it would make a diagnostic route mean something else.
    """

    MOPED = "moped"
    MOTORCYCLE = "motorcycle"
    TRUCK = "truck"
    TAXI = "taxi"
    BUS = "bus"


class Powertrain(StrEnum):
    ELECTRIC = "electric"
    COMBUSTION = "combustion"


#: Which Valhalla costing reads each carrier's access bit. Changing a value here
#: without changing the matching carrier in access.lua produces routes that
#: silently obey the wrong rules.
_COSTING: dict[Carrier, str] = {
    Carrier.MOPED: "motor_scooter",
    Carrier.MOTORCYCLE: "motorcycle",
    Carrier.TRUCK: "truck",
    Carrier.TAXI: "taxi",
    Carrier.BUS: "bus",
}


def costing_for(carrier: Carrier) -> str:
    return _COSTING[carrier]


def costing_options_for(
    carrier: Carrier, top_speed_kph: int, *, for_map_matching: bool = False
) -> dict[str, Any]:
    """Costing options for a carrier, keyed by costing name as Valhalla expects.

    ``for_map_matching`` omits ``disable_hierarchy_pruning``. That is not a
    tuning choice: sending it to ``/trace_attributes`` **segfaults Valhalla
    3.8.3**, taking the whole service down for every user. Verified 2026-08-06
    against the pinned image; the same option on ``/route`` is fine and
    necessary.
    """
    costing = _COSTING[carrier]
    options: dict[str, Any] = {"top_speed": top_speed_kph}

    if not for_map_matching:
        # Without this, routes over roughly 30 km fail outright for the
        # two-wheeled classes. Valhalla's search climbs to higher road-class
        # hierarchy levels on long routes, and NL-ACC-01 strips our classes off
        # the autowegen that populate the top level, so there is nothing up
        # there to climb to. Requires
        # service_limits.max_distance_disable_hierarchy_culling to be non-zero;
        # valhalla/build.sh sets it.
        options["disable_hierarchy_pruning"] = True

    if costing in {"truck", "taxi", "bus"}:
        # A four-wheeled class borrows an auto-family costing purely for its
        # access bit. Those costings also apply vehicle dimensions to weight and
        # height limits, and a lorry's or a coach's defaults would keep a
        # microcar out of half the country. Regulation (EU) 168/2013 Annex I
        # sets the L6e-B maxima. Using a representative small model here can
        # route a taller or heavier legal microcar through a signed restriction
        # it does not fit under.
        options |= {
            "height": 2.5,
            "width": 1.5,
            "length": 3.0,
            # Delegated Regulation (EU) 44/2014 permits up to 300 kg payload
            # for L6e-BU on top of the 425 kg running-order maximum.
            "weight": 0.725,
            "axle_load": 0.725,
            "hazmat": False,
        }
    elif costing == "motorcycle":
        # Motorcycle costing prefers trails and twisty roads by default, which
        # is a touring preference, not a commute. Neither affects legality:
        # access bits are hard constraints.
        options |= {"use_trails": 0.0, "use_highways": 0.0}
    elif costing == "motor_scooter":
        options |= {"use_primary": 0.3, "use_hills": 0.5}

    return {costing: options}
