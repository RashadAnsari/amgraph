"""Prepare and audit every registered country for the single combined graph."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

import osmium

from amgraph_rules.countries import modelled_countries
from audit_country import audit
from merge_countries import merge, source_paths
from prepare_country import ROOT, digest, prepare, require_current


def run(command, **kwargs):
    subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def prepare_all(work: Path, download: bool):
    for country in modelled_countries():
        require_current(country)
        directory, _, module = source_paths(work)[country.code]
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Preparing {country.code}", flush=True)
        if hasattr(module, "PREPARE_TARGETS"):
            targets = module.PREPARE_TARGETS if download else (module.PREPARE_TARGETS[-1],)
            env = {**os.environ, "AMGRAPH_WORK": str(directory)}
            relative = directory.relative_to(ROOT / "infra")
            run(
                [
                    "make",
                    "-C",
                    "infra",
                    f"WORK={relative}",
                    f"EXTRACT_URL={module.EXTRACT_URL}",
                    *targets,
                ],
                env=env,
            )
        elif download:
            run(
                [
                    "uv",
                    "run",
                    "python",
                    "infra/prepare_country.py",
                    "--country",
                    country.code,
                    "--work",
                    str(directory),
                    "--download",
                ]
            )
        else:
            prepare(country.code, directory)


def audit_all(work: Path):
    for country in modelled_countries():
        require_current(country)
        directory, extract, module = source_paths(work)[country.code]
        if not extract.is_file():
            raise ValueError(f"missing {country.code} input: {extract}")
        if hasattr(module, "AUDIT_TESTS"):
            # The authority-specific assertions remain attached to that data
            # source. Required input existence is checked before pytest so a
            # missing extract cannot turn a skipped test into a passing gate.
            for name in ("official-access.tsv", "boundaries/legal-zones.geojson"):
                if not (directory / name).is_file():
                    raise ValueError(f"missing audit evidence: {directory / name}")
            run(
                ["uv", "run", "pytest", "-m", "graph", *module.AUDIT_TESTS, "-q"],
                env={**os.environ, "AMGRAPH_EXTRACT": str(extract)},
            )

            class Count(osmium.SimpleHandler):
                def __init__(self):
                    super().__init__()
                    self.ways = 0

                def way(self, way):
                    self.ways += bool(way.tags.get("highway"))

            counter = Count()
            counter.apply_file(str(extract))
            if not counter.ways:
                raise ValueError("an empty input is not an audit")
            report = {
                "country": country.code,
                "rules_version": country.rules_version,
                "enriched_sha256": digest(extract),
                "ways": counter.ways,
                "audit_tests": module.AUDIT_TESTS,
            }
            (directory / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
        else:
            audit(country.code, directory)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "audit", "merge"))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--work", type=Path, default=ROOT / "infra/work")
    args = parser.parse_args()
    work = args.work.resolve()
    if args.action == "prepare":
        prepare_all(work, args.download)
    elif args.action == "audit":
        audit_all(work)
    else:
        merge(work)
