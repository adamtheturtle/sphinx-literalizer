"""Integration tests for the Sphinx extension."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock

from sphinx.testing.util import SphinxTestApp

from sphinx_literalizer import setup


def test_boolean_array_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON boolean array renders the same as an equivalent code-block."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        json.dumps([True, False, True]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: py
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. code-block:: py

           True,
           False,
           True,
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_array_of_arrays_typescript(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Nested arrays render the same as an equivalent TypeScript code-block."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        json.dumps([["a", 1.0]]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: ts
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. code-block:: ts

           ["a", 1.0],
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_prefix_spaces(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :prefix: option prepends spaces to each output line."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(json.dumps([1]))
    (source_directory / "index.rst").write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: py
           :prefix: 4
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    assert "<span></span>    " in content_html


def test_prefix_tabs(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :prefix-char: tabs option prepends tab characters."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(json.dumps([1]))
    (source_directory / "index.rst").write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :prefix: 2
           :prefix-char: tabs
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    assert "\t\t" in content_html


def test_wrap_adds_brackets(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :wrap: flag produces the same output as a wrapped code-block."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(json.dumps([1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: py
           :wrap:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. code-block:: py

           [
               1,
               2,
           ]
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_no_wrap_by_default(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :wrap:, output matches an unwrapped code-block."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(json.dumps([1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: py
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. code-block:: py

           1,
           2,
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_setup_returns_metadata() -> None:
    """setup() registers the directive and returns correct metadata."""
    app = MagicMock()
    result = setup(app=app)
    app.add_directive.assert_called_once_with(
        "literalizer",
        app.add_directive.call_args[0][1],
    )
    assert result["parallel_read_safe"] is True
    assert result["parallel_write_safe"] is True
    assert "version" in result
