"""Safe replacement of derived infrastructure artefacts."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path


def replace_atomically(destination: Path, write: Callable[[Path], None]) -> None:
    """Keep the last complete artefact when generating its replacement fails."""
    # Format-sensitive writers such as Osmium infer their output encoding from
    # the final suffix, so keep the destination's complete name at the end.
    temporary = destination.with_name(f".{os.getpid()}.tmp.{destination.name}")
    temporary.unlink(missing_ok=True)
    try:
        write(temporary)
        temporary.replace(destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
