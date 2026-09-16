"""Language-default and language-version integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sphinx.errors import ExtensionError
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_tcl_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A JSON array renders correctly for the tcl language."""
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"$reference": "user_obj"}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[{"$reference": "user_obj"}, 42]]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"name": "Ada", "active": True}]),
    )
    _ = (source_directory / "calls.json").write_text(
        data=json.dumps(obj=[{"name": "Ada", "active": True}]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "task.json").write_text(
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
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"name": "Ada", "active": True}]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Java cannot wrap a bare value (without a variable_form) at file "
            "scope"
        ),
    )
