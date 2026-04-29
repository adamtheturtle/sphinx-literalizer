# pylint: disable=too-many-lines
"""Integration tests for the Sphinx extension."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sphinx.errors import ExtensionError
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

           1705314600.0,
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
    """An unsupported modifier raises a clear ExtensionError."""
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"^Language 'python' does not support modifier 'public'\.$",
    ):
        app.build()


def test_modifiers_without_variable_name_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Using :modifiers: without :variable-name: raises an
    ExtensionError.
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
           :modifiers: public
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"^':modifiers:' requires ':variable-name:'\.$",
    ):
        app.build()


def test_modifiers_with_existing_variable_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Combining :modifiers: with :existing-variable: raises an
    ExtensionError.
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
           :existing-variable:
           :modifiers: public
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    with pytest.raises(
        expected_exception=ExtensionError,
        match=(
            r"^':modifiers:' cannot be combined with "
            r"':existing-variable:'\.$"
        ),
    ):
        app.build()


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
    """An unsupported sequence-format raises a clear ExtensionError."""
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'python' does not support sequence-format 'vec'\.",
    ):
        app.build()


def test_unsupported_set_format_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported set-format raises a clear ExtensionError."""
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'rust' does not support set-format 'frozenset'\.",
    ):
        app.build()


def test_unsupported_bytes_format_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported bytes-format raises a clear ExtensionError."""
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'rust' does not support bytes-format 'python'\.",
    ):
        app.build()


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
    """An unsupported comment-format raises a clear ExtensionError."""
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'python' does not support comment-format 'block'\.",
    ):
        app.build()


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


def test_line_ending_none(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :line-ending: option controls statement terminators."""
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
           :variable-name: x
           :include-delimiters:
           :line-ending: semicolon
    """
        )
    )
    semi_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    semi_app.build()
    assert semi_app.statuscode == 0
    semi_html = (semi_app.outdir / "index.html").read_text()
    semi_app.cleanup()

    source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: javascript
           :variable-name: x
           :include-delimiters:
           :line-ending: none
    """
        )
    )
    none_app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    none_app.build()
    assert none_app.statuscode == 0
    none_html = (none_app.outdir / "index.html").read_text()
    none_app.cleanup()

    assert semi_html != none_html


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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'python' does not support empty-dict-key 'positional'\.",
    ):
        app.build()


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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=(
            r"Language 'python' does not support "
            r"heterogeneous-strategy 'tagged_enum'\."
        ),
    ):
        app.build()


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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'javascript' does not support 'default-set-element-type'\.",
    ):
        app.build()


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
    """An unsupported dict-entry-style raises a clear ExtensionError."""
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'python' does not support dict-entry-style 'symbol'\.",
    ):
        app.build()


def test_unsupported_numeric_literal_suffix_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported numeric-literal-suffix raises a clear
    ExtensionError.
    """
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'python' does not support numeric-literal-suffix 'auto'\.",
    ):
        app.build()


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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'python' does not support 'default-ordered-map-value-type'\.",
    ):
        app.build()


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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Cannot determine input format for 'data\.dat'\.",
    ):
        app.build()


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


def test_include_preamble_no_effect_python(
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
           :language: python
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

        .. code-block:: python

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
    assert "process(1, 42);" in text
    assert "process(0, 99);" in text
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'python' does not support call-style 'object'\.",
    ):
        app.build()


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
    """A row whose value count differs from :parameter-names: raises a
    clear ExtensionError instead of a raw traceback.
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=(
            r"':parameter-names:' has 2 entries but the data provides "
            r"a different number of values: "
            r"Expected 2 parameters but got 3 values"
        ),
    ):
        app.build()


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
    """Using :module-name: with a language that lacks a named scope
    raises a clear ExtensionError.
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
    with pytest.raises(
        expected_exception=ExtensionError,
        match=r"Language 'python' does not support ':module-name:'\.",
    ):
        app.build()
