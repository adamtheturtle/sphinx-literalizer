"""Integration tests for the Sphinx extension."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp


def test_source_attribute_is_absolute(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literal_block node's source attribute is an absolute path.

    This matches Sphinx's built-in LiteralInclude behaviour, which sets
    ``source`` to an absolute path via ``env.relfn2path()``.  Code that
    inspects doctree nodes can therefore rely on the path being absolute
    without needing its own relative→absolute resolution step.
    """
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

    doctree = app.env.get_doctree("index")
    literal_blocks = list(doctree.findall(nodes.literal_block))
    (literal_block,) = literal_blocks
    source = literal_block["source"]
    assert Path(source).is_absolute()
    app.cleanup()


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
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. code-block:: python

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
           :language: typescript
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

        .. code-block:: typescript

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
    source_file = source_directory / "index.rst"
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
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

    (source_directory / "expected.py").write_text("    1,\n")
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalinclude:: expected.py
           :language: python
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


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
    source_file = source_directory / "index.rst"
    source_file.write_text(
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

    (source_directory / "expected.go").write_text("\t\t1,\n")
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalinclude:: expected.go
           :language: go
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


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
           :language: python
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

        .. code-block:: python

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


def test_yaml_file_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A YAML sequence renders the same as an equivalent Python code-block."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        dedent("""\
            - true
            - false
            - true
        """)
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
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
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. code-block:: python

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
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. code-block:: python

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


def test_date_format_option(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :date-format: option formats dates using the given strftime string."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text("- 2026-03-15\n")
    source_file = source_directory / "index.rst"
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: python
           :date-format: %d/%m/%Y
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

        .. code-block:: python

           "15/03/2026",
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_date_format_default_is_isoformat(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :date-format:, dates are formatted as ISO 8601 strings."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text("- 2026-03-15\n")
    source_file = source_directory / "index.rst"
    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
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
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           "2026-03-15",
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html
