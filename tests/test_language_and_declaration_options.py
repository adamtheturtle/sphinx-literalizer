"""Language and declaration-option integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_swift_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the swift language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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


def test_variable_name_implies_include_delimiters(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A variable form includes collection delimiters without the flag.

    literalizer 2026.8.16+ rejects delimiter-less variable forms, so the
    directive enables delimiters whenever ``:variable-name:`` is set.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
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

    _ = source_file.write_text(
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


def test_wrap_in_file_implies_include_delimiters(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A wrapped file includes collection delimiters without the flag.

    literalizer 2026.8.29+ rejects a whole file built from a
    delimiter-less fragment, so the directive enables delimiters
    whenever ``:wrap-in-file:`` is set.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
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
    assert literal_block.astext() == "(\n    1,\n    2,\n)"
    app.cleanup()


def test_dart_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the dart language."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = (source_directory / "expected.java").write_text(
        data=(
            "public static final int[] myList = new int[]{\n"
            "    1,\n"
            "    2\n"
            "};\n"
        )
    )
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            - 2024-01-15
        """
        )
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
