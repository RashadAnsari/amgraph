"""Write the manifest that travels inside a graph release.

The access rules are read twice: `valhalla/lua/countries/nl.lua` decides access
when the tiles are built, and `amgraph_rules.countries.nl` carries the same
classes, carriers and limits for whoever serves them. A consumer pins the
package by tag, and a pin can lag the graph it is asked to serve.

`rules_version` is what makes that visible. It is read from the country module
here rather than passed in, so the number in the manifest is the number the
tiles were actually built under, and anyone deploying a release can refuse one
whose value does not match their own. That check is the reason this file exists;
everything else in it is for reading a live host's logs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from amgraph_rules.countries.nl import RULES_VERSION


def _wkd_release(work: Path) -> str | None:
    """Which monthly authority release the overlay was matched from.

    Recorded because it is discovered at build time rather than pinned, so
    without this there is no way to tell afterwards which month's decisions a
    given graph is carrying. Deliberately not inside `wkd/`, which the build
    deletes to free disk before the tiles are written.
    """
    stamp = work / "wkd-release.txt"
    return stamp.read_text().strip() if stamp.exists() else None


def build(release: int, commit: str, extract_url: str, work: Path) -> dict:
    return {
        "release": release,
        "rules_version": RULES_VERSION,
        "graph_commit": commit,
        "extract_url": extract_url,
        "wkd_release": _wkd_release(work),
        "valhalla_version": _valhalla_version(),
        "built_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }


def _valhalla_version() -> str:
    """From build.sh, so the manifest cannot claim a version we did not use."""
    build_sh = Path(__file__).resolve().parents[1] / "valhalla" / "build.sh"
    for line in build_sh.read_text().splitlines():
        if line.startswith("VALHALLA_VERSION="):
            return line.split("=", 1)[1].strip().strip('"')
    raise ValueError("build.sh no longer declares VALHALLA_VERSION")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", required=True, type=int)
    parser.add_argument("--extract-url", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    work = Path(__file__).resolve().parent / "work"
    manifest = build(args.release, commit, args.extract_url, work)

    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, indent=2, sort_keys=True))
