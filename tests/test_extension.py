"""Integration tests for the Sphinx extension."""

import json
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock

from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from sphinx_literalizer import setup


def _build_sphinx(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    json_data: object,
    directive_options: str,
) -> list[str]:
    """Build a minimal Sphinx project and return literal block texts."""
    srcdir = tmp_path / "src"
    srcdir.mkdir()
    (srcdir / "conf.py").write_text(
        "extensions = ['sphinx_literalizer']\n",
    )
    (srcdir / "data.json").write_text(
        json.dumps(json_data),
    )
    option_lines = "\n".join(
        f"   {line.strip()}" for line in directive_options.splitlines()
    )
    rst = f"Test\n====\n\n.. literalizer:: data.json\n{option_lines}\n"
    (srcdir / "index.rst").write_text(rst)
    app = make_app(
        srcdir=srcdir,
        builddir=tmp_path / "build",
        buildername="html",
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    assert not app.warning.getvalue()

    doctree = app.env.get_doctree("index")
    return [node.astext() for node in doctree.findall(nodes.literal_block)]


def test_boolean_array_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON boolean array renders as Python booleans."""
    blocks = _build_sphinx(
        make_app=make_app,
        tmp_path=tmp_path,
        json_data=[True, False, True],
        directive_options="   :language: py",
    )
    (text,) = blocks
    assert "True," in text
    assert "False," in text


def test_array_of_arrays_typescript(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Nested arrays render in TypeScript syntax."""
    blocks = _build_sphinx(
        make_app=make_app,
        tmp_path=tmp_path,
        json_data=[["a", 1.0]],
        directive_options="   :language: ts",
    )
    (text,) = blocks
    assert '["a", 1.0],' in text


def test_prefix_spaces(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :prefix: option prepends spaces to each output line."""
    blocks = _build_sphinx(
        make_app=make_app,
        tmp_path=tmp_path,
        json_data=[1],
        directive_options="   :language: py\n   :prefix: 4",
    )
    (text,) = blocks
    assert all(line.startswith("    ") for line in text.splitlines())


def test_prefix_tabs(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :prefix-char: tabs option uses tab characters."""
    blocks = _build_sphinx(
        make_app=make_app,
        tmp_path=tmp_path,
        json_data=[1],
        directive_options="   :language: go\n   :prefix: 2\n   :prefix-char: tabs",
    )
    (text,) = blocks
    assert all(line.startswith("\t\t") for line in text.splitlines())


def test_wrap_adds_brackets(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :wrap: flag wraps output in brackets."""
    blocks = _build_sphinx(
        make_app=make_app,
        tmp_path=tmp_path,
        json_data=[1, 2],
        directive_options="   :language: py\n   :wrap:",
    )
    (text,) = blocks
    assert text.startswith("[")


def test_no_wrap_by_default(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :wrap:, output is not wrapped in brackets."""
    blocks = _build_sphinx(
        make_app=make_app,
        tmp_path=tmp_path,
        json_data=[1, 2],
        directive_options="   :language: py",
    )
    (text,) = blocks
    assert not text.startswith("[")


def test_setup_returns_metadata() -> None:
    """setup() registers the directive and returns correct metadata."""
    app = MagicMock()
    result = setup(app=app)
    app.add_directive.assert_called_once_with(
        "literalizer",
        # Don't check the exact class to avoid tight coupling.
        app.add_directive.call_args[0][1],
    )
    assert result["parallel_read_safe"] is True
    assert result["parallel_write_safe"] is True
    assert "version" in result
