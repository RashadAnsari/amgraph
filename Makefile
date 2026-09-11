# amgraph-graph. Run `make` for the list.
#
# Every target here is also what CI runs, so a green laptop and a green
# pipeline mean the same thing.

.DEFAULT_GOAL := help
.PHONY: help deps rules lint format format-check test test-audit verify country-prepare country-merge country-graph infra-%


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

test-audit: ## Audit every supported country's complete enriched extract
	uv run python infra/all_countries.py audit

country-prepare: ## Fetch and enrich all supported countries
	uv run python infra/all_countries.py prepare --download

country-merge: ## Merge all audited countries into one attributed graph input
	uv run python infra/all_countries.py merge

country-graph: country-merge ## Build one graph containing all supported countries
	valhalla/build.sh

verify: deps rules lint format-check test ## Everything CI checks before it spends an hour on tiles

infra-%: ; @$(MAKE) -C infra $*
