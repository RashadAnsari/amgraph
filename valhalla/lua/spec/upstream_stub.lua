bit = {
  band = function(one, two) return one & two end,
  bnot = function(value) return ~value end,
  bor = function(...)
    local value = 0
    for index = 1, select("#", ...) do
      value = value | select(index, ...)
    end
    return value
  end,
}

function ways_proc(kv, _)
  return 0, kv, false, false
end

function nodes_proc(kv, _)
  return 0, { access_mask = kv.upstream_access_mask or bit.bor(512, 1024, 8) }
end
