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


def is_cycle_infrastructure(tags: dict) -> bool:
    """Mirrors `M.is_cycle_infrastructure` in valhalla/lua/access.lua.

    The two must agree. A way this says yes to and the Lua says no to would be
    handed a `yes` the rules never read; the reverse would leave a path out of
    the index that decides whether a carriageway keeps its closure.
    """
    highway = tags.get("highway")
    if highway == "cycleway":
        return True
    return highway == "path" and (
        tags.get("bicycle") == "designated" or osm_cycle_sign(tags) is not None
    )


#: The one register sign that may open a path, and only for the snorfiets.
#:
#: Not G11, and the reason is art. 5 lid 8 rather than accuracy. A verplicht
#: fietspad can carry an onderbord that sends snorfietsen to the rijbaan, and
#: the register's coverage of onderborden is documented as poor, so a G11
#: cannot be read as admitting a snorfiets without checking a subplate that may
#: not be recorded. Art. 5 lid 8 reaches "het verkeersteken dat het verplichte
#: fietspad aangeeft" and nothing else, so a G12a is untouched by it and can be
#: read at face value. Amsterdam and Utrecht are why this matters in practice.
OPENS_FOR_SNORFIETS = "G12a"


def cycle_sign_of(properties: dict) -> str | None:
    """The cycle-path sign this register record describes, if any.

    PLACED is the only status that describes the road as it is now. The others
    are planned, removed or unknown, and acting on a sign that is not yet up
    would open a path on the strength of somebody's intention.

    `validated` is deliberately not consulted: the register carries the field
    but not one of its 181,765 cycle signs is marked validated, so filtering on
    it would discard the whole source. Measured 2026-08-15.
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
    if sign is None and register_sign == OPENS_FOR_SNORFIETS:
        snorfiets = True

    mofa = stated_access(tags, ("mofa",))
    moped = stated_access(tags, ("moped",))
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
