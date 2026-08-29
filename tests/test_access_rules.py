"""Every access-tag combination in the Netherlands, not a sample of them.

The rules themselves are pinned case by case in
`valhalla/lua/spec/access_spec.lua`, which is plain Lua, needs nothing
installed and runs in `make verify`. That is where a new rule belongs.

This adds the one thing that spec cannot do: read the country. Lua has no OSM
reader, so it cannot ask which tag combinations actually exist. Python can, and
the answer is small — 2.8 million highway ways collapse to about fifteen
thousand distinct combinations of the tags the rules consult, which is few
enough to check all of them rather than whichever ones happen to lie on a
sampled route.

It found the defect it was written to find. `access=no` together with
`motor_vehicle=yes` on a `highway=cycleway` returned before the
cycle-infrastructure branch and handed a brommobiel a fietspad. Six ways in the
Netherlands are tagged that way.

A pass here means no way in the country can be offered to a class the law bars
from it — as far as the rules know. It says nothing about whether
OpenStreetMap describes the Netherlands correctly.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ACCESS_LUA = ROOT / "valhalla" / "lua" / "access.lua"

#: Lua 5.4, because 5.5 makes for-loop variables const and access.lua assigns
#: to one. Valhalla itself embeds an older Lua, so 5.4 is the closer match.
lupa = pytest.importorskip("lupa.lua54", reason="lupa provides the Lua runtime")

#: Every tag key access.lua consults. This pass enumerates combinations of
#: these, so a key read by the rules but missing here would silently narrow the
#: test; the check below fails instead.
CONSULTED = [
    "highway",
    "junction",
    "motorroad",
    "access",
    "vehicle",
    "bicycle",
    "mofa",
    "moped",
    "speed_pedelec",
    "motorcar",
    "motor_vehicle",
    "access:forward",
    "access:backward",
    "vehicle:forward",
    "vehicle:backward",
    "access:lanes",
    "access:lanes:forward",
    "access:lanes:backward",
    "vehicle:lanes",
    "vehicle:lanes:forward",
    "vehicle:lanes:backward",
    "mofa:forward",
    "mofa:backward",
    "bicycle:forward",
    "bicycle:backward",
    "mofa:lanes",
    "mofa:lanes:forward",
    "mofa:lanes:backward",
    "bicycle:lanes",
    "bicycle:lanes:forward",
    "bicycle:lanes:backward",
    "moped:forward",
    "moped:backward",
    "moped:lanes",
    "moped:lanes:forward",
    "moped:lanes:backward",
    "motor_vehicle:forward",
    "motor_vehicle:backward",
    "motorcar:forward",
    "motorcar:backward",
    "motor_vehicle:lanes",
    "motor_vehicle:lanes:forward",
    "motor_vehicle:lanes:backward",
    "motorcar:lanes",
    "motorcar:lanes:forward",
    "motorcar:lanes:backward",
    "access:conditional",
    "access:forward:conditional",
    "access:backward:conditional",
    "vehicle:conditional",
    "vehicle:forward:conditional",
    "vehicle:backward:conditional",
    "bicycle:conditional",
    "bicycle:forward:conditional",
    "bicycle:backward:conditional",
    "mofa:conditional",
    "mofa:forward:conditional",
    "mofa:backward:conditional",
    "moped:conditional",
    "moped:forward:conditional",
    "moped:backward:conditional",
    "speed_pedelec:conditional",
    "speed_pedelec:forward",
    "speed_pedelec:backward",
    "speed_pedelec:forward:conditional",
    "speed_pedelec:backward:conditional",
    "speed_pedelec:lanes",
    "speed_pedelec:lanes:forward",
    "speed_pedelec:lanes:backward",
    "oneway:speed_pedelec",
    "oneway:speed_pedelec:conditional",
    "motor_vehicle:conditional",
    "motor_vehicle:forward:conditional",
    "motor_vehicle:backward:conditional",
    "motorcar:conditional",
    "motorcar:forward:conditional",
    "motorcar:backward:conditional",
    "maxspeed",
    "maxspeed:forward",
    "maxspeed:backward",
    "zone:maxspeed",
    "zone:maxspeed:forward",
    "zone:maxspeed:backward",
    "source:maxspeed",
    "source:maxspeed:forward",
    "source:maxspeed:backward",
    "maxspeed:type",
    "maxspeed:type:forward",
    "maxspeed:type:backward",
    "maxspeed:conditional",
    "maxspeed:forward:conditional",
    "maxspeed:backward:conditional",
    "maxspeed:mofa:conditional",
    "maxspeed:mofa:forward:conditional",
    "maxspeed:mofa:backward:conditional",
    "maxspeed:mofa",
    "maxspeed:mofa:forward",
    "maxspeed:mofa:backward",
    "maxspeed:bicycle",
    "maxspeed:bicycle:forward",
    "maxspeed:bicycle:backward",
    "maxspeed:bicycle:conditional",
    "maxspeed:bicycle:forward:conditional",
    "maxspeed:bicycle:backward:conditional",
    "maxspeed:moped:conditional",
    "maxspeed:moped:forward:conditional",
    "maxspeed:moped:backward:conditional",
    "maxspeed:moped",
    "maxspeed:moped:forward",
    "maxspeed:moped:backward",
    "maxspeed:speed_pedelec",
    "maxspeed:speed_pedelec:forward",
    "maxspeed:speed_pedelec:backward",
    "maxspeed:speed_pedelec:conditional",
    "maxspeed:speed_pedelec:forward:conditional",
    "maxspeed:speed_pedelec:backward:conditional",
    "maxspeed:motor_vehicle:conditional",
    "maxspeed:motor_vehicle:forward:conditional",
    "maxspeed:motor_vehicle:backward:conditional",
    "maxspeed:motor_vehicle",
    "maxspeed:motor_vehicle:forward",
    "maxspeed:motor_vehicle:backward",
    "maxspeed:motorcar:conditional",
    "maxspeed:motorcar:forward:conditional",
    "maxspeed:motorcar:backward:conditional",
    "maxspeed:motorcar",
    "maxspeed:motorcar:forward",
    "maxspeed:motorcar:backward",
    "maxwidth",
    "maxwidth:physical",
    "maxwidth:forward",
    "maxwidth:backward",
    "maxwidth:conditional",
    "maxwidth:forward:conditional",
    "maxwidth:backward:conditional",
    "maxheight",
    "maxheight:forward",
    "maxheight:backward",
    "maxheight:conditional",
    "maxheight:forward:conditional",
    "maxheight:backward:conditional",
    "maxlength",
    "maxlength:forward",
    "maxlength:backward",
    "maxlength:conditional",
    "maxlength:forward:conditional",
    "maxlength:backward:conditional",
    "maxweight",
    "maxweight:forward",
    "maxweight:backward",
    "maxweight:conditional",
    "maxweight:forward:conditional",
    "maxweight:backward:conditional",
    "maxaxles",
    "maxaxles:conditional",
    "maxaxleload",
    "maxaxleload:conditional",
    "hazmat",
    "hazmat:conditional",
    "hazmat:forward",
    "hazmat:backward",
    "hazmat:forward:conditional",
    "hazmat:backward:conditional",
    "oneway",
    "oneway:vehicle",
    "oneway:mofa",
    "oneway:moped",
    "oneway:motor_vehicle",
    "oneway:motorcar",
    "oneway:conditional",
    "oneway:vehicle:conditional",
    "oneway:mofa:conditional",
    "oneway:moped:conditional",
    "oneway:motor_vehicle:conditional",
    "oneway:motorcar:conditional",
    "traffic_sign",
    "traffic_sign:forward",
    "traffic_sign:backward",
    "amgraph:snorfiets",
    "amgraph:bromfiets",
    "amgraph:country",
]


class DutchRules:
    """`access.lua`, loaded once, answering for the Netherlands."""

    def __init__(self) -> None:
        self._runtime = lupa.LuaRuntime()
        access = self._runtime.eval(f'dofile("{ACCESS_LUA}")')
        self._access = access
        self._country = access.COUNTRIES.NL

        #: Every OSM key the rules read for this country, from the rules
        #: themselves. See test_the_consulted_key_list_still_matches_the_rules.
        self.consulted = list(access.consulted_keys(self._country).values())

    def __call__(self, tags: dict[str, str]) -> tuple[bool, bool, bool]:
        # Carrier flags rather than classes(), so the direction handling is
        # covered too: moped is the snorfiets, motorcycle the bromfiets and
        # speed pedelec, truck the brommobiel. See AGENTS.md, the two files
        # that must agree.
        flags = dict(self._access.carrier_flags(self._runtime.table_from(tags), self._country))
        return (
            flags["moped_forward"] == "true",
            flags["motorcycle_forward"] == "true",
            flags["truck_forward"] == "true",
        )


@pytest.fixture(scope="module")
def rules() -> DutchRules:
    return DutchRules()


def test_the_consulted_key_list_still_matches_the_rules(rules) -> None:
    """Keeps the exhaustive pass exhaustive.

    If access.lua starts reading a key this file does not vary, the enumeration
    below quietly stops covering it and nothing else notices.

    The rules answer for themselves rather than being read with a regular
    expression over the source, which is how this worked until the per-class key
    families became derived: `mofa` plus a suffix list produces
    `mofa:lanes:forward` without that string appearing anywhere to match. A
    pattern that cannot see a key reports no gap, so the weaker the rules got
    the greener this went.
    """
    missing = set(rules.consulted) - set(CONSULTED)
    assert not missing, (
        f"access.lua reads {sorted(missing)}, which this pass never varies, so it "
        "would stop being exhaustive. Add them to CONSULTED."
    )

    # The converse is not an error — a key may be varied here without the rules
    # reading it yet — but a key that has stopped being read is worth removing,
    # because every one of them multiplies the combinations enumerated below.
    unread = set(CONSULTED) - set(rules.consulted)
    assert not unread, (
        f"CONSULTED varies {sorted(unread)}, which access.lua no longer reads. "
        "Remove them: each one multiplies the combination count for nothing."
    )


@pytest.mark.graph
def test_no_tag_combination_in_the_netherlands_breaks_a_rule(rules) -> None:
    osmium = pytest.importorskip("osmium", reason="reads the extract")
    work = ROOT / "infra" / "work"
    override = os.environ.get("AMGRAPH_EXTRACT")
    if override:
        extract = Path(override)
    else:
        # The enriched extract by preference: it carries the authority's
        # verdict, so it is what the graph is actually built from. Falling back
        # to the plain one still checks every rule, just without those tags.
        enriched = sorted(work.glob("*-official.osm.pbf"))
        assert len(enriched) <= 1, f"more than one enriched extract: {enriched}"
        extract = enriched[0] if enriched else work / "netherlands-latest.osm.pbf"
    if not extract.exists():
        pytest.skip(f"no extract at {extract}")

    combos: Counter[tuple[str | None, ...]] = Counter()

    class Collect(osmium.SimpleHandler):
        def way(self, w) -> None:
            if w.tags.get("highway") is None:
                return
            combos[tuple(w.tags.get(k) for k in CONSULTED)] += 1

    Collect().apply_file(str(extract))
    assert combos, "the extract produced no combinations"

    failures: list[str] = []
    for combo, count in combos.items():
        tags = {k: v for k, v in zip(CONSULTED, combo, strict=True) if v is not None}
        snorfiets, bromfiets, brommobiel = rules(tags)

        # RVV art. 42 admits only motorvoertuigen, and no bromfiets is one.
        barred = (
            tags.get("highway") in {"motorway", "motorway_link"} or tags.get("motorroad") == "yes"
        )
        if barred and (snorfiets or bromfiets or brommobiel):
            failures.append(f"{tags} on an autosnelweg or autoweg ({count:,} ways)")

        # Art. 6 lid 3. A brommobiel is wider than 0.75 m, so it belongs on the
        # rijbaan and may never be routed onto cycle infrastructure.
        if tags.get("highway") == "cycleway" and brommobiel:
            failures.append(f"{tags} put a brommobiel on a cycleway ({count:,} ways)")

        # The fail-safe. A cycleway nothing says anything about is ambiguous
        # between G11 and G12a, which are opposite answers, so it admits
        # nobody — with one exception, and the exception is bounded here rather
        # than trusted. The road authority's sign register can say which sign
        # stands on it, and `amgraph:snorfiets=yes` is that answer. It
        # reaches the snorfiets alone: art. 5 lid 1 admits that class to a G11
        # and a G12a alike, so the register only has to establish that one of
        # the two is there. For a bromfiets they are opposite answers and no
        # value of the overlay may open the way. See docs/rules.md
        # NL-ACC-02 and NL-ACC-03.
        says_something = any(
            tags.get(k)
            for k in (
                "traffic_sign",
                "traffic_sign:forward",
                "traffic_sign:backward",
                "moped",
                "mofa",
                "bicycle",
                "access",
                "vehicle",
            )
        )
        if tags.get("highway") == "cycleway" and not says_something:
            register_opened = tags.get("amgraph:snorfiets") == "yes"
            if bromfiets:
                failures.append(f"{tags} put a bromfiets on an unsigned cycleway ({count:,} ways)")
            if snorfiets and not register_opened:
                failures.append(f"{tags} opened an unsigned cycleway ({count:,} ways)")

    assert not failures, (
        f"{len(failures)} of {len(combos):,} combinations break a rule:\n"
        + "\n".join(failures[:15])
    )
