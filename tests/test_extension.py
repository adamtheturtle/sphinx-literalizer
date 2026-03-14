"""Integration tests for the Sphinx extension."""

from collections.abc import Callable
from pathlib import Path

from sphinx.testing.util import SphinxTestApp


def test_build_documentation_with_extension(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """With the extension enabled, Sphinx can build HTML documentation."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(
        "extensions = ['sphinx_literalizer']\n",
    )
    (srcdir / "index.rst").write_text(
        "Test\n====\n\nHello, world.\n",
    )
    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="html",
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    index_html = (tmp_path / "build" / "html" / "index.html").read_text()
    assert "Hello, world" in index_html
