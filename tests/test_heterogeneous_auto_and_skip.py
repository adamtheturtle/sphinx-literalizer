"""Automatic heterogeneous-strategy integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sphinx.errors import ExtensionError
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, True, "x"]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"a": 1}, {"a": 2}]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"k1": 1, "k2": 2}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"id": 1, "desc": "x", "blocks": [1, 2]}]),
    )
    _ = (source_directory / "index.rst").write_text(
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


def test_heterogeneous_strategy_precedence_requires_string_list(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Invalid strategy precedence is rejected by a public Sphinx
    build.
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
           :heterogeneous-strategy: auto
    """
        )
    )
    app = make_app(
        srcdir=source_directory,
        confoverrides={
            "extensions": ["sphinx_literalizer"],
            "literalizer_heterogeneous_strategy_precedence": 42,
        },
    )

    with pytest.raises(
        expected_exception=ExtensionError,
        match=(
            "'literalizer_heterogeneous_strategy_precedence' must be "
            "a list of strings"
        ),
    ):
        app.build()


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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"id": 1, "desc": "x", "blocks": [1, 2]}]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    assert len(list(doctree.findall(condition=nodes.literal_block))) == 0
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
           :heterogeneous-strategy: error
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"a": 1, "b": [1, "x"]}]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert len(list(doctree.findall(condition=nodes.literal_block))) == 0
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1, 2], [3, 4]]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"id": 1, "desc": "x", "blocks": [1, 2]}]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"a": 1}, {"a": 2}]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.yaml").write_text(data="1: a\n2: b\n")
    _ = (source_directory / "index.rst").write_text(
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
    assert len(list(doctree.findall(condition=nodes.literal_block))) == 0
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
    _ = (source_directory / "data.yaml").write_text(data="1: a\n2: b\n")
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.yaml").write_text(data="- {1: a, 2: b}\n")
    _ = (source_directory / "index.rst").write_text(
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
    assert len(list(doctree.findall(condition=nodes.literal_block))) == 0
    app.cleanup()
