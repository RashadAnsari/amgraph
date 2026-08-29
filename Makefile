# amgraph-graph. Run `make` for the list.
#
# Every target here is also what CI runs, so a green laptop and a green
# pipeline mean the same thing.

.DEFAULT_GOAL := help
.PHONY: help deps rules lint format format-check test test-audit verify infra-%

help: ## Show this list
	@grep -hE '^[a-z%-]+:.*?## ' $(MAKEFILE_LIST) infra/Makefile \
		| sed 's/:.*## /\t/' | sort | awk -F'\t' '{printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

deps: ## Install Python dependencies
	uv sync

rules: ## Unit-test the access rules (no graph, no extract, no network)
	valhalla/lua/spec/run.sh

lint: ## Ruff checks
	uv run ruff check .

format: ## Format Python sources
	uv run ruff format .

format-check: ## Fail if anything is unformatted
	uv run ruff format --check .

test: ## Unit tests that need nothing built
	uv run pytest -q

test-audit: ## Every access-tag combination in the country, against the extract
	# Not a sample. 2.8 million highway ways collapse to about fifteen thousand
	# distinct combinations of the tags the rules read, so all of them can be
	# checked. Needs the enriched extract on disk, not a running router, and it
	# is the only gate that covers combinations no route happens to touch.
	uv run pytest -m graph tests/test_access_rules.py tests/test_official_overlay.py -q

verify: deps rules lint format-check test ## Everything CI checks before it spends an hour on tiles

infra-%: ; @$(MAKE) -C infra $*
