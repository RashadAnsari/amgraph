"""Reject partial, stale or unaudited combined graph inputs."""

import argparse
import json
from pathlib import Path

from amgraph_rules.countries import modelled_countries
from prepare_country import Access, digest, require_current


def check(work: Path, extract: Path):
    report = json.loads((work / "combined.json").read_text())
    expected = {country.code: country for country in modelled_countries()}
    if set(report["countries"]) != set(expected):
        raise ValueError("combined input must contain every supported country, with no extras")
    if report["enriched_sha256"] != digest(extract):
        raise ValueError("combined input changed after the audited merge")
    for code, country in expected.items():
        require_current(country)
        Access(code)
        source = report["countries"][code]
        audit = source["audit"]
        if (
            source["rules_version"] != country.rules_version
            or audit.get("rules_version") != country.rules_version
            or audit.get("country") != code
            or audit.get("enriched_sha256") != source["enriched_sha256"]
            or audit.get("ways", 0) <= 0
            or report["ways"].get(code, 0) <= 0
        ):
            raise ValueError(f"{code} lacks matching nonempty audit evidence")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--extract", required=True, type=Path)
    args = parser.parse_args()
    check(args.work, args.extract)
