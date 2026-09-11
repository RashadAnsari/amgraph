-- Valhalla tag-transform entry point for amgraph.
--
-- Thin adapter. It decorates upstream's `ways_proc` instead of forking
-- graph.lua, so upgrading Valhalla means pointing UPSTREAM_GRAPH_LUA at the new
-- file rather than rebasing 2,500 lines. All the access rules live in
-- access.lua and the country modules beside it.

local UPSTREAM = os.getenv("UPSTREAM_GRAPH_LUA") or "/valhalla/lua/graph.lua"
local ACCESS = os.getenv("AMGRAPH_ACCESS_LUA") or "/valhalla/lua/access.lua"

dofile(UPSTREAM)

local access = assert(loadfile(ACCESS))()
local upstream_ways_proc = ways_proc
local upstream_nodes_proc = nodes_proc

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
  -- Valhalla's enhance stage otherwise replaces these bits with its stock
  -- country defaults. Every carrier decision is explicit, including a ban
  -- and an unused carrier: see 3.8.3 mjolnir/countryaccess.cc GetAccess.
  for _, carrier in ipairs(access.CARRIER_ORDER) do
    out[carrier .. "_tag"] = "true"
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

  -- A border control must satisfy every jurisdiction touching the node.
  -- Clearing all unassigned carriers also prevents stock taxi/bus permission
  -- from surviving where this country's vehicle model does not use that bit.
  local countries = access.countries_for(tags)
  local allowed = {}
  for index, country in ipairs(countries) do
    local classes = access.node_classes(tags, country)
    local current = {}
    for position, class in ipairs(country.classes) do
      current[class.carrier] = classes[position]
    end
    for _, carrier in ipairs(access.CARRIER_ORDER) do
      if index == 1 then allowed[carrier] = current[carrier]
      else allowed[carrier] = allowed[carrier] and current[carrier] end
    end
  end
  for _, carrier in ipairs(access.CARRIER_ORDER) do
    if not allowed[carrier] then
      local mask = access.CARRIERS[carrier].mask
      out["access_mask"] = bit.band(out["access_mask"], bit.bnot(mask))
    end
  end
  return filter, out
end
