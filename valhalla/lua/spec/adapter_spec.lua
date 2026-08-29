-- Pins the carrier-bit intersection in amgraph.lua. access_spec.lua verifies the
-- legal decisions; this verifies that a node decision reaches the Valhalla
-- bits that the API's costings actually query.

dofile(arg[1])

local failures = 0
local checks = 0

local function equals(description, actual, expected)
  checks = checks + 1
  if actual ~= expected then
    failures = failures + 1
    print(string.format("FAIL %s: expected %s, got %s",
      description, tostring(expected), tostring(actual)))
  end
end

local function mask(tags)
  local _, out = nodes_proc(tags, {})
  return out.access_mask
end

equals("moped=no clears the borrowed motorcycle bit",
  mask({ moped = "no" }) & 1024, 0)
equals("moped=no does not clear the snorfiets moped bit",
  mask({ moped = "no" }) & 512, 512)
equals("motorcar=no clears the borrowed truck bit",
  mask({ motorcar = "no" }) & 8, 0)
equals("C13 on a node clears both two-wheeler carrier bits",
  mask({ traffic_sign = "NL:C13" }) & (512 | 1024), 0)
equals("an ordinary node preserves all carrier bits",
  mask({ highway = "crossing" }) & (512 | 1024 | 8), 512 | 1024 | 8)
equals("amgraph never reopens an upstream physical refusal",
  mask({ upstream_access_mask = 0, moped = "yes", motorcar = "yes" }), 0)

print(string.format("%d adapter checks, %d failures", checks, failures))
os.exit(failures == 0 and 0 or 1)
