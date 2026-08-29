from __future__ import annotations

import sys
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[1] / "infra"
sys.path.insert(0, str(INFRA))

from artifacts import replace_atomically  # noqa: E402


def test_failed_generation_keeps_the_last_complete_artifact(tmp_path: Path) -> None:
    destination = tmp_path / "graph-input.pbf"
    destination.write_text("complete")

    def fail_after_partial_write(candidate: Path) -> None:
        candidate.write_text("partial")
        raise ValueError("new legal input was not understood")

    with pytest.raises(ValueError, match="not understood"):
        replace_atomically(destination, fail_after_partial_write)

    assert destination.read_text() == "complete"
    assert list(tmp_path.iterdir()) == [destination]


def test_successful_generation_replaces_the_artifact(tmp_path: Path) -> None:
    destination = tmp_path / "graph-input.osm.pbf"
    destination.write_text("old")

    def write_format_sensitive_artifact(candidate: Path) -> None:
        assert candidate.name.endswith(destination.name)
        candidate.write_text("new")

    replace_atomically(destination, write_format_sensitive_artifact)

    assert destination.read_text() == "new"
