"""The Dutch cycle-path rules, as pure functions of tags and sign codes.

Split out of official_access.py so they can be tested without an OSM extract, a
shapefile reader or a projection library. That matters more than it sounds:
`path_classes` has to give the same answer as the cycle branch of
`valhalla/lua/access.lua`, and a rule that can only be exercised by a
forty-minute national job is a rule that stops being exercised.

Everything here is a statement about Dutch law. The geometry that decides which
way a sign or a section belongs to is in official_access.py.
"""

from __future__ import annotations

import re

#: Cycle-path signs from RVV 1990 bijlage I, and which classes each admits, as
#: {snorfiets, bromfiets}. The same table as `cycle_signs` in
#: valhalla/lua/countries/nl.lua, and it must not drift from it.
CYCLE_SIGNS = {"G11": (True, False), "G12a": (True, True), "G13": (False, False)}


#: Access values access.lua reads as a permission and as a refusal. Kept in
#: step with ALLOW and DENY there. `use_sidepath` is a refusal: for the class it
#: names, the rider is obliged onto the parallel path.
_ALLOW = {"yes", "designated", "permissive"}
_DENY = {"no", "use_sidepath", "agricultural", "forestry", "dismount"}


def stated_access(tags: dict, keys) -> bool | None:
    for key in keys:
        value = tags.get(key)
        if value is not None:
            return value in _ALLOW if value in _ALLOW or value in _DENY else False
    return None


def osm_cycle_sign(tags: dict) -> str | None:
    """The cycle-path sign the mapper wrote, if any."""
    for key in ("traffic_sign", "traffic_sign:forward", "traffic_sign:backward"):
        value = tags.get(key)
        if not value:
            continue
        for token in value.replace(";", ",").split(","):
            token = token.strip().removeprefix("NL:")
            if token in CYCLE_SIGNS:
                return token
    return None


#: The voetpad values NL-ACC-12 can open, and what the overlay writes there.
#: The same strings as FOOTPATH, FOOTPATH_PLATE and FOOTPATH_G12A in
#: valhalla/lua/access.lua.
FOOTPATH = {"footway", "pedestrian"}
FOOTPATH_PLATE = "footpath_onderbord"
FOOTPATH_G12A = "footpath_g12a"
_OVERLAY_KEYS = ("amgraph:snorfiets", "amgraph:bromfiets")


def is_cycle_infrastructure(tags: dict) -> bool:
    """Mirrors `M.is_cycle_infrastructure` in valhalla/lua/access.lua.

    The two must agree. A way this says yes to and the Lua says no to would be
    handed a `yes` the rules never read; the reverse would leave a path out of
    the index that decides whether a carriageway keeps its closure.
    """
    highway = tags.get("highway")
    if highway == "cycleway":
        return True
    if highway in FOOTPATH:
        return any(tags.get(key) == FOOTPATH_G12A for key in _OVERLAY_KEYS)
    return highway == "path" and (
        tags.get("bicycle") == "designated" or osm_cycle_sign(tags) is not None
    )


#: The register signs that may open a path, and only for the snorfiets: art. 5
#: lid 1 admits it to both, so confusing them costs nothing. Art. 5 lid 8 is
#: applied to a register G11 exactly as to a mapped one, in Paths.way.
OPENS_FOR_SNORFIETS = frozenset({"G11", "G12a"})


def cycle_sign_of(properties: dict) -> str | None:
    """The cycle-path sign this register record describes, if any.

    PLACED is the only status that describes the road as it is now. The others
    are planned, removed or unknown, and acting on a sign that is not yet up
    would open a path on the strength of somebody's intention.

    `validated` is not consulted: no cycle sign in the register is marked
    validated, so filtering on it would discard the whole source.
    """
    if properties.get("status") != "PLACED":
        return None
    code = properties.get("rvvCode")
    return code if code in CYCLE_SIGNS else None


def path_classes(tags: dict, register_sign: str | None) -> tuple[bool, bool]:
    """Which classes may use this path, as access.lua will decide it.

    Explicit OSM access tags beat a sign, an OSM sign beats the register, and
    the register reaches the snorfiets only — see the cycle branch in
    access.lua for why that asymmetry is what makes it safe.
    """
    sign = osm_cycle_sign(tags)
    snorfiets, bromfiets = CYCLE_SIGNS.get(sign, (False, False))
    if sign is None and register_sign in OPENS_FOR_SNORFIETS:
        snorfiets = True

    mofa = stated_access(tags, ("mofa",))
    moped = stated_access(tags, ("moped",))
    # NL-ACC-03: a cycle path a bromfiets may use is a G12a, which admits the
    # snorfiets, unless the way refuses bicycles or the snorfiets. Mirrors
    # cycle_evidence_keys on the snorfiets in countries/nl.lua.
    vetoed = any(
        key in tags and stated_access(tags, (key,)) is not True for key in ("bicycle", "mofa")
    )
    if sign is None and moped is True and not vetoed:
        snorfiets = True
    if mofa is not None:
        snorfiets = mofa
    if moped is not None:
        bromfiets = moped
    if stated_access(tags, ("bicycle",)) is False:
        snorfiets = False
    if stated_access(tags, ("access",)) is False or stated_access(tags, ("vehicle",)) is False:
        snorfiets = mofa is True
        bromfiets = moped is True
    return snorfiets, bromfiets


def mapped_signs(tags: dict) -> set[str]:
    """Every sign code on the unscoped `traffic_sign`, as access.lua reads it.

    Directional signs are left out because the Lua reads the cycle signs and
    the G7 from the unscoped key only.
    """
    value = tags.get("traffic_sign") or ""
    return {token.strip().removeprefix("NL:") for token in value.replace(";", ",").split(",")}


def _letters(text: str | None) -> str:
    return re.sub(r"[^a-z]", "", (text or "").lower())


#: Onderbord texts under a G7 that admit bromfietsen, letters only, as
#: (snorfiets, bromfiets). RVV art. 67 lid 2: "Indien het beoogde verkeersgedrag
#: wordt aangegeven door middel van teksten … blijkt het beoogde verkeersgedrag
#: uit het onderbord." A snorfiets is a bromfiets (NL-DEF-01), so every one of
#: these admits it. A closed list on purpose: the register holds thousands of
#: free-text plates, and any text not listed here opens nothing.
_PLATES_ADMITTING = {
    "bromfietsentoegestaan": (True, True),
    "bromfietserstoegestaan": (True, True),
    "fietsenbromensnorfietsentoegestaan": (True, True),
}


def plate_admits(texts) -> tuple[bool, bool]:
    """Which classes the plates under one register G7 admit.

    Every plate on the sign must be one of the admitting texts. A second plate
    usually carries hours or a further condition, which this graph cannot hold,
    so a sign with one says nothing.
    """
    plates = [_letters(text) for text in texts if _letters(text)]
    if not plates or any(plate not in _PLATES_ADMITTING for plate in plates):
        return (False, False)
    return (
        all(_PLATES_ADMITTING[plate][0] for plate in plates),
        all(_PLATES_ADMITTING[plate][1] for plate in plates),
    )


def plate_refuses_snorfiets(texts) -> bool:
    """Whether any plate on a register sign names the snorfiets.

    On a G11 that is the art. 5 lid 8 onderbord. Nothing on a plate naming the
    snorfiets admits it to a G11 it would not already use, so any mention is
    read as the refusal.
    """
    return any("snor" in _letters(text) for text in texts)


def footpath_overlay(
    tags: dict,
    register_sign: str | None,
    register_plate: tuple[bool, bool] | None,
) -> tuple[str | None, str | None]:
    """NL-ACC-12: what the overlay writes on a voetpad, as (snorfiets, bromfiets).

    `register_sign` is the register's cycle sign for this way, `register_plate`
    the classes a register G7 beside it admits by its plate. Each opening needs
    the mapper and the register to say the same thing; neither is trusted alone.
    """
    if tags.get("highway") not in FOOTPATH:
        return (None, None)
    signs = mapped_signs(tags)
    # NL-ACC-03: a G12a defines a fiets/bromfietspad, whatever was drawn.
    if "G12a" in signs and register_sign == "G12a":
        return (FOOTPATH_G12A, FOOTPATH_G12A)
    # A voetpad the mapper left unsigned is still a voetpad; the register's G7
    # beside it is the sign, and the mapper's permission the second source.
    unsigned = not (tags.get("traffic_sign") or "").strip()
    if ("G7" in signs or unsigned) and register_plate is not None:
        return (
            FOOTPATH_PLATE if register_plate[0] and stated_access(tags, ("mofa",)) else None,
            FOOTPATH_PLATE if register_plate[1] and stated_access(tags, ("moped",)) else None,
        )
    return (None, None)


def on_exempt_road(name: str | None, point: tuple[float, float], roads) -> bool:
    """Whether a way named `name` at `point` (lat, lon) is on an excepted road.

    `roads` is (name, (south, west, north, east)) pairs, as the country module
    states them for art. 5 lid 8.
    """
    if not name:
        return False
    lat, lon = point
    return any(
        name == road and south <= lat <= north and west <= lon <= east
        for road, (south, west, north, east) in roads
    )


def closes_class(
    class_head: str,
    class_tail: str,
    auto_head: str,
    auto_tail: str,
) -> bool:
    """Whether an undirected OSM way must close for this WKD class.

    On a carriageway, an ``N`` in the direction where ``AUTO`` is also ``N``
    normally describes the unused side of a one-way road. It is not a class
    prohibition. An ``N`` where automobiles may travel is one, and because the
    overlay does not carry direction it closes the complete way.

    A cycle-like section has no automobile direction to use as that reference.
    Any refusal therefore closes the complete way rather than guessing whether
    it is merely the unused side of a one-way path.
    """
    automobile_directions = (auto_head == "J", auto_tail == "J")
    if any(automobile_directions):
        return (class_head == "N" and automobile_directions[0]) or (
            class_tail == "N" and automobile_directions[1]
        )
    return class_head == "N" or class_tail == "N"
