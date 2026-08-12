# pylint: disable=too-many-lines
"""Integration tests for the Sphinx extension."""

import json
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock

import pytest
from docutils import nodes
from sphinx.errors import ExtensionError
from sphinx.testing.util import SphinxTestApp
from sphinx.util.console import strip_colors


def _assert_directive_error(
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
    """
    app.build()
    document = source_directory / "index.rst"
    expected = f"{document}:{line}: ERROR: {message} [docutils]"
    reported = strip_colors(app.warning.getvalue()).splitlines()
    assert reported == [expected]


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
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
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

    doctree = app.env.get_doctree(docname="index")
    literal_blocks = list(doctree.findall(condition=nodes.literal_block))
    (literal_block,) = literal_blocks
    source = literal_block["source"]
    assert Path(source).is_absolute()
    app.cleanup()


def test_literalizer_call_pre_indent_level(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :pre-indent-level: option indents the generated calls."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: f
           :parameter-names: flag,count
           :per-element:
           :pre-indent-level: 2
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
    text = literal_block.astext()
    assert text.startswith("        f(")
    app.cleanup()


def test_boolean_array_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON boolean array renders the same as an equivalent code-
    block.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[True, False, True]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
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
        data=dedent(
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
    """Nested arrays render the same as an equivalent TypeScript code-
    block.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[["a", 1.0]]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
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
        data=dedent(
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


def test_pre_indent_level_spaces(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :pre-indent-level: option prepends indentation to each
    output line.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :pre-indent-level: 1
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

    (source_directory / "expected.py").write_text(data="    1,\n")
    source_file.write_text(
        data=dedent(
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


def test_pre_indent_level_tabs(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :indent-char: tabs option uses tab characters for
    indentation.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :pre-indent-level: 2
           :indent: 1
           :indent-char: tabs
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

    (source_directory / "expected.go").write_text(data="\t\t1,\n")
    source_file.write_text(
        data=dedent(
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


def test_indent_default_uses_library_default(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """When neither :indent: nor :indent-char: is specified, the
    language's own default indent is used.

    Go defaults to a single tab, so the output should use tabs rather
    than the four-space fallback that was previously hard-coded.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :include-delimiters:
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

    (source_directory / "expected.go").write_text(
        data='map[string]int{\n\t"a": 1,\n}\n',
    )
    source_file.write_text(
        data=dedent(
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


def test_indent_only_uses_spaces(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """When only :indent: is specified (without :indent-char:), spaces
    are used with the given count.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :indent: 2
           :include-delimiters:
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

    (source_directory / "expected.go").write_text(
        data='map[string]int{\n  "a": 1,\n}\n',
    )
    source_file.write_text(
        data=dedent(
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


def test_indent_char_only_uses_default_count(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """When only :indent-char: is specified (without :indent:), the
    default count of 4 is used with the given character.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :indent-char: tabs
           :include-delimiters:
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

    (source_directory / "expected.go").write_text(
        data='map[string]int{\n\t\t\t\t"a": 1,\n}\n',
    )
    source_file.write_text(
        data=dedent(
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


def test_include_delimiters_adds_brackets(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :include-delimiters: flag produces the same output as a
    wrapped code-block.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :include-delimiters:
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           (
               1,
               2,
           )
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
        data=dedent(
            text="""\
            - true
            - false
            - true
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
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
        data=dedent(
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


def test_date_format_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :date-format: python option renders dates as constructors."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            - 2024-01-15
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: python
           :date-format: python
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           datetime.date(year=2024, month=1, day=15),
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_date_format_iso_default(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :date-format:, dates render using the language's
    default date format.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            - 2024-01-15
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           datetime.date(year=2024, month=1, day=15),
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_date_format_iso_explicit(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :date-format: iso option explicitly selects ISO format."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            - 2024-01-15
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: bash
           :date-format: iso
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: bash

           "2024-01-15"
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_date_format_epoch(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :datetime-format: epoch option renders datetimes as epoch
    floats.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            - 2024-01-15T10:30:00+00:00
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: python
           :datetime-format: epoch
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           1705314600,
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_date_format_java_instant(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :date-format: java option renders dates for Java."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            - 2024-01-15
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: java
           :date-format: java
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: java

           LocalDate.of(2024, 1, 15)
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_swift_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the swift language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: swift
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: swift

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


def test_php_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the php language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: php
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: php

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


def test_variable_name_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :variable-name: option wraps output in a variable
    declaration.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :include-delimiters:
           :variable-name: my_list
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           my_list = (
               1,
               2,
           )
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_dart_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the dart language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: dart
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: dart

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


def test_julia_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the julia language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: julia
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: julia

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


def test_existing_variable_dart(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :existing-variable: flag produces a variable assignment
    instead of a declaration.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: dart
           :include-delimiters:
           :variable-name: myList
           :existing-variable:
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
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: dart
           :include-delimiters:
           :variable-name: myList
    """
        )
    )
    new_variable_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    new_variable_app.build()
    assert new_variable_app.statuscode == 0
    new_variable_html = (new_variable_app.outdir / "index.html").read_text()
    new_variable_app.cleanup()

    # Assignment (existing-variable) differs from declaration (new variable)
    assert content_html != new_variable_html


def test_modifiers_java(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :modifiers: option adds modifiers to a new variable
    declaration.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :include-delimiters:
           :variable-name: myList
           :modifiers: public, static, final,
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

    (source_directory / "expected.java").write_text(
        data=(
            "public static final int[] myList = new int[]{\n"
            "    1,\n"
            "    2\n"
            "};\n"
        )
    )
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalinclude:: expected.java
           :language: java
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_unsupported_modifier_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported modifier is reported as a directive error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :variable-name: my_list
           :modifiers: public
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="'public' is not a valid value.",
    )


def test_unsupported_modifier_error_lists_choices(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported modifier for a language that has modifiers lists
    the valid choices in the error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :variable-name: myList
           :modifiers: bogus
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "'bogus' is not a valid value. Choose from: final, private, "
            "protected, public, static."
        ),
    )


def test_modifiers_without_variable_name_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Using :modifiers: without :variable-name: is an error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :modifiers: public
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="':modifiers:' requires ':variable-name:'.",
    )


def test_modifiers_with_existing_variable_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Combining :modifiers: with :existing-variable: is an error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :variable-name: myList
           :existing-variable:
           :modifiers: public
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="':modifiers:' cannot be combined with ':existing-variable:'.",
    )


def test_modifiers_with_both_variable_forms_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Combining :modifiers: with :both-variable-forms: is an error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :variable-name: myList
           :both-variable-forms:
           :modifiers: public
           :wrap-in-file:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="':modifiers:' cannot be combined with ':both-variable-forms:'.",
    )


def test_rust_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the rust language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: rust

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


def test_elixir_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the elixir language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: elixir
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: elixir

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


def test_date_format_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :date-format: rust option renders dates as NaiveDate calls."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            - 2024-01-15
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: rust
           :date-format: rust
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: rust

           NaiveDate::from_ymd_opt(2024, 1, 15).unwrap(),
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_no_include_delimiters_by_default(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :include-delimiters:, output matches an unwrapped
    code-block.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
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
        data=dedent(
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


def test_mojo_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the mojo language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: mojo
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: mojo

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


def test_yaml_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the yaml language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: yaml
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

    (source_directory / "expected.yaml").write_text(data="1,\n2\n")
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalinclude:: expected.yaml
           :language: yaml
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_sequence_format_list_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :sequence-format: list option uses list delimiters for
    Python.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :include-delimiters:
           :sequence-format: list
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
        data=dedent(
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


def test_sequence_format_tuple_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :sequence-format: tuple option (Python default) uses tuple
    delimiters.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :include-delimiters:
           :sequence-format: tuple
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           (
               1,
               2,
           )
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_set_format_frozenset_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :set-format: frozenset option uses frozenset for Python."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            !!set
            a: null
            b: null
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: python
           :include-delimiters:
           :set-format: frozenset
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

    # Without frozenset option (default set) should differ
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: python
           :include-delimiters:
           :set-format: set
    """
        )
    )
    set_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    set_app.build()
    assert set_app.statuscode == 0
    set_html = (set_app.outdir / "index.html").read_text()
    set_app.cleanup()

    assert content_html != set_html


def test_bytes_format_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :bytes-format: option changes Python bytes formatting."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            !!binary |
              SGVsbG8=
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: python
           :bytes-format: hex
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    hex_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: python
           :bytes-format: python
    """
        )
    )
    python_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    python_app.build()
    assert python_app.statuscode == 0
    python_html = (python_app.outdir / "index.html").read_text()
    python_app.cleanup()

    assert hex_html != python_html


def test_fortran_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the fortran language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: fortran
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

    (source_directory / "expected.f90").write_text(
        data="fint(1_int64),\nfint(2_int64)\n"
    )
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalinclude:: expected.f90
           :language: fortran
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_norg_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the norg language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: norg
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

    (source_directory / "expected.norg").write_text(data="1,\n2\n")
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalinclude:: expected.norg
           :language: text
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_sequence_format_tuple_elixir(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :sequence-format: tuple option works for Elixir."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: elixir
           :include-delimiters:
           :sequence-format: tuple
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    tuple_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: elixir
           :include-delimiters:
           :sequence-format: list
    """
        )
    )
    list_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    list_app.build()
    assert list_app.statuscode == 0
    list_html = (list_app.outdir / "index.html").read_text()
    list_app.cleanup()

    assert tuple_html != list_html


def test_sequence_format_tuple_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :sequence-format: tuple option works for Rust."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :include-delimiters:
           :sequence-format: tuple
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    tuple_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :include-delimiters:
           :sequence-format: vec
    """
        )
    )
    vec_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    vec_app.build()
    assert vec_app.statuscode == 0
    vec_html = (vec_app.outdir / "index.html").read_text()
    vec_app.cleanup()

    assert tuple_html != vec_html


def test_objective_c_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the objective-c language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: objective-c
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: objective-c

           @1,
           @2,
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_sequence_format_array_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :sequence-format: array option works for Rust."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :include-delimiters:
           :sequence-format: array
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    array_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :include-delimiters:
           :sequence-format: vec
    """
        )
    )
    vec_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    vec_app.build()
    assert vec_app.statuscode == 0
    vec_html = (vec_app.outdir / "index.html").read_text()
    vec_app.cleanup()

    assert array_html != vec_html


def test_r_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the r language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: r
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: r

           1,
           2
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_unsupported_sequence_format_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported sequence-format is reported as a directive error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :sequence-format: vec
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support sequence-format 'vec'.",
    )


def test_unsupported_set_format_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported set-format is reported as a directive error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": [1]}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :set-format: frozenset
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'rust' does not support set-format 'frozenset'.",
    )


def test_unsupported_bytes_format_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported bytes-format is reported as a directive error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": [1]}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :bytes-format: python
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'rust' does not support bytes-format 'python'.",
    )


def test_comment_format_block(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :comment-format: option changes the comment style."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            # a comment
            key: value
        """
        )
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: go
           :comment-format: double_slash
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    slash_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: go
           :comment-format: block
    """
        )
    )
    block_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    block_app.build()
    assert block_app.statuscode == 0
    block_html = (block_app.outdir / "index.html").read_text()
    block_app.cleanup()

    assert slash_html != block_html


def test_unsupported_comment_format_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported comment-format is reported as a directive error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :comment-format: block
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support comment-format 'block'.",
    )


def test_variable_type_hints_always(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :variable-type-hints: always produces type-annotated output."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :variable-name: my_var
           :variable-type-hints: always
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    html = (app.outdir / "index.html").read_text()
    assert "my_var" in html
    app.cleanup()


def test_python_union_format(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Python annotation and union options reach literalizer."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(data="- hello\n- 42\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: python
           :variable-name: my_data
           :wrap-in-file:
           :include-delimiters:
           :variable-type-hints: always
           :annotation-evaluation: postponed
           :union-format: typing
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "from __future__ import annotations\n"
        "from typing import Union\n"
        "my_data: tuple[Union[str, int], ...] = (\n"
        '    "hello",\n'
        "    42,\n"
        ")"
    )
    app.cleanup()


def test_declaration_style_let(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :declaration-style: option changes the declaration keyword."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: javascript
           :variable-name: x
           :include-delimiters:
           :declaration-style: let
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    html = (app.outdir / "index.html").read_text()
    assert "let" in html
    app.cleanup()


def test_declaration_style_lazy_static_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Rust's :declaration-style: lazy_static wraps the value in
    ``LazyLock`` and adds the matching ``use`` to the preamble.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1, "b": 2}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :variable-name: CONFIG
           :declaration-style: lazy_static
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "use std::sync::LazyLock;" in text
    assert (
        "static CONFIG: LazyLock<HashMap<&str, i32>> = "
        "LazyLock::new(|| HashMap::from([" in text
    )
    app.cleanup()


def test_dict_format_map(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :dict-format: option changes how dicts are rendered."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: javascript
           :include-delimiters:
           :dict-format: map
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    html = (app.outdir / "index.html").read_text()
    assert "Map" in html
    app.cleanup()


def test_integer_format_hex(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :integer-format: option changes how integers are rendered."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[255]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: javascript
           :integer-format: hex
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    html = (app.outdir / "index.html").read_text()
    assert "0xff" in html or "0xFF" in html
    app.cleanup()


def test_numeric_separator_underscore(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :numeric-separator: option adds separators to numbers."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1000000]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: javascript
           :numeric-separator: underscore
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


def test_numeric_style_explicit(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :numeric-style: option controls numeric literal style."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[42]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: haskell
           :numeric-style: explicit
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


def test_string_format_single(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :string-format: option changes string quoting style."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=["hello"]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: javascript
           :string-format: single
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    html = (app.outdir / "index.html").read_text()
    assert "&#39;hello&#39;" in html or "'hello'" in html
    app.cleanup()


def test_string_format_multiline_native_delimiters(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The shared multiline member uses each language's native syntax."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj="first\n\n  indented\nlast"),
    )
    languages = (
        "python",
        "java",
        "cpp",
        "go",
        "javascript",
        "kotlin",
        "scala",
        "rust",
        "crystal",
        "d",
        "dart",
        "groovy",
        "lua",
        "nim",
        "swift",
        "typescript",
    )
    directives = "\n\n".join(
        f".. literalizer:: data.json\n"
        f"   :language: {language}\n"
        "   :string-format: multiline"
        for language in languages
    )
    (source_directory / "index.rst").write_text(
        data=f"Test\n====\n\n{directives}\n",
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    actual = [
        literal_block.astext()
        for literal_block in doctree.findall(condition=nodes.literal_block)
    ]
    assert actual == [
        '"""\\\nfirst\n\n  indented\nlast"""',
        '"""\nfirst\n\n  indented\nlast"""',
        'R"(first\n\n  indented\nlast)"',
        "`first\n\n  indented\nlast`",
        "`first\n\n  indented\nlast`",
        '"""first\n\n  indented\nlast"""',
        '"""first\n\n  indented\nlast"""',
        'r#"first\n\n  indented\nlast"#',
        "%q|first\n\n  indented\nlast|",
        "`first\n\n  indented\nlast`",
        "'''first\n\n  indented\nlast'''",
        "'''first\n\n  indented\nlast'''",
        "[[first\n\n  indented\nlast]]",
        '"""first\n\n  indented\nlast"""',
        '#"""\nfirst\n\n  indented\nlast\n"""#',
        "`first\n\n  indented\nlast`",
    ]
    app.cleanup()


def test_cpp_multiline_raw_string_delimiters(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """C++ uses neutral delimiters and accepts a custom fallback base."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj='first\n)"\nlast'),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :string-format: multiline

        .. literalizer:: data.json
           :language: cpp
           :string-format: multiline
           :multiline-raw-string-delimiter-base: TAG
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
    actual = [
        literal_block.astext()
        for literal_block in doctree.findall(condition=nodes.literal_block)
    ]
    assert actual == [
        'R"x(first\n)"\nlast)x"',
        'R"TAG(first\n)"\nlast)TAG"',
    ]
    assert "LITERALIZER" not in "".join(actual)
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("language", "delimiter_base", "expected_message"),
    argvalues=[
        (
            "python",
            "TAG",
            (
                "Language 'python' does not support "
                "':multiline-raw-string-delimiter-base:'."
            ),
        ),
        (
            "cpp",
            "(",
            (
                "Cpp multiline_raw_string_delimiter_base '(' is invalid: "
                "these characters are not permitted by C++'s raw-string "
                "delimiter grammar: ['(']"
            ),
        ),
    ],
)
def test_multiline_raw_string_delimiter_base_error(
    language: str,
    delimiter_base: str,
    expected_message: str,
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The C++-only delimiter option reports invalid uses cleanly."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj="first\nsecond"),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer:: data.json
           :language: {language}
           :string-format: multiline
           :multiline-raw-string-delimiter-base: {delimiter_base}
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=expected_message,
    )


def test_string_format_multiline_preserves_edge_newlines(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Multiline JSON scalars preserve edge newlines and indentation."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj="\nfirst\n\n  indented\nlast\n"),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :string-format: multiline
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        '"""\\\n\nfirst\n\n  indented\nlast\n"""'
    )
    app.cleanup()


def test_string_format_multiline_literalizer_call_yaml(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Multiline applies to YAML scalars in literalizer-call."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data="- |+\n  first\n\n    indented\n  last\n",
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.yaml
           :language: python
           :target-function: emit
           :parameter-names: message
           :per-element:
           :string-format: multiline
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        'emit(message="""\\\nfirst\n\n  indented\nlast\n""")'
    )
    app.cleanup()


def test_string_format_multiline_java_promotes_jdk_11(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Java multiline output uses the Java 16 text-block syntax."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj="first\nsecond"),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :language-version: jdk_11
           :string-format: multiline
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == '"""\nfirst\nsecond"""'
    app.cleanup()


def test_unsupported_string_format_multiline_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported multiline string format is an error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj="first\nsecond"),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: c
           :string-format: multiline
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'c' does not support string-format 'multiline'.",
    )


def test_trailing_comma_no(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :trailing-comma: option controls trailing commas."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1]),
    )
    source_file = source_directory / "index.rst"

    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: javascript
           :include-delimiters:
           :trailing-comma: yes
    """
        )
    )
    yes_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    yes_app.build()
    assert yes_app.statuscode == 0
    yes_html = (yes_app.outdir / "index.html").read_text()
    yes_app.cleanup()

    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: javascript
           :include-delimiters:
           :trailing-comma: no
    """
        )
    )
    no_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    no_app.build()
    assert no_app.statuscode == 0
    no_html = (no_app.outdir / "index.html").read_text()
    no_app.cleanup()

    assert yes_html != no_html


def test_go_line_ending_defaults_to_none(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Go uses its idiomatic no-semicolon default line ending."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    (source_directory / "index.rst").write_text(
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        'x := map[string]string{\n\t"key": "value",\n}'
    )
    app.cleanup()


def test_collection_layout_literalizer_multiline(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :collection-layout: option controls nested literal layout."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1, 2], [3, 4]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :include-delimiters:
           :collection-layout: multiline
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "(\n"
        "    (\n"
        "        1,\n"
        "        2,\n"
        "    ),\n"
        "    (\n"
        "        3,\n"
        "        4,\n"
        "    ),\n"
        ")"
    )
    app.cleanup()


def test_collection_layout_literalizer_call_multiline(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :collection-layout: option applies inside call arguments."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[[[1, 2], [3, 4]]]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: handle
           :parameter-names: items
           :per-element:
           :collection-layout: multiline
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "handle(items=(\n"
        "    (\n"
        "        1,\n"
        "        2,\n"
        "    ),\n"
        "    (\n"
        "        3,\n"
        "        4,\n"
        "    ),\n"
        "))"
    )
    app.cleanup()


def test_empty_dict_key_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :empty-dict-key: option is rejected for unsupported
    languages.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :empty-dict-key: positional
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support 'empty-dict-key'.",
    )


def test_empty_dict_key_positional(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :empty-dict-key: positional option works for R."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: r
           :empty-dict-key: positional
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


def test_heterogeneous_strategy_unsupported_value(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :heterogeneous-strategy: option rejects values a language
    does not support.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :heterogeneous-strategy: tagged_enum
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Language 'python' does not support heterogeneous-strategy "
            "'tagged_enum'."
        ),
    )


def test_heterogeneous_strategy_tagged_enum(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Rust's :heterogeneous-strategy: tagged_enum renders mixed scalars
    via a generated tagged enum.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: tagged_enum
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    expected = dedent(
        text="""\
        enum Value {
            I32(i32),
            Str(&'static str),
        }

        vec![
            Value::I32(1),
            Value::Str("hello"),
        ]"""
    )
    assert literal_block.astext() == expected
    app.cleanup()


def test_heterogeneous_strategy_object_variant_nim(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Nim's :heterogeneous-strategy: object_variant renders mixed
    scalars via a generated object variant type.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: nim
           :heterogeneous-strategy: object_variant
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "case kind: ValueKind" in text
    assert "Value(kind: vkInt, intVal: 1)" in text
    assert 'Value(kind: vkStr, strVal: "hello")' in text
    app.cleanup()


def test_heterogeneous_strategy_union_type_dhall(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Dhall's :heterogeneous-strategy: union_type renders mixed scalars
    via a generated Dhall union type.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: dhall
           :heterogeneous-strategy: union_type
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "let Value = < Int : Integer | Str : Text > in" in text
    assert "Value.Int +1" in text
    assert 'Value.Str "hello"' in text
    app.cleanup()


def test_unsupported_default_set_element_type_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :default-set-element-type: option is rejected for unsupported
    languages.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: javascript
           :default-set-element-type: Int
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'javascript' does not support 'default-set-element-type'.",
    )


def test_unsupported_empty_dict_key_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A language that defines the ``EmptyDictKey`` enum but does not
    accept the ``empty_dict_key`` constructor keyword is reported as a
    clean directive error rather than an uncaught ``TypeError``.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj={}))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :empty-dict-key: allow
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'cpp' does not support 'empty-dict-key'.",
    )


def test_unsupported_call_style_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A language that defines the ``CallStyles`` enum but does not accept
    the ``call_style`` constructor keyword is reported as a clean
    directive error rather than an uncaught ``TypeError``.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[[1]]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: forth
           :target-function: f
           :parameter-names: x
           :call-style: postfix
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'forth' does not support 'call-style'.",
    )


def test_default_set_element_type(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :default-set-element-type: option works for Go."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :default-set-element-type: int
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


def test_default_sequence_element_type(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :default-sequence-element-type: option works for Go."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :default-sequence-element-type: int
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


def test_default_dict_key_type(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :default-dict-key-type: option works for Go."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :default-dict-key-type: any
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


def test_dict_entry_style_symbol(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :dict-entry-style: option changes how dict entries are rendered."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: ruby
           :dict-entry-style: symbol
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


def test_float_format_scientific(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :float-format: option changes how floats are rendered."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1234.5]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :float-format: scientific
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


def test_float_format_fixed(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :float-format: fixed option renders floats in fixed
    notation.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1234.5]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :float-format: fixed
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


def test_numeric_literal_suffix_auto(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :numeric-literal-suffix: option adds type suffixes to
    numbers.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[42]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :numeric-literal-suffix: auto
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


def test_unsupported_dict_entry_style_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported dict-entry-style is reported as a directive
    error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :dict-entry-style: symbol
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support dict-entry-style 'symbol'.",
    )


def test_unsupported_numeric_literal_suffix_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported numeric-literal-suffix is a directive error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[42]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :numeric-literal-suffix: auto
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support numeric-literal-suffix 'auto'.",
    )


def test_default_ordered_map_value_type(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :default-ordered-map-value-type: option works for Go."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :default-ordered-map-value-type: any
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


def test_unsupported_default_ordered_map_value_type_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :default-ordered-map-value-type: option is rejected for
    unsupported languages.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :default-ordered-map-value-type: Any
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support 'default-ordered-map-value-type'.",
    )


def test_default_dict_value_type(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :default-dict-value-type: option works for Go."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :default-dict-value-type: any
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


def test_toml_input_format(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A .toml file is auto-detected and parsed as TOML."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.toml").write_text(data='key = "value"\n')
    (source_directory / "index.rst").write_text(
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
    (source_directory / "data.json5").write_text(data='{key: "value"}')
    (source_directory / "index.rst").write_text(
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
    (source_directory / "data.txt").write_text(data="- 1\n- 2\n")
    (source_directory / "index.rst").write_text(
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
    (source_directory / "data.dat").write_text(data="[1]")
    (source_directory / "index.rst").write_text(
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
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Cannot determine input format for 'data.dat'. "
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
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2]),
    )
    (source_directory / "index.rst").write_text(
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
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    (source_directory / "index.rst").write_text(
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
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    source_file = source_directory / "index.rst"
    source_file.write_text(
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

    source_file.write_text(
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
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    (source_directory / "index.rst").write_text(
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


def test_literalizer_call_basic_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders function calls matching
    an equivalent code-block.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           my_func(flag=True, count=42, name="hello")
           my_func(flag=False, count=99, name="world")
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_literalizer_call_heterogeneous_per_element_preamble(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Heterogeneous per-element calls include one complete Rust preamble.

    The preamble must include the variants used by every call argument,
    including the empty nested list in the second call.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[[1, "two"]], [[False, []]]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: rust
           :target-function: process
           :parameter-names: value
           :per-element:
           :heterogeneous-strategy: tagged_enum
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "enum Value {\n"
        "    I32(i32),\n"
        "    Str(&'static str),\n"
        "    Bool(bool),\n"
        "    List(Vec<Value>),\n"
        "}\n"
        "\n"
        'process(vec![Value::I32(1), Value::Str("two")]);\n'
        "process(vec![Value::Bool(false), Value::List(vec![])]);"
    )
    app.cleanup()


def test_literalizer_call_go(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders positional-style calls
    for Go.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: go
           :target-function: myFunc
           :parameter-names: flag,count
           :per-element:
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
    assert "myFunc(true, 42)" in text
    assert "myFunc(false, 99)" in text
    app.cleanup()


def test_literalizer_call_without_per_element(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :per-element:, the whole value is passed as a single
    argument.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2, 3]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: x
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
    assert "my_func" in text
    app.cleanup()


def test_literalizer_call_include_preamble(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :include-preamble: option works with literalizer-call."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42]]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: go
           :target-function: myFunc
           :parameter-names: flag,count
           :per-element:
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

    doctree = app.env.get_doctree(docname="index")
    literal_blocks = list(
        doctree.findall(condition=nodes.literal_block),
    )
    (literal_block,) = literal_blocks
    text = literal_block.astext()
    assert "package main" in text
    assert "myFunc(true, 42)" in text
    app.cleanup()


def test_literalizer_call_omit_code(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :omit-code: option omits generated calls."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(
        data="- 2024-01-15T10:30:00Z\n",
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.yaml
           :language: java
           :target-function: billingSystem.recordDelivery
           :parameter-names: delivered_at
           :per-element:
           :datetime-format: instant
           :include-preamble:
           :omit-code:
    """
        ),
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
    assert literal_block.astext() == "import java.time.Instant;"
    app.cleanup()


def test_literalizer_call_source_is_absolute(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literal_block node's source attribute is an absolute path."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: f
           :parameter-names: x
           :per-element:
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
    source = literal_block["source"]
    assert Path(source).is_absolute()
    app.cleanup()


def test_literalizer_call_call_transform(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive supports :call-transform: to wrap
    each call expression.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :call-transform: print($0)
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           print(my_func(flag=True, count=42, name="hello"))
           print(my_func(flag=False, count=99, name="world"))
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_literalizer_call_call_transform_index(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :call-transform: template exposes the zero-based call
    position as ``$index``.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :call-transform: result_$index = $call
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           result_0 = my_func(flag=True, count=42, name="hello")
           result_1 = my_func(flag=False, count=99, name="world")
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_literalizer_call_call_transform_no_reexpansion(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A ``$zipped`` literal that itself contains a placeholder token is
    inserted verbatim rather than being re-expanded.

    The zip element renders to the Python literal ``"$call"``; a naive
    sequential substitution would rewrite that ``$call`` into the whole
    call expression.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[[1]]))
    (source_directory / "zip.json").write_text(
        data=json.dumps(obj=["$call"]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: x
           :per-element:
           :zip-file: zip.json
           :call-transform: $call  # $zipped
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           my_func(x=1)  # "$call"
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_literalizer_call_zip_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:zip-file: pairs a parallel data file with the generated calls,
    surfacing each element as ``$zipped`` rendered as a native literal.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    (source_directory / "expected.json").write_text(
        data=json.dumps(obj=["first", "second"]),
    )
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :zip-file: expected.json
           :call-transform: assert $call == $zipped
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           assert my_func(flag=True, count=42, name="hello") == "first"
           assert my_func(flag=False, count=99, name="world") == "second"
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_literalizer_call_comment_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:comment-file: emits one trailing comment per generated call,
    using the target language's comment syntax, with a blank line
    emitting no comment for that call.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    (source_directory / "comments.txt").write_text(data="first case\n\n")
    source_file = source_directory / "index.rst"
    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :comment-file: comments.txt
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
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           my_func(flag=True, count=42, name="hello")  # first case
           my_func(flag=False, count=99, name="world")
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_literalizer_call_comment_file_length_mismatch(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A :comment-file: whose line count does not match the number of
    generated calls is surfaced as a clean directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    (source_directory / "comments.txt").write_text(data="only one\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :comment-file: comments.txt
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "comment_source has 1 entry(ies) but 2 call(s) were "
            "generated; the lengths must match"
        ),
    )


def test_literalizer_call_racket(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Racket S-expression calls
    with prefixed keyword arguments.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: racket
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "(process #:flag #t #:count 42)" in text
    assert "(process #:flag #f #:count 99)" in text
    app.cleanup()


def test_literalizer_call_common_lisp(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Common Lisp calls with
    ``:keyword`` arguments.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: common-lisp
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "(process :flag t :count 42)" in text
    assert "(process :flag nil :count 99)" in text
    app.cleanup()


def test_literalizer_call_clojure(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Clojure calls as
    S-expressions with ``:keyword`` arguments.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: clojure
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "(process :flag true :count 42)" in text
    assert "(process :flag false :count 99)" in text
    app.cleanup()


def test_literalizer_call_objective_c(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Objective-C calls as
    positional C-style calls with boxed scalars.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: objective-c
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert text == "process(@YES, @42);\nprocess(@NO, @99);"
    app.cleanup()


def test_literalizer_call_perl(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Perl calls as positional
    subroutine invocations.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: perl
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert text == (
        "process(JSON::PP::true, 42);\nprocess(JSON::PP::false, 99);"
    )
    app.cleanup()


def test_literalizer_call_ref_case_camel(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:ref-case: camel`` converts ``{"$ref": "name"}`` identifiers
    to camelCase in the rendered call.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[
                [{"$ref": "user_obj"}, 42],
                [{"$ref": "admin_user"}, 99],
            ],
        ),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: typescript
           :target-function: process
           :parameter-names: user,count
           :per-element:
           :ref-case: camel
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    expected = (
        "process({ user: userObj, count: 42 });\n"
        "process({ user: adminUser, count: 99 });"
    )
    assert text == expected
    app.cleanup()


def test_literalizer_call_ref_marker(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``{"$ref": "name"}`` markers at argument positions emit the name
    as a bare identifier rather than formatting it as a literal.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[
                [{"$ref": "user_obj"}, 42],
                [{"$ref": "admin"}, 99],
            ],
        ),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: process
           :parameter-names: user,count
           :per-element:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "process(user=user_obj, count=42)" in text
    assert "process(user=admin, count=99)" in text
    app.cleanup()


def test_call_style_positional_typescript(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :call-style: positional option overrides TypeScript's default
    OBJECT style so the call drops the parameter-name object wrapper.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"flag": True, "count": 42}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: typescript
           :target-function: myFunc
           :parameter-names: obj
           :call-style: positional
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert 'myFunc({"flag": true, "count": 42});' in text
    assert "obj:" not in text
    app.cleanup()


def test_call_style_unsupported_value(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :call-style: option rejects values a language does not
    support.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"flag": True}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: f
           :parameter-names: obj
           :call-style: object
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support call-style 'object'.",
    )


def test_literalizer_call_without_per_element_uses_call_style(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :per-element:, the call uses the language's call style
    (e.g. Swift's keyword labels) rather than a positional argument.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2, 3]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: swift
           :target-function: process
           :parameter-names: data
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "process(data: [1, 2, 3])" in text
    app.cleanup()


def test_parameter_count_mismatch_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A row whose value count differs from :parameter-names: is a
    directive error instead of a raw traceback.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1, 2, 3]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: f
           :parameter-names: a,b
           :per-element:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "':parameter-names:' has 2 entries but the data provides a different "
            "number of values: Expected 2 parameters but got 3 values"
        ),
    )


def test_module_name_java(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :module-name: option overrides the wrapper module name."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :wrap-in-file:
           :variable-name: x
           :module-name: Foo
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "class Foo" in text
    app.cleanup()


def test_module_name_unsupported_language_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Using :module-name: with a language that lacks a named scope is a
    directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :module-name: Foo
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support ':module-name:'.",
    )


def test_both_variable_forms_csharp(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :both-variable-forms: flag emits declaration and assignment."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj={"x": 1}))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: csharp
           :variable-name: my_var
           :both-variable-forms:
           :wrap-in-file:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "var my_var" in text
    assert "my_var =" in text
    app.cleanup()


def test_both_variable_forms_requires_variable_name(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Using :both-variable-forms: without :variable-name: is an error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj={"x": 1}))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :both-variable-forms:
           :wrap-in-file:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="':both-variable-forms:' requires ':variable-name:'.",
    )


def test_existing_variable_requires_variable_name(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Using :existing-variable: without :variable-name: is an error
    rather than silently emitting a plain literal.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj={"x": 1}))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :existing-variable:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="':existing-variable:' requires ':variable-name:'.",
    )


def test_both_variable_forms_incompatible_with_existing_variable(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Combining :both-variable-forms: with :existing-variable: is an
    error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj={"x": 1}))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :variable-name: my_var
           :existing-variable:
           :both-variable-forms:
           :wrap-in-file:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "':both-variable-forms:' cannot be combined with ':existing-"
            "variable:'."
        ),
    )


def test_literalizer_call_consumable_refs(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:consumable-refs: causes refs used exactly once to be consumed
    (e.g. wrapped in ``std::move`` for C++).
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[{"$ref": "my_vec"}, 42]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: cpp
           :target-function: process
           :parameter-names: data,count
           :per-element:
           :consumable-refs: my_vec
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "std::move(my_vec)" in text
    app.cleanup()


def test_literalizer_call_variable_name_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:variable-name:`` wraps the ``literalizer-call`` output in a
    per-language variable binding.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"count": 42}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: rust
           :target-function: make_widget
           :parameter-names: count
           :variable-name: my_data
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    expected = 'let my_data = make_widget(HashMap::from([("count", 42)]));'
    assert text == expected
    app.cleanup()


def test_literalizer_call_existing_variable_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:existing-variable:`` produces an assignment without a
    declaration keyword.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"count": 42}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: rust
           :target-function: make_widget
           :parameter-names: count
           :variable-name: my_data
           :existing-variable:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    expected = 'my_data = make_widget(HashMap::from([("count", 42)]));'
    assert text == expected
    app.cleanup()


def test_literalizer_call_variable_form_per_element_single_element(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:variable-name:`` with ``:per-element:`` over a single-element
    source binds the one resulting call to the variable.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"count": 42}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: rust
           :target-function: make_widget
           :parameter-names: count
           :per-element:
           :variable-name: my_data
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    expected = 'let my_data = make_widget(HashMap::from([("count", 42)]));'
    assert text == expected
    app.cleanup()


def test_literalizer_call_variable_form_per_element_multi_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:variable-name:`` with ``:per-element:`` over a source that
    produces more than one call surfaces literalizer's
    ``UnsupportedCallShapeError`` as a directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"count": 1}, {"count": 2}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: rust
           :target-function: make_widget
           :parameter-names: count
           :per-element:
           :variable-name: my_data
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Rust cannot represent this call shape: "
            "variable_form binds a single call result, but this "
            "input produces 2 calls; supply exactly one call "
            "(per_element=False, or per_element=True with a "
            "single-element source)"
        ),
    )
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("language", "expected"),
    argvalues=[
        ("python", "p1 = Playlist()"),
        ("rust", "let p1 = Playlist();"),
        ("cpp", "auto p1 = Playlist();"),
        ("go", "p1 := Playlist()"),
        ("ruby", "p1 = Playlist()"),
    ],
)
def test_literalizer_call_zero_arg_constructor_variable_name(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    language: str,
    expected: str,
) -> None:
    """An empty ``:parameter-names:`` with ``:per-element:`` over a
    single-element source binds a no-argument constructor to the
    variable.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(data="- []\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer-call:: data.yaml
           :language: {language}
           :target-function: Playlist
           :parameter-names:
           :per-element:
           :variable-name: p1
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert text == expected
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("language", "expected"),
    argvalues=[
        ("python", "p1 = Playlist()"),
        ("rust", "let p1 = Playlist::new();"),
        ("cpp", "auto p1 = Playlist();"),
        ("go", "p1 := NewPlaylist()"),
        ("ruby", "p1 = Playlist.new()"),
    ],
)
def test_literalizer_call_constructor_class_variable_name(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    language: str,
    expected: str,
) -> None:
    """``:constructor-class:`` derives the call target from the
    selected language.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(data="- []\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer-call:: data.yaml
           :language: {language}
           :constructor-class: Playlist
           :per-element:
           :variable-name: p1
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert text == expected
    app.cleanup()


def test_literalizer_call_requires_target_or_constructor(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``literalizer-call`` requires an explicit target source."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[[]]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :per-element:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Use exactly one of ':target-function:' and ':constructor-class:'.",
    )
    app.cleanup()


def test_literalizer_call_target_function_and_constructor_class_rejected(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:constructor-class:`` cannot be combined with an explicit
    target function.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[[]]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: Playlist
           :constructor-class: Playlist
           :per-element:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="':target-function:' cannot be combined with ':constructor-class:'.",
    )
    app.cleanup()


def test_literalizer_call_rust_mut_variable_name(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:modifiers: mut`` with ``:variable-name:`` renders a mutable
    Rust binding, so the constructed value can be mutated through the
    binding (the construct-then-mutate ladder of issue #228).
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(data="- []\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.yaml
           :language: rust
           :target-function: Playlist
           :parameter-names:
           :per-element:
           :variable-name: p1
           :modifiers: mut
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert text == "let mut p1 = Playlist();"
    app.cleanup()


def test_literalizer_call_parameter_names_omitted(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Omitting ``:parameter-names:`` entirely is equivalent to an empty
    value: the call takes no arguments.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[[]]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: Playlist
           :per-element:
           :variable-name: p1
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert text == "p1 = Playlist()"
    app.cleanup()


def test_unrepresentable_input_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A YAML non-string dict key for a language that cannot represent it
    surfaces literalizer's ``UnrepresentableInputError`` as a
    directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(data="1: a\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: go
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Go cannot represent dict key of type int",
    )
    app.cleanup()


def test_literalizer_error_base_covers_new_exceptions(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Any ``LiteralizerError`` subclass surfaces as a directive error.

    The directives catch literalizer's common ``LiteralizerError`` base
    rather than an allowlist of concrete classes, so an exception the
    extension does not name -- here ``UnrepresentableSpecialFloatError``,
    raised for a NaN in an Odin JSON value -- is still reported against
    the offending directive instead of aborting the build with a
    traceback.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(data="value: .nan\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: odin
           :json-type: json_value
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Odin json_type renders the literalized value as a JSON "
            "text; JSON has no representation for non-finite floats "
            "(NaN / +Infinity / -Infinity) and json.parse_string "
            "rejects them at runtime."
        ),
    )
    app.cleanup()


def test_tcl_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the tcl language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: tcl
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "[list" in text
    app.cleanup()


def test_nix_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the nix language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: nix
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert text.startswith("[")
    assert "1\n  2" in text
    app.cleanup()


def test_sml_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the sml language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: sml
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "SInt" in text
    app.cleanup()


def test_v_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the V language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: v
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "1," in text
    app.cleanup()


def test_wren_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the wren language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: wren
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "1," in text
    app.cleanup()


def test_forth_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the forth language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: forth
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "1" in text
    assert "2" in text
    app.cleanup()


def test_module_name_auto_cased(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :module-name: value is auto-converted to the language's expected
    case using the language's module_name_case.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :wrap-in-file:
           :variable-name: x
           :module-name: my_module
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "class MyModule" in text
    app.cleanup()


def test_roc_language_key(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Roc is selected by language name even though Pygments falls back
    to text.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: roc
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    assert "RList" in text
    assert literal_block["language"] == "text"
    app.cleanup()


def test_ref_key_literalizer(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :ref-key: option customizes ref markers for literalizer."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"$reference": "user_obj"}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :ref-case: snake
           :ref-key: $reference
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == "user_obj"
    app.cleanup()


def test_ref_key_literalizer_call(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :ref-key: option customizes ref markers for
    literalizer-call.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[{"$reference": "user_obj"}, 42]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: process
           :parameter-names: user,count
           :per-element:
           :ref-case: snake
           :ref-key: $reference
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == "process(user=user_obj, count=42)"
    app.cleanup()


def test_language_version(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :language-version: option selects a literalizer version
    enum.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :language-version: py39
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == "1,\n2,"
    app.cleanup()


def test_language_defaults_apply_to_both_directives(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Configured language defaults apply unless a directive overrides
    them.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"name": "Ada", "active": True}]),
    )
    (source_directory / "calls.json").write_text(
        data=json.dumps(obj=[{"name": "Ada", "active": True}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :heterogeneous-strategy: record
           :record-shape-names: name,active=Task
           :include-delimiters:
           :include-preamble:

        .. literalizer-call:: calls.json
           :language: cpp
           :target-function: process
           :parameter-names: task
           :per-element:
           :heterogeneous-strategy: record
           :record-shape-names: name,active=Task
           :include-preamble:

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp20
           :heterogeneous-strategy: record
           :record-shape-names: name,active=Task
           :include-preamble:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={
            "extensions": ["sphinx_literalizer"],
            "literalizer_language_defaults": {
                "cpp": {"language-version": "cpp14"},
            },
        },
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    literal_blocks = list(doctree.findall(condition=nodes.literal_block))
    default_literal, default_call, explicit_override = literal_blocks
    assert 'Task{"Ada", true}' in default_literal.astext()
    assert 'process(Task{"Ada", true});' in default_call.astext()
    assert '.name = "Ada"' in explicit_override.astext()
    app.cleanup()


def test_record_null_substitutions_cpp14(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Record field null substitutions keep a C++14 task typed."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "task.json").write_text(
        data=json.dumps(
            obj=[
                {
                    "task_id": None,
                    "assignee": None,
                    "status": "todo",
                },
            ]
        ),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: task.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :record-shape-names: task_id,assignee,status=Task
           :record-null-substitutions: {"task_id": -1, "assignee": ""}
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert 'Task{-1, "", "todo"}' in literal_block.astext()
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("substitutions", "expected_message"),
    argvalues=[
        (
            "{not JSON}",
            (
                "':record-null-substitutions:' must be a valid JSON "
                "object: Expecting property name enclosed in double "
                "quotes."
            ),
        ),
        ("[]", "':record-null-substitutions:' must be a JSON object."),
    ],
)
def test_record_null_substitutions_invalid_value_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    substitutions: str,
    expected_message: str,
) -> None:
    """Invalid record null substitutions are reported on the
    directive.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :record-null-substitutions: {substitutions}
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=expected_message,
    )


@pytest.mark.parametrize(
    argnames=("defaults", "error_message"),
    argvalues=[
        ("cpp14", r"entries must be dictionaries"),
        (
            {"include-preamble": "true"},
            r"only supports shared format options",
        ),
        (
            {"language-version": 14},
            r"option values must be strings",
        ),
    ],
)
def test_language_defaults_invalid_value_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    defaults: object,
    error_message: str,
) -> None:
    """Invalid language defaults raise a clear ExtensionError."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={
            "extensions": ["sphinx_literalizer"],
            "literalizer_language_defaults": {"cpp": defaults},
        },
    )
    with pytest.raises(expected_exception=ExtensionError, match=error_message):
        app.build()


def test_cpp17_language_version(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:language-version: cpp17`` avoids C++20 field-name syntax."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"name": "Ada", "active": True}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp17
           :heterogeneous-strategy: record
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert 'Record0{"Ada", true}' in literal_block.astext()
    app.cleanup()


def test_unsupported_language_version_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported language-version is reported as a directive
    error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :language-version: ada_2022
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support language-version 'ada_2022'.",
    )


def test_wrap_in_file_without_variable_raises_directive_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Languages that cannot wrap a bare value at file scope surface a
    clean directive error (rather than a literalizer traceback) when
    ``:wrap-in-file:`` is set without ``:variable-name:``.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :wrap-in-file:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Java cannot wrap a bare value (without a variable_form) at file "
            "scope"
        ),
    )


def test_heterogeneous_strategy_record_go(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Go's :heterogeneous-strategy: record renders a record-shaped
    mapping as a generated struct with the default name prefix.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"flag": True, "count": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :heterogeneous-strategy: record
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "package main\n"
        "type Record0 struct {\n"
        "\tFlag bool\n"
        "\tCount int\n"
        "}\n"
        "\n"
        "Record0{\n"
        "\tFlag: true,\n"
        "\tCount: 1,\n"
        "}"
    )
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("language", "record_declaration", "nested_map_literal"),
    argvalues=[
        (
            "csharp",
            (
                "record Record0(string Name, Dictionary<string, object> "
                "Input, Dictionary<string, object> Expected);"
            ),
            "new Dictionary<string, object>",
        ),
        (
            "cpp",
            (
                "struct Record0 { std::string name; "
                "std::map<std::string, LiteralizerRecordValue> input; "
                "std::map<std::string, LiteralizerRecordValue> expected; "
                "};"
            ),
            "std::map<std::string, LiteralizerRecordValue>",
        ),
        ("go", "type Record0 struct {", "map[string]any"),
        (
            "java",
            (
                "record Record0(String name, java.util.Map<String, Object> "
                "input, java.util.Map<String, Object> expected) {}"
            ),
            "Map.ofEntries",
        ),
        (
            "kotlin",
            (
                "data class Record0(val name: String, "
                "val input: Map<String, Any?>, "
                "val expected: Map<String, Any?>)"
            ),
            "mapOf<String, Any?>",
        ),
        (
            "rust",
            (
                "struct Record0 {\n"
                "    name: &'static str,\n"
                "    input: HashMap<&'static str, Value>,\n"
                "    expected: HashMap<&'static str, Value>,\n"
                "}"
            ),
            "HashMap::from",
        ),
        (
            "scala",
            (
                "case class Record0(name: String, input: Map[String, Any], "
                "expected: Map[String, Any])"
            ),
            "Map[String, Any]",
        ),
    ],
)
def test_record_nested_map_fallback(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    language: str,
    record_declaration: str,
    nested_map_literal: str,
) -> None:
    """Record rendering keeps one outer shape and falls back to maps
    for incompatible nested sibling shapes in statically typed targets.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[
                {
                    "name": "test_1",
                    "input": {
                        "type": "create",
                        "pr_id": "pr_1",
                        "draft": True,
                    },
                    "expected": {"pr_id": "pr_1", "status": "draft"},
                },
                {
                    "name": "test_2",
                    "input": {"type": "publish", "pr_id": "pr_1"},
                    "expected": {"error": "invalid_operation"},
                },
            ],
        ),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer:: data.json
           :language: {language}
           :heterogeneous-strategy: record
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    output = literal_block.astext()
    assert record_declaration in output
    assert output.count("Record0") == 3
    assert "Record1" not in output
    assert nested_map_literal in output
    assert all(
        value in output
        for value in ("test_1", "test_2", "draft", "invalid_operation")
    )
    app.cleanup()


def test_record_struct_name_prefix_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Python's :heterogeneous-strategy: record honours
    :record-struct-name-prefix: for the generated dataclass name.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}, {"x": 3, "y": 4}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :heterogeneous-strategy: record
           :record-struct-name-prefix: Row
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "from __future__ import annotations\n"
        "import dataclasses\n"
        "@dataclasses.dataclass(frozen=True)\n"
        "class Row0:\n"
        "    x: int\n"
        "    y: int\n"
        "\n"
        "(\n"
        "    Row0(x=1, y=2),\n"
        "    Row0(x=3, y=4),\n"
        ")"
    )
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("strategy", "data", "expected"),
    argvalues=[
        (
            "tuple",
            [1, "Ada", True],
            'std::make_tuple(\n    1,\n    "Ada",\n    true\n)',
        ),
        (
            "record",
            [{"name": "Ada", "score": 42}],
            "struct Candidate0 { std::string name; int score{}; };",
        ),
    ],
)
def test_cpp14_candidate_facing_heterogeneous_strategies(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    strategy: str,
    data: list[object] | dict[str, int | str],
    expected: str,
) -> None:
    """C++14 exposes tuple and named-record alternatives to wrappers."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=data))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: {strategy}
           :record-struct-name-prefix: Candidate
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    output = literal_block.astext()
    assert expected in output
    if strategy == "tuple":
        assert "LiteralizerVariant" not in output
    app.cleanup()


def test_cpp14_named_carrier_preamble_only(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Literalizer forwards a carrier name and can omit literal code."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[{"name": "build", "args": [1, "fast", None]}],
        ),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :heterogeneous-value-name: TaskValue
           :record-struct-name-prefix: Task
           :include-delimiters:
           :preamble-only:

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :heterogeneous-value-name: TaskValue
           :record-struct-name-prefix: Task
           :include-delimiters:
           :variable-name: task
           :pre-indent-level: 1
    """
        ),
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    preamble_block, literal_block = doctree.findall(
        condition=nodes.literal_block,
    )
    preamble = preamble_block.astext()
    literal = literal_block.astext()
    assert "struct TaskValue {" in preamble
    assert "struct Task0 {" in preamble
    assert "auto task =" not in preamble
    assert "struct TaskValue {" not in literal
    assert "auto task = std::vector<Task0>{" in literal

    app.cleanup()


def _find_cpp_compiler() -> str:
    """Return an available C++ compiler."""
    compiler = shutil.which(cmd="clang++") or shutil.which(cmd="g++")
    if compiler is None:
        msg = "A C++ compiler is required for this test."
        raise RuntimeError(msg)
    return compiler


def test_cpp_compiler_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing C++ compiler fails instead of skipping the composition
    test.
    """
    monkeypatch.setattr(
        target=shutil, name="which", value=Mock(return_value=None)
    )
    with pytest.raises(
        expected_exception=RuntimeError,
        match="A C\\+\\+ compiler is required",
    ):
        _find_cpp_compiler()


def test_literalizer_call_named_carrier_preamble_only(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Literalizer-call composes a named carrier with later C++14 code."""
    compiler = _find_cpp_compiler()

    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[["build", [1, "fast", None]]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :heterogeneous-value-name: TaskValue
           :target-function: run
           :parameter-names: name,args
           :per-element:
           :preamble-only:

        .. literalizer-call:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :heterogeneous-value-name: TaskValue
           :target-function: run
           :parameter-names: name,args
           :per-element:
    """
        ),
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    preamble_block, call_block = doctree.findall(
        condition=nodes.literal_block,
    )
    assert "struct TaskValue {" in preamble_block.astext()
    assert (
        "std::make_shared<TypedHolder<std::string>>" in preamble_block.astext()
    )
    assert "run(" not in preamble_block.astext()
    assert "struct TaskValue {" not in call_block.astext()
    assert call_block.astext() == (
        'run("build", std::vector<TaskValue>{'
        'TaskValue{1}, TaskValue{"fast"}, TaskValue{nullptr}});'
    )
    combined = (
        "#include <cassert>\n\n"
        f"{preamble_block.astext()}\n\n"
        "void run(const std::string&, "
        "const std::vector<TaskValue>& values) {\n"
        "    assert(values.at(1).is<std::string>());\n"
        '    assert(values.at(1).get<std::string>() == "fast");\n'
        "    assert(!values.at(1).is<const char*>());\n"
        "}\n\n"
        "int main() {\n"
        f"    {call_block.astext()}\n"
        "    return 0;\n"
        "}\n"
    )
    assert combined.count("struct TaskValue {") == 1
    combined_path = tmp_path / "combined.cpp"
    combined_path.write_text(data=combined)
    executable_path = tmp_path / "combined"
    subprocess.run(
        args=[
            compiler,
            "-std=c++14",
            str(object=combined_path),
            "-o",
            str(object=executable_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        args=[str(object=executable_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    app.cleanup()


def test_heterogeneous_value_name_unsupported_language_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A carrier name on an unsupported language raises a clear error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data="[1, 2]")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :heterogeneous-value-name: Value
    """
        ),
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support ':heterogeneous-value-name:'.",
    )


@pytest.mark.parametrize(
    argnames=("language", "strategy", "data", "expected"),
    argvalues=[
        ("rust", "tagged_enum", [1, "x", None], "enum TaskValue {"),
        ("mojo", "variant", [1, "x"], "comptime TaskValue = Variant["),
        ("nim", "object_variant", [1, "x", None], "TaskValueKind = enum"),
        ("dhall", "union_type", [1, "x", None], "let TaskValue = <"),
    ],
)
def test_heterogeneous_value_name_supported_languages(  # noqa: PLR0913
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    language: str,
    strategy: str,
    data: list[object],
    expected: str,
) -> None:
    """The general name option reaches each language-specific setting."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=data))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer:: data.json
           :language: {language}
           :heterogeneous-strategy: {strategy}
           :heterogeneous-value-name: TaskValue
           :include-delimiters:
           :include-preamble:
    """
        ),
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert expected in literal_block.astext()
    app.cleanup()


def test_cpp14_nested_tuple_strategy_uses_standard_tuple_types(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Nested C++14 tuples do not fall back to variant wrappers."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1, "Mainframe1"]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: tuple
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    output = literal_block.astext()
    assert "std::vector<std::tuple<int, std::string>>" in output
    assert "std::make_tuple(" in output
    assert "LiteralizerVariant" not in output
    app.cleanup()


def test_record_struct_name_prefix_unsupported_language_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:record-struct-name-prefix: with a language that has no record
    strategy is a directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: typescript
           :record-struct-name-prefix: Row
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Language 'typescript' does not support ':record-struct-name-"
            "prefix:'."
        ),
    )


def test_record_shape_names_java(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Java's :record-shape-names: maps a key set to a custom record
    name instead of the auto-generated one.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}, {"x": 3, "y": 4}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=Point
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "import java.util.Map;\n"
        "record Point(int x, int y) {}\n"
        "\n"
        "new Object[]{\n"
        "    new Point(1, 2),\n"
        "    new Point(3, 4)\n"
        "}"
    )
    app.cleanup()


def test_record_shape_names_cpp14_external_record(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """C++14 maps a named record shape to a caller-declared struct."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[
                {"title": "Write docs", "done": False},
                {"title": "Review PR", "done": True},
            ],
        ),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :record-shape-names: title,done=Task
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    output = literal_block.astext()
    assert output == (
        "#include <initializer_list>\n"
        "#include <string>\n"
        "#include <map>\n"
        "#include <vector>\n"
        "\n"
        "std::vector<Task>{\n"
        '    Task{"Write docs", false},\n'
        '    Task{"Review PR", true},\n'
        "}"
    )
    assert "struct Task" not in output
    assert "LiteralizerVariant" not in output
    app.cleanup()


def test_record_shape_names_cpp14_error_external_map_alias(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """C++14 ERROR uses a named map shape as the vector element type."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "expenses.json").write_text(
        data=json.dumps(
            obj=[
                {
                    "expense_id": "001",
                    "trip_id": "001",
                    "amount_usd": "49.99",
                },
            ],
        ),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: expenses.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: error
           :record-shape-names: expense_id,trip_id,amount_usd=Expense
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "std::vector<Expense>{\n"
        "    std::map<std::string, std::string>{"
        '{"expense_id", "001"}, {"trip_id", "001"}, '
        '{"amount_usd", "49.99"}},\n'
        "}"
    )
    app.cleanup()


def test_record_shape_names_invalid_name_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A :record-shape-names: name that is not a PascalCase identifier
    is surfaced as a clean directive error, not a traceback.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=point
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "record_shape_names entry for keys ['x', 'y'] maps to "
            "'point', which is not a PascalCase Java identifier."
        ),
    )


def test_record_shape_names_malformed_entry_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A :record-shape-names: entry without '=' is a directive error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "':record-shape-names:' entry 'x,y' is missing the '=' between the "
            "comma-separated keys and the name."
        ),
    )


def test_record_shape_names_trailing_separator_ignored(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A trailing ';' (or empty entry) in :record-shape-names: is
    skipped rather than treated as a malformed entry.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}, {"x": 3, "y": 4}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=Point;
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "import java.util.Map;\n"
        "record Point(int x, int y) {}\n"
        "\n"
        "new Object[]{\n"
        "    new Point(1, 2),\n"
        "    new Point(3, 4)\n"
        "}"
    )
    app.cleanup()


def test_record_shape_names_empty_name_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A :record-shape-names: entry with keys but an empty name is a
    directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "':record-shape-names:' entry 'x,y=' must have at least one key and a"
            " non-empty name."
        ),
    )


def test_record_shape_names_duplicate_key_set_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Two :record-shape-names: entries for the same key set (in any
    key order) are a directive error instead of silently
    keeping only the last name.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=Point; y,x=Other
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="':record-shape-names:' has multiple entries for the key set {x, y}.",
    )


def test_record_shape_names_unsupported_language_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:record-shape-names: with a language that does not support it
    (e.g. Python) is a directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :heterogeneous-strategy: record
           :record-shape-names: x,y=Point
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support ':record-shape-names:'.",
    )


def test_fortran_language_version_v2003(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Fortran accepts :language-version: v2003 again, defining int64
    via selected_int_kind and real64 via selected_real_kind instead of
    importing them from iso_fortran_env.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1, 2]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: fortran
           :language-version: v2003
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == dedent(
        text="""\
        module fval_m
          implicit none
          integer, parameter :: int64 = selected_int_kind(18)
          integer, parameter :: real64 = selected_real_kind(15, 307)
          integer, parameter :: tag_null = 0
          integer, parameter :: tag_bool = 1
          integer, parameter :: tag_int = 2
          integer, parameter :: tag_real = 3
          integer, parameter :: tag_str = 4
          integer, parameter :: tag_list = 5
          integer, parameter :: tag_map = 6
          integer, parameter :: tag_set = 7
          integer, parameter :: tag_entry = 8
          type :: fval_t
            integer :: tag = tag_null
            logical :: bv = .false.
            integer(kind=int64) :: iv = 0_int64
            real(kind=real64) :: rv = 0.0_real64
            character(len=:), pointer :: sv => null()
            type(fval_t), pointer :: items(:) => null()
          end type fval_t
        contains
          function fnull() result(v)
            type(fval_t) :: v
            v%tag = tag_null
          end function fnull
          function fbool(b) result(v)
            logical, intent(in) :: b
            type(fval_t) :: v
            v%tag = tag_bool
            v%bv = b
          end function fbool
          function fint(n) result(v)
            integer(kind=int64), intent(in) :: n
            type(fval_t) :: v
            v%tag = tag_int
            v%iv = n
          end function fint
          function freal(x) result(v)
            real(kind=real64), intent(in) :: x
            type(fval_t) :: v
            v%tag = tag_real
            v%rv = x
          end function freal
          function fstr(s) result(v)
            character(len=*), intent(in) :: s
            type(fval_t) :: v
            v%tag = tag_str
            allocate(character(len=len(s)) :: v%sv)
            v%sv = s
          end function fstr
          function flist(a) result(v)
            type(fval_t), intent(in) :: a(:)
            type(fval_t) :: v
            v%tag = tag_list
            allocate(v%items(size(a)))
            v%items = a
          end function flist
          function fmap(a) result(v)
            type(fval_t), intent(in) :: a(:)
            type(fval_t) :: v
            v%tag = tag_map
            allocate(v%items(size(a)))
            v%items = a
          end function fmap
          function fset(a) result(v)
            type(fval_t), intent(in) :: a(:)
            type(fval_t) :: v
            v%tag = tag_set
            allocate(v%items(size(a)))
            v%items = a
          end function fset
          function fentry(k, u) result(v)
            character(len=*), intent(in) :: k
            type(fval_t), intent(in) :: u
            type(fval_t) :: v
            v%tag = tag_entry
            allocate(character(len=len(k)) :: v%sv)
            v%sv = k
            allocate(v%items(1))
            v%items(1) = u
          end function fentry
        end module fval_m

        flist([fval_t ::
            fint(1_int64),
            fint(2_int64)
        ])"""
    )
    app.cleanup()


def test_heterogeneous_strategy_tuple_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Rust's :heterogeneous-strategy: tuple renders a fixed-length
    heterogeneous scalar array as a native tuple instead of raising.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, True, "x"]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: tuple
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == '(\n    1,\n    true,\n    "x",\n)'
    app.cleanup()


def test_heterogeneous_strategy_auto_keeps_homogeneous_output_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The auto mode leaves homogeneous data in its natural
    representation instead of converting it to a generated record.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"a": 1}, {"a": 2}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: auto
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        'HashMap::from([("a", 1)]),\nHashMap::from([("a", 2)]),'
    )
    app.cleanup()


def test_heterogeneous_strategy_auto_keeps_map_shape_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The auto mode keeps a genuinely map-shaped mapping as a native
    map rather than promoting it to a record (the core #199 concern).
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"k1": 1, "k2": 2}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: auto
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == '("k1", 1),\n("k2", 2),'
    app.cleanup()


def test_heterogeneous_strategy_auto_falls_back_to_record_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The auto mode falls back to record for a record-shaped dict that
    the natural representation cannot hold in a strict-map language.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"id": 1, "desc": "x", "blocks": [1, 2]}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: auto
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        'Record0 { id: 1, desc: "x", blocks: vec![1, 2] },'
    )
    app.cleanup()


def test_heterogeneous_strategy_auto_default_precedence_prefers_tuple_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """With the default precedence, auto skips record (which cannot
    represent a mixed-scalar list) and uses tuple.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: auto
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == '1,\n"hello",'
    app.cleanup()


def test_heterogeneous_strategy_auto_precedence_config_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The precedence config value reorders the strategies auto tries,
    so the same input renders differently.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: auto
           :include-preamble:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={
            "extensions": ["sphinx_literalizer"],
            "literalizer_heterogeneous_strategy_precedence": [
                "tagged_enum",
                "tuple",
            ],
        },
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "enum Value {\n"
        "    I32(i32),\n"
        "    Str(&'static str),\n"
        "}\n"
        "\n"
        'Value::I32(1),\nValue::Str("hello"),'
    )
    app.cleanup()


def test_concrete_heterogeneous_strategy_unrepresentable_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A concrete (non-auto) strategy that cannot represent the input
    surfaces as a clean directive error, not a traceback.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"id": 1, "desc": "x", "blocks": [1, 2]}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: tagged_enum
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Dict has values of mixed type families including a "
            "container, which this heterogeneous strategy cannot "
            "represent (at input path '[0]')"
        ),
    )


def test_skip_if_unrepresentable_emits_no_node_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:skip-if-unrepresentable: emits no node (instead of failing the
    build) when the input cannot be represented in the language.

    ``:heterogeneous-strategy: error`` is set explicitly because the
    default is now ``auto``, under which ``[1, "hello"]`` is
    representable (as a tuple); ``error`` keeps it a hard failure so the
    skip flag has something to skip.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: error
           :skip-if-unrepresentable:
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
    assert not list(doctree.findall(condition=nodes.literal_block))
    app.cleanup()


def test_unrepresentable_without_skip_raises_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :skip-if-unrepresentable: an unrepresentable input is
    still reported as a clean directive error.

    ``:heterogeneous-strategy: error`` is set explicitly because the
    default is now ``auto``, under which ``[1, "hello"]`` is
    representable (as a tuple) and would not fail the build.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: error
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Collection contains heterogeneous scalar types that "
            "cannot be represented in the target language "
            "(found types: int, str)"
        ),
    )


def test_skip_if_unrepresentable_after_auto_exhausts_precedence_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """When auto exhausts the configured precedence without representing
    the input, :skip-if-unrepresentable: emits no node.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"a": 1, "b": [1, "x"]}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: auto
           :skip-if-unrepresentable:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={
            "extensions": ["sphinx_literalizer"],
            "literalizer_heterogeneous_strategy_precedence": [
                "record",
                "tagged_enum",
            ],
        },
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    assert not list(doctree.findall(condition=nodes.literal_block))
    app.cleanup()


def test_heterogeneous_strategy_auto_literalizer_call_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The auto mode integrates with literalizer-call: homogeneous call
    data keeps its natural rendering.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1, 2], [3, 4]]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: rust
           :target-function: add
           :parameter-names: a,b
           :per-element:
           :heterogeneous-strategy: auto
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == "add(1, 2);\nadd(3, 4);"
    app.cleanup()


def test_unset_heterogeneous_strategy_defaults_to_auto_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unset :heterogeneous-strategy: defaults to ``auto`` rather
    than falling through to literalizer's per-language default
    (``error`` for Rust): a record-shaped heterogeneous dict falls back
    to ``record`` instead of failing the build.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"id": 1, "desc": "x", "blocks": [1, 2]}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        'Record0 { id: 1, desc: "x", blocks: vec![1, 2] },'
    )
    app.cleanup()


def test_unset_heterogeneous_strategy_keeps_homogeneous_output_rust(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Defaulting to ``auto`` leaves homogeneous data byte-identical to
    the pre-default behavior: the natural ``HashMap`` rendering is used
    with no fallback applied.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"a": 1}, {"a": 2}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        'HashMap::from([("a", 1)]),\nHashMap::from([("a", 2)]),'
    )
    app.cleanup()


def test_skip_if_unrepresentable_unrepresentable_input_csharp(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:skip-if-unrepresentable: also covers shape-level rejections
    (UnrepresentableInputError), not just heterogeneous collections.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(data="1: a\n2: b\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: csharp
           :skip-if-unrepresentable:
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
    assert not list(doctree.findall(condition=nodes.literal_block))
    app.cleanup()


def test_unrepresentable_input_without_skip_raises_csharp(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A shape-level rejection without :skip-if-unrepresentable: is
    reported as a clean directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(data="1: a\n2: b\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: csharp
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="CSharp cannot represent dict key of type int",
    )


def test_skip_if_unrepresentable_literalizer_call_csharp(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:skip-if-unrepresentable: makes literalizer-call emit no node
    when the call data cannot be represented in the language.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.yaml").write_text(data="- {1: a, 2: b}\n")
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.yaml
           :language: csharp
           :target-function: f
           :parameter-names: m
           :per-element:
           :skip-if-unrepresentable:
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
    assert not list(doctree.findall(condition=nodes.literal_block))
    app.cleanup()


def test_literalizer_call_variable_name_tcl(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:variable-name:`` binds a ``literalizer-call`` result for a
    language that gained call-variable-binding in ``literalizer``
    ``2026.5.17`` (Tcl).
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"count": 42}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: tcl
           :target-function: make_widget
           :parameter-names: count
           :variable-name: my_data
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    expected = 'set my_data [make_widget [dict create "count" 42]]'
    assert text == expected
    app.cleanup()


def test_literalizer_call_existing_variable_d(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:existing-variable:`` binds a ``literalizer-call`` result
    without a declaration keyword for a language that gained
    call-variable-binding in ``literalizer`` ``2026.5.17`` (D).
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"count": 42}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: d
           :target-function: make_widget
           :parameter-names: count
           :variable-name: my_data
           :existing-variable:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    expected = 'my_data = make_widget(JSONValue(["count": JSONValue(42)]));'
    assert text == expected
    app.cleanup()


def test_literalizer_call_wrap_in_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:wrap-in-file:`` on ``literalizer-call`` renders a complete,
    self-contained file: an injected no-op stub for the target function
    precedes the generated calls.

    This exercises ``literalizer`` ``2026.5.17.1``'s self-contained
    ``literalize_call`` file mode (previously ``:wrap-in-file:`` was
    parsed but silently ignored by ``literalizer-call``).
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: make_widget
           :parameter-names: count
           :per-element:
           :wrap-in-file:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    text = literal_block.astext()
    expected = (
        "def make_widget(*_args: object, **_kwargs: object) -> object: ...\n"
        "make_widget(count=1)\n"
        "make_widget(count=2)"
    )
    assert text == expected
    app.cleanup()


def test_record_struct_name_prefix_swift(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Swift's :heterogeneous-strategy: record honours
    :record-struct-name-prefix:, exercising the ``RECORD`` strategy
    ``literalizer`` ``2026.5.17`` added for Swift.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}, {"x": 3, "y": 4}]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: swift
           :heterogeneous-strategy: record
           :record-struct-name-prefix: Row
           :include-delimiters:
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

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "struct Row0 { let x: Int; let y: Int }\n"
        "\n"
        "[\n"
        "    Row0(x: 1, y: 2),\n"
        "    Row0(x: 3, y: 4),\n"
        "]"
    )
    app.cleanup()


def test_json_type_rust_serde_json_value(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:json-type: serde_json_value`` routes Rust through
    ``serde_json::json!`` so heterogeneous data round-trips without
    needing a heterogeneous-strategy fallback.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1, "b": "two"}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :json-type: serde_json_value
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        'serde_json::json!({\n    "a": 1,\n    "b": "two",\n})'
    )
    app.cleanup()


def test_bool_format_perl_json_pp_ref(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    r"""``:bool-format: json_pp_ref`` renders Perl booleans as ``\1`` /
    ``\0`` scalar references, the conventional form for JSON::PP and
    friends.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj=[True, False]),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: perl
           :bool-format: json_pp_ref
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == "[\n    \\1,\n    \\0,\n]"
    app.cleanup()


def test_json_type_rejected_for_unsupported_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A language whose ``JsonTypes`` enum has no matching member
    (e.g. Python) surfaces a clean directive error rather than
    crashing on the constructor kwarg.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :json-type: serde_json_value
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Language 'python' does not support json-type 'serde_json_value'."
        ),
    )
    app.cleanup()


def test_json_rendering_cpp_inline_document(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:json-rendering: inline_document`` renders the C++ JSON value
    as one inline JSON document handed to ``nlohmann::json::parse``
    instead of structural ``nlohmann::json`` factory expressions.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1, "b": "two"}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :json-type: nlohmann_json
           :json-rendering: inline_document
           :variable-name: data
           :include-delimiters:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        'auto data = nlohmann::json::parse(R"json({\n'
        '    "a": 1,\n'
        '    "b": "two"\n'
        '})json");'
    )
    app.cleanup()


def test_json_rendering_rejected_for_unsupported_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A language without a ``JsonRenderings`` enum (e.g. Python)
    surfaces a clean directive error rather than crashing on the
    constructor kwarg.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :json-rendering: inline_document
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support 'json-rendering'.",
    )
    app.cleanup()


def test_json_rendering_requires_json_type(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:json-rendering:`` without ``:json-type:`` surfaces
    literalizer's validation error against the directive.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :json-rendering: inline_document
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Cpp json_rendering selects how json_type values are "
            "rendered and requires json_type to be set."
        ),
    )
    app.cleanup()


def test_error_reports_input_path(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An error tied to one input value reports that value's path.

    literalizer attaches the offending value's input path to its
    errors; the directive error appends it as a compact locator so an
    author can find the value in a large data file.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(
        data=json.dumps(
            obj={"tasks": [{"name": "a", "items": [1, "two"]}]},
        ),
    )
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: error
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Collection contains heterogeneous scalar types that cannot "
            "be represented in the target language (found types: int, "
            "str) (at input path 'tasks[0].items')"
        ),
    )
    app.cleanup()


def test_error_reports_directive_line(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A failing directive is reported at its own line in the document.

    The document has a passing directive first so the reported line
    cannot be right by accident: it identifies the failing block rather
    than the first ``literalizer`` block in the file.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python

        Prose between the blocks.

        .. literalizer:: data.json
           :language: python
           :sequence-format: vec
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    _assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=9,
        message="Language 'python' does not support sequence-format 'vec'.",
    )
    app.cleanup()


def test_errors_do_not_stop_the_build(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """One build reports every failing directive rather than the first.

    Each error is a document error, so the build carries on and an
    author fixing a large tree sees all of the bad blocks in one run.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :sequence-format: vec

        .. literalizer:: data.json
           :language: rust
           :set-format: frozenset
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    document = source_directory / "index.rst"
    reported = strip_colors(app.warning.getvalue()).splitlines()
    assert reported == [
        (
            f"{document}:4: ERROR: Language 'python' does not support "
            "sequence-format 'vec'. [docutils]"
        ),
        (
            f"{document}:8: ERROR: Language 'rust' does not support "
            "set-format 'frozenset'. [docutils]"
        ),
    ]
    app.cleanup()


def test_errors_fail_the_build_with_warnings_as_errors(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A failing directive still fails the build under ``-W``."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :sequence-format: vec
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
        warningiserror=True,
    )
    app.build()
    assert app.statuscode == 1

    document = source_directory / "index.rst"
    reported = strip_colors(app.warning.getvalue()).splitlines()
    assert reported == [
        (
            f"{document}:4: ERROR: Language 'python' does not support "
            "sequence-format 'vec'. [docutils]"
        )
    ]
    app.cleanup()
