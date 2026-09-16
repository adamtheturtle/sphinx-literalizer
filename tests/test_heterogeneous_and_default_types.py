"""Heterogeneous-value and default-type integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support empty-dict-key 'positional'.",
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, "hello"]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj={}))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'cpp' does not support ':empty-dict-key:'.",
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[[1]]))
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'forth' does not support ':call-style:'.",
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1234.5]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1234.5]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[42]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[42]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    _ = (source_directory / "index.rst").write_text(
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
