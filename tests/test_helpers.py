"""Shared helpers for extension integration tests."""

from pathlib import Path

from sphinx.testing.util import SphinxTestApp
from sphinx.util.console import strip_colors


def assert_directive_error(
    *,
    app: SphinxTestApp,
    source_directory: Path,
    line: int,
    message: str,
) -> None:
    """Assert that building *app* reports one directive error.

    The error is expected against ``index.rst`` at *line* -- the first
    line of the offending directive -- so an author can find the block
    that failed without searching the document for it.

    Every directive error also ends with the data file the directive
    names, so the expectation is completed from the argument written on
    *line* rather than repeated in *message* at every call site.
    """
    app.build()
    document = source_directory / "index.rst"
    directive = document.read_text(encoding="utf-8").splitlines()[line - 1]
    _, data_file = directive.split(sep="::", maxsplit=1)
    expected = (
        f"{document}:{line}: ERROR: {message} "
        f"(in '{data_file.strip()}') [docutils]"
    )
    reported = strip_colors(app.warning.getvalue()).splitlines()
    assert reported == [expected]
