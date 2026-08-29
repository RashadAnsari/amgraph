#!/usr/bin/env bash
# Runs the access-rule unit tests.
#
# Uses a local lua when there is one and Docker otherwise, so the same command
# works on a laptop with nothing installed and in CI.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
lua_dir="$(dirname "$here")"

if command -v lua >/dev/null 2>&1; then
  lua "$here/access_spec.lua" "$lua_dir/access.lua"
  lua "$here/second_country_spec.lua" "$lua_dir/access.lua"
  UPSTREAM_GRAPH_LUA="$here/upstream_stub.lua" \
    AMGRAPH_ACCESS_LUA="$lua_dir/access.lua" \
    lua "$here/adapter_spec.lua" "$lua_dir/amgraph.lua"
  exit
fi

exec docker run --rm \
  -v "$lua_dir:/lua:ro" \
  -w /lua \
  nickblah/lua:5.4-alpine \
  sh -c 'lua /lua/spec/access_spec.lua /lua/access.lua && \
    lua /lua/spec/second_country_spec.lua /lua/access.lua && \
    UPSTREAM_GRAPH_LUA=/lua/spec/upstream_stub.lua \
    AMGRAPH_ACCESS_LUA=/lua/access.lua \
    lua /lua/spec/adapter_spec.lua /lua/amgraph.lua'
