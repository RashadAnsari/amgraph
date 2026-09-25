-- access.lua with the invented ZZ fixture registered beside the real countries.
--
-- amgraph.lua keeps its access module to itself, so the adapter spec points
-- AMGRAPH_ACCESS_LUA here to run the adapter over two countries. The real
-- registry never sees ZZ.

local here = debug.getinfo(1, "S").source:match("^@(.*/)") or "./"
local access = assert(loadfile(here .. "../access.lua"))()
access.COUNTRIES.ZZ = access.prepare(assert(loadfile(here .. "fixture_country.lua"))()("zz-fixture"))
return access
