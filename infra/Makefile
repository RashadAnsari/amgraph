# Map data and the routing graph.
.DEFAULT_GOAL := help
.PHONY: help extract graph clean-work size official-data sign-data official-access supported-area legal-zones

# The road authority's own access decisions, published monthly as public domain.
#
# WKD_RELEASE is discovered rather than pinned. The graph is rebuilt weekly
# precisely because the underlying data moves, and a pinned date here would go
# quietly stale while every build kept passing. Files are named DD-MM-YYYY.zip,
# which does not sort, so the awk rewrites them to YYYY-MM-DD to pick the
# newest. Set WKD_RELEASE explicitly to reproduce an older build.
WKD_BASE ?= https://downloads.rijkswaterstaatdata.nl/wkd/geogegevens/Shape
WKD_RELEASE ?=

EXTRACT_URL ?= https://download.geofabrik.de/europe/netherlands-latest.osm.pbf
WORK := work
SUPPORTED_AREA_URL ?= https://api.pdok.nl/kadaster/brk-bestuurlijke-gebieden/ogc/v1/collections/landgebied/items?f=json&limit=10

help: ## Show this list
	@grep -hE '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/' \
		| awk -F'\t' '{printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

extract: ## Download a fresh OSM extract
	mkdir -p $(WORK)
	curl -fL --progress-bar -o $(WORK)/$(notdir $(EXTRACT_URL)) $(EXTRACT_URL)

graph: ## Build the routing graph from the current extract
	../valhalla/build.sh

official-data: sign-data ## Download the road authority's access and built-up-area decisions
	# Rijkswaterstaat's Wegkenmerkendatabase, public domain, refreshed monthly.
	# Verkeerstypen says which classes may use each NWB section; Komgrenzen says
	# which sections lie inside the bebouwde kom.
	@set -e; \
	release="$(WKD_RELEASE)"; \
	if [ -z "$$release" ]; then \
		release=$$(curl -fsS --max-time 60 "$(WKD_BASE)/Verkeerstypen/" \
			| grep -oE '[0-9]{2}-[0-9]{2}-[0-9]{4}\.zip' | sort -u \
			| awk -F'[-.]' '{printf "%s%s%s %s-%s-%s\n", $$3, $$2, $$1, $$1, $$2, $$3}' \
			| sort | tail -1 | cut -d' ' -f2); \
	fi; \
	if [ -z "$$release" ]; then \
		echo "Could not discover a WKD release from $(WKD_BASE)." >&2; \
		echo "Pin one instead: make infra-official-data WKD_RELEASE=01-08-2026" >&2; \
		exit 1; \
	fi; \
	echo "==> WKD release $$release"; \
	mkdir -p $(WORK); \
	printf '%s\n' "$$release" > $(WORK)/wkd-release.txt; \
	mkdir -p $(WORK)/wkd; \
	for set in Verkeerstypen Komgrenzen; do \
		curl -fL --progress-bar -o "$(WORK)/wkd/$$set.zip" \
			"$(WKD_BASE)/$$set/$$release.zip"; \
		rm -rf "$(WORK)/wkd/$$set"; \
		unzip -oq "$(WORK)/wkd/$$set.zip" -d "$(WORK)/wkd/$$set"; \
		rm -f "$(WORK)/wkd/$$set.zip"; \
	done

sign-data: ## Download the national traffic-sign register (about 1 GB)
	# Every sign standing on a Dutch road, with its RVV code and position.
	# NDW publishes it daily as open data, no key.
	#
	# A prerequisite of official-data rather than a step somebody remembers,
	# because without it the matcher does not fail: it stops refusing, and the
	# 17,094 use_sidepath lifts and 2,469 path openings the signs contradict go
	# straight into the graph with every test still green. official_access.py
	# now refuses outright instead, and its error message names this target's
	# parent, so the two must not come apart again.
	mkdir -p $(WORK)/ndw
	curl -fL --progress-bar -o $(WORK)/ndw/signs.geojson \
		"https://data.ndw.nu/api/rest/static-road-data/traffic-signs/v4/current-state?f=geojson"

supported-area: ## Download the official BRK boundary of the Netherlands
	mkdir -p $(WORK)/boundaries
	curl -fL --progress-bar -o $(WORK)/boundaries/netherlands.geojson \
		'$(SUPPORTED_AREA_URL)'

legal-zones: ## Build conservative municipal vehicle-rule boundaries
	mkdir -p $(WORK)/boundaries/municipalities
	curl -fL --progress-bar -o $(WORK)/boundaries/municipalities/amsterdam.geojson \
		'https://api.pdok.nl/kadaster/brk-bestuurlijke-gebieden/ogc/v1/collections/gemeentegebied/items?f=json&bbox=4.7,52.25,5.1,52.5&limit=100'
	curl -fL --progress-bar -o $(WORK)/boundaries/municipalities/den-haag.geojson \
		'https://api.pdok.nl/kadaster/brk-bestuurlijke-gebieden/ogc/v1/collections/gemeentegebied/items?f=json&bbox=4.1,51.9,4.5,52.2&limit=100'
	curl -fL --progress-bar -o $(WORK)/boundaries/municipalities/nijmegen.geojson \
		'https://api.pdok.nl/kadaster/brk-bestuurlijke-gebieden/ogc/v1/collections/gemeentegebied/items?f=json&bbox=5.7,51.7,6.0,52.0&limit=100'
	curl -fL --progress-bar -o $(WORK)/boundaries/municipalities/utrecht.geojson \
		'https://api.pdok.nl/kadaster/brk-bestuurlijke-gebieden/ogc/v1/collections/gemeentegebied/items?f=json&bbox=5.0,52.0,5.3,52.2&limit=100'
	# The project's interpreter, not the system one: this reads the municipal
	# rules straight out of the country module so the two cannot drift.
	cd .. && uv run python infra/legal_zones.py \
		infra/$(WORK)/boundaries/municipalities/*.geojson \
		--output infra/$(WORK)/boundaries/legal-zones.geojson

official-access: supported-area legal-zones ## Match authority decisions and legal boundaries onto OSM
	# Writes the authority verdict for the Lua tests and an enriched PBF for the
	# graph. The latter also attributes every complete way to the BRK boundary.
	cd .. && uv run python infra/official_access.py

size: ## How much disk the working set uses
	@du -sh $(WORK)/* 2>/dev/null || echo "nothing built yet"

clean-work: ## Delete extracts and tiles. They are large and rebuildable.
	rm -rf $(WORK)
