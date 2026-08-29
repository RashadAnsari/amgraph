-- Valhalla tag-transform entry point for amgraph.
--
-- Thin adapter. It decorates upstream's `ways_proc` instead of forking
-- graph.lua, so upgrading Valhalla means pointing UPSTREAM_GRAPH_LUA at the new
-- file rather than rebasing 2,500 lines. All the access rules live in
-- access.lua and the country modules beside it.

local UPSTREAM = os.getenv("UPSTREAM_GRAPH_LUA") or "/valhalla/lua/graph.lua"
local ACCESS = os.getenv("AMGRAPH_ACCESS_LUA") or "/valhalla/lua/access.lua"

-- Which country this graph is being built for. Ways carry their own attribution
-- and do not need it, but nodes do: infra/official_access.py writes the
-- boundary verdict onto ways only, so a node has nothing to say where it is.
--
-- One graph per country is already the rule — access.lua closes any way whose
-- country it cannot establish, so a border-crossing way gets no access at all
-- — and this is that rule written down where the build can check it. An
-- unrecognised or missing code leaves every node closed to our classes rather
-- than silently applying a neighbour's sign vocabulary, which is what naming a
-- country outright here would do.
local COUNTRY = os.getenv("AMGRAPH_COUNTRY") or "NL"

dofile(UPSTREAM)

local access = assert(loadfile(ACCESS))()
local upstream_ways_proc = ways_proc
local upstream_nodes_proc = nodes_proc

local node_country = access.COUNTRIES[COUNTRY]

function ways_proc(kv, nokeys)
  -- Upstream consumes and rewrites tags as it runs, so the original OSM tags
  -- must be copied first. Our rules are written against what a mapper actually
  -- typed, not against Valhalla's normalised output.
  local tags = {}
  for key, value in pairs(kv) do
    tags[key] = value
  end

  local filter, out, is_polygon, roundabout = upstream_ways_proc(kv, nokeys)
  if filter ~= 0 then
    return filter, out, is_polygon, roundabout
  end

  for flag, value in pairs(access.carrier_flags(tags)) do
    out[flag] = value
  end

  return filter, out, is_polygon, roundabout
end

function nodes_proc(kv, nokeys)
  local tags = {}
  for key, value in pairs(kv) do
    tags[key] = value
  end

  local filter, out = upstream_nodes_proc(kv, nokeys)
  if filter ~= 0 then
    return filter, out
  end

  local classes = access.node_classes(tags, node_country)

  -- Intersect with upstream rather than replacing it. Our legal-class reading
  -- may close a borrowed carrier bit, but it may never reopen a wall, bollard
  -- or other physical refusal that upstream already understood.
  --
  -- Every carrier this build could borrow is cleared when the country is
  -- unknown, not just the ones this country uses: an unknown country has no
  -- class list to iterate, and leaving a carrier untouched would let upstream's
  -- ordinary road access stand in for a legal verdict nobody made.
  if node_country == nil then
    for _, carrier in ipairs(access.CARRIER_ORDER) do
      local mask = access.CARRIERS[carrier].mask
      out["access_mask"] = bit.band(out["access_mask"], bit.bnot(mask))
    end
    return filter, out
  end

  for index, class in ipairs(node_country.classes) do
    if not classes[index] then
      local mask = access.CARRIERS[class.carrier].mask
      out["access_mask"] = bit.band(out["access_mask"], bit.bnot(mask))
    end
  end

  return filter, out
end
