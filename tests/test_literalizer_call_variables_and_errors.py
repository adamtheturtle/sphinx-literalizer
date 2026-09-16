"""Literalizer-call variable and error integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_module_name_java(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :module-name: option overrides the wrapper module name."""
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
           :module-name: Foo
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"x": 1})
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"x": 1})
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"x": 1})
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"x": 1})
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[{"$ref": "my_vec"}, 42]]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"count": 42}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"count": 42}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"count": 42}]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"count": 1}, {"count": 2}]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.yaml").write_text(data="- []\n")
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.yaml").write_text(data="- []\n")
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[[]]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[[]]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.yaml").write_text(data="- []\n")
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[[]]))
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.yaml").write_text(data="1: a\n")
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.yaml").write_text(data="value: .nan\n")
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
