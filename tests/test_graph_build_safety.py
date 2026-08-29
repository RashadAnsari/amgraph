from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTAINER_NAME = "amgraph-valhalla"


def test_graph_build_stops_the_container_that_serves_the_graph() -> None:
    """A live router memory-maps tiles.tar; rewriting it under one corrupts it.

    The container name is the coupling: the build can only stop a running
    router if it knows what that router is called, and the failure is silent
    because the service keeps answering `/status` while serving bytes that no
    longer exist.
    """
    build = (REPOSITORY_ROOT / "valhalla/build.sh").read_text()

    assert f'VALHALLA_CONTAINER="{CONTAINER_NAME}"' in build
    assert "valhalla_build_tiles --concurrency 1" in build


def test_every_input_the_overlay_refuses_to_run_without_is_fetched() -> None:
    """The overlay's inputs went out of step with its fetch once, silently.

    `official_access.py` reads the sign register and exits if it is absent. The
    target that fetches it was deleted while that requirement stayed, so the
    build failed every week for three weeks with nobody looking. This is cheap
    and it makes the next such omission fail here rather than in the pipeline.
    """
    overlay = (REPOSITORY_ROOT / "infra/official_access.py").read_text()
    makefile = (REPOSITORY_ROOT / "infra/Makefile").read_text()

    assert 'here / "work" / "ndw" / "signs.geojson"' in overlay
    assert "$(WORK)/ndw/signs.geojson" in makefile
    # A prerequisite, not a separate step: the overlay's own error message tells
    # the reader to run official-data, so official-data has to be enough.
    assert "official-data: sign-data" in makefile
