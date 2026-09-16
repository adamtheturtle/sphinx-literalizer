"""Input-format and preamble integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_toml_input_format(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A .toml file is auto-detected and parsed as TOML."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.toml").write_text(data='key = "value"\n')
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.toml
           :language: python
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    literal_blocks = list(doctree.findall(condition=nodes.literal_block))
    (literal_block,) = literal_blocks
    assert '"value"' in literal_block.astext()
    app.cleanup()


def test_json5_input_format(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A .json5 file is auto-detected and parsed as JSON5."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json5").write_text(data='{key: "value"}')
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json5
           :language: python
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    literal_blocks = list(doctree.findall(condition=nodes.literal_block))
    (literal_block,) = literal_blocks
    assert '"value"' in literal_block.astext()
    app.cleanup()


def test_explicit_input_format_overrides_extension(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :input-format: option overrides file extension detection."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    # Write YAML content with a .txt extension
    _ = (source_directory / "data.txt").write_text(data="- 1\n- 2\n")
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.txt
           :language: python
           :input-format: yaml
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    app.cleanup()


def test_unknown_extension_without_input_format_errors(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unrecognized extension without :input-format: raises an
    error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.dat").write_text(data="[1]")
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.dat
           :language: python
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Cannot determine input format from the file extension. "
            "Use the :input-format: option."
        ),
    )


def test_language_with_no_pygments_lexer(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Languages with pygments_name=None use 'text' for highlighting."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: dhall
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    literal_blocks = list(doctree.findall(condition=nodes.literal_block))
    (literal_block,) = literal_blocks
    assert literal_block["language"] == "text"
    app.cleanup()


def test_include_preamble_go(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :include-preamble: flag prepends import / package lines."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :include-delimiters:
           :include-preamble:
           :variable-name: x
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    literal_blocks = list(
        doctree.findall(condition=nodes.literal_block),
    )
    (literal_block,) = literal_blocks
    text = literal_block.astext()
    assert text.startswith("package main\n\n")
    assert "x := map[string]string{" in text
    app.cleanup()


def test_include_preamble_no_effect_ruby(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :include-preamble: flag has no effect when the language has
    no preamble.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: ruby
           :include-preamble:
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

    _ = source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: ruby

           1,
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_no_include_preamble_by_default(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :include-preamble:, the preamble is not in the output
    even for languages that have one.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :include-delimiters:
           :variable-name: x
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    literal_blocks = list(
        doctree.findall(condition=nodes.literal_block),
    )
    (literal_block,) = literal_blocks
    text = literal_block.astext()
    assert not text.startswith("package main")
    assert "x := map[string]string{" in text
    app.cleanup()
