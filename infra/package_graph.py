"""Create the single release ZIP from its complete country-indexed manifest."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from amgraph_rules.countries import modelled_countries
from artifacts import replace_atomically
from prepare_country import ROOT, digest


def package(work: Path, output: Path):
    manifest = json.loads((work / "manifest.json").read_text())
    expected = {country.code for country in modelled_countries()}
    if set(manifest["countries"]) != expected:
        raise ValueError("a release ZIP must cover every supported country")
    files = {
        "manifest.json",
        "valhalla.json",
        "valhalla/tiles.tar",
        "valhalla/admin.sqlite",
        manifest["legal_zones"],
        *[c["boundary"] for c in manifest["countries"].values()],
    }
    hashes = {
        "valhalla/tiles.tar": manifest["build"]["tiles_sha256"],
        manifest["legal_zones"]: manifest["legal_zones_sha256"],
    }
    hashes.update({c["boundary"]: c["boundary_sha256"] for c in manifest["countries"].values()})
    for name in files:
        path = work / name
        if not path.resolve().is_relative_to(work.resolve()) or not path.is_file():
            raise ValueError(f"missing or unsafe release path: {name}")
        if name in hashes and digest(path) != hashes[name]:
            raise ValueError(f"release content changed: {name}")

    def write(candidate):
        with zipfile.ZipFile(
            candidate, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1
        ) as archive:
            for name in sorted(files):
                archive.write(work / name, name)
            archive.write(ROOT / "NOTICE.md", "NOTICE.md")
        with zipfile.ZipFile(candidate) as archive:
            if archive.testzip() is not None:
                raise ValueError("release ZIP failed its integrity check")

    replace_atomically(output, write)
    print(f"Wrote {output}: {', '.join(sorted(expected))}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, default=ROOT / "infra/work")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    package(args.work, args.output)
