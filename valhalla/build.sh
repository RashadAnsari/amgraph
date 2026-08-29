#!/usr/bin/env bash
# Builds the amgraph routing graph.
#
# Runs upstream Valhalla, unmodified and pinned by digest, with our own Lua tag
# transform so the country's access classes land on carrier travel modes. See
# docs/rules.md §2.
#
#   ./valhalla/build.sh [path-to-extract.osm.pbf]
set -euo pipefail

# Pinned: an image tag can move under us, and a routing graph that silently
# changes its access semantics is the worst kind of regression.
VALHALLA_IMAGE="ghcr.io/valhalla/valhalla@sha256:e84a20c31605048c5bf4860f2bcf48c2e3f3d9f2ec8ff13d1497fed055310081"
VALHALLA_VERSION="3.8.3"
VALHALLA_CONTAINER="amgraph-valhalla"

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work_dir="${WORK_DIR:-$repo_root/infra/work}"
lua_dir="$repo_root/valhalla/lua"
# infra/official_access.py writes the enriched extract with both the road
# authority's access verdict and official BRK country attribution.
extract="${1:-}"
if [[ -z "$extract" ]]; then
  # Found rather than named, so the extract's country is not baked in here.
  # `make infra-extract EXTRACT_URL=…` saves whatever Geofabrik calls the file,
  # so hardcoding netherlands-*.osm.pbf made the workflow's own extract_url
  # input impossible to use.
  shopt -s nullglob
  enriched=("$work_dir"/*-official.osm.pbf)
  plain=()
  for candidate in "$work_dir"/*.osm.pbf; do
    [[ "$candidate" == *-official.osm.pbf ]] || plain+=("$candidate")
  done
  shopt -u nullglob

  if (( ${#enriched[@]} > 1 || ${#plain[@]} > 1 )); then
    echo "More than one extract in $work_dir. Name the one to build from:" >&2
    printf '  %s\n' "${enriched[@]}" "${plain[@]}" >&2
    echo "  $0 <path-to.osm.pbf>" >&2
    exit 1
  fi

  if (( ${#enriched[@]} == 1 )); then
    extract="${enriched[0]}"
  else
    echo "No *-official.osm.pbf in $work_dir." >&2
    echo "A graph without BRK attribution cannot serve any route. Run:" >&2
    echo "  make infra-official-data infra-official-access" >&2
    exit 1
  fi
fi

if [[ "$extract" != *-official.osm.pbf ]]; then
  echo "Refusing an extract without the official access and BRK overlay: $extract" >&2
  exit 1
fi

if [[ ! -f "$extract" ]]; then
  echo "No extract at $extract" >&2
  echo "Fetch one with: curl -o $extract https://download.geofabrik.de/europe/netherlands-latest.osm.pbf" >&2
  exit 1
fi

mkdir -p "$work_dir/valhalla" "$work_dir/lua"

# Our transform decorates upstream's ways_proc rather than replacing it, so it
# needs upstream's graph.lua on disk. It is fetched for the pinned version
# rather than committed: it is a dependency, not our code, and vendoring 2,500
# lines we never edit would invite someone to edit them.
upstream_lua="$work_dir/lua/graph.lua"
if [[ ! -f "$upstream_lua" ]]; then
  echo "Fetching upstream graph.lua for Valhalla $VALHALLA_VERSION"
  curl -fsSL -o "$upstream_lua" \
    "https://raw.githubusercontent.com/valhalla/valhalla/$VALHALLA_VERSION/lua/graph.lua"
fi
cp "$lua_dir/access.lua" "$lua_dir/amgraph.lua" "$work_dir/lua/"
mkdir -p "$work_dir/lua/countries"
cp "$lua_dir/countries/"*.lua "$work_dir/lua/countries/"

# Which country's rules the nodes in this graph are read under. Ways carry
# their own attribution from infra/official_access.py and need none; nodes do
# not, so a graph is built for one country and says which. An unrecognised code
# leaves every node closed to our classes rather than borrowing a neighbour's
# sign vocabulary, which is the conservative half of "one graph per country".
AMGRAPH_COUNTRY="${AMGRAPH_COUNTRY:-NL}"

in_container() {
  docker run --rm \
    -v "$work_dir:/data" \
    -e UPSTREAM_GRAPH_LUA=/data/lua/graph.lua \
    -e AMGRAPH_ACCESS_LUA=/data/lua/access.lua \
    -e AMGRAPH_COUNTRY="$AMGRAPH_COUNTRY" \
    -w /data \
    "$VALHALLA_IMAGE" "$@"
}

echo "==> Writing config"
in_container valhalla_build_config \
  --mjolnir-tile-dir /data/valhalla/tiles \
  --mjolnir-tile-extract /data/valhalla/tiles.tar \
  --mjolnir-admin /data/valhalla/admin.sqlite \
  --mjolnir-timezone /data/valhalla/tz_world.sqlite \
  --mjolnir-graph-lua-name /data/lua/amgraph.lua \
  --service-limits-max-distance-disable-hierarchy-culling 200000 \
  > "$work_dir/valhalla.json"

# Why the hierarchy-culling limit above is not a default.
#
# Valhalla's bidirectional A* climbs to higher road-class hierarchy levels on
# long routes. Almost every Dutch trunk road is an autoweg carrying
# motorroad=yes, and NL-ACC-01 strips every one of our classes off those, so for
# the two-wheelers the top hierarchy level is close to empty and the search
# finds nothing beyond roughly 30 km. Utrecht to Amsterdam failed outright.
#
# `disable_hierarchy_pruning` fixes it, but the option is silently ignored
# unless this limit is above the route's arc distance, and it ships as 0.

echo "==> Building admin areas (needed for country-specific access rules)"
in_container valhalla_build_admins --config /data/valhalla.json "/data/$(basename "$extract")"

# From empty, and that means the archive as well as the directory.
#
# The config names a tile directory *and* a tile extract, and Valhalla reads
# the archive in preference to the directory wherever both exist. So the
# enhance phase of a build reads last build's tiles.tar rather than the tiles
# it has just written, and aborts on the first mismatch: "Mismatch in end
# offset … Tile file might be corrupted". Deleting the directory alone does
# not help, which is what made this look like stale tiles twice over.
#
# Both are derived entirely from this script. The archive is rebuilt from the
# fresh tiles at the packing step below.
#
# The dev router is stopped first because it has that archive memory-mapped,
# and unlinking a mapped file leaves it serving bytes that no longer exist.
if docker ps -q --filter "name=^/${VALHALLA_CONTAINER}$" | grep -q .; then
  echo "==> Stopping the dev router; it has tiles.tar mapped"
  docker rm -f "$VALHALLA_CONTAINER" >/dev/null
fi

echo "==> Building tiles"
rm -rf "$work_dir/valhalla/tiles" "$work_dir/valhalla/tiles.tar"
# The default uses every core. On a Docker Desktop bind mount that produced
# overlapping enhance-stage temporary files and a reproducible 160-byte tile
# offset mismatch. A legal graph is rebuilt weekly, not interactively; the
# slower serial write is preferable to a graph that cannot be validated.
in_container valhalla_build_tiles --concurrency 1 \
  --config /data/valhalla.json "/data/$(basename "$extract")"

# A running valhalla_service mmaps tiles.tar, so rewriting it underneath one
# does not swap the graph: it corrupts the map the live process is reading.
# The service keeps answering /status, then returns "Tile file might be
# corrupted" and segfaults. Stop it first; dev-serve.sh starts it again.
if docker ps -q --filter "name=^/${VALHALLA_CONTAINER}$" | grep -q .; then
  echo "==> Stopping the dev router; it has tiles.tar mapped"
  docker rm -f "$VALHALLA_CONTAINER" >/dev/null
fi

# --overwrite, because without it this step fails the moment a tiles.tar
# exists, which is every rebuild after the first. The tiles above are already
# rebuilt at that point, so the failure leaves fresh tiles on disk and a stale
# archive being served — a rules change appears to have been built and has not.
echo "==> Packing tiles into a single archive"
in_container /bin/bash -c "cd /data && valhalla_build_extract --config /data/valhalla.json --overwrite -v"

echo "==> Done. Tiles in $work_dir/valhalla"
du -sh "$work_dir/valhalla" 2>/dev/null || true
