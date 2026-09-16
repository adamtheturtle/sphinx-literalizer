"""Comment and type-option integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_comment_format_block(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :comment-format: option changes the comment style."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            # a comment
            key: value
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

    _ = source_file.write_text(
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


@pytest.mark.parametrize(
    argnames=("collection_layout", "expected"),
    argvalues=[
        (
            "compact",
            """\
(
    # first case
    ({"a": 1, "b": 2}, "x"),
    # second case
    ({"a": 3}, "y"),
    # third case
    ({"a": 4}, "z"),
)""",
        ),
        (
            "multiline",
            """\
(
    # first case
    (
        {
            "a": 1,
            "b": 2,
        },
        "x",
    ),
    # second case
    (
        {
            "a": 3,
        },
        "y",
    ),
    # third case
    (
        {
            "a": 4,
        },
        "z",
    ),
)""",
        ),
    ],
)
def test_element_comments_label_their_own_element(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    collection_layout: str,
    expected: str,
) -> None:
    """A comment before an element is rendered before that element.

    Comments in the data file are the labels an author writes for each
    element, so a comment that slides onto another element -- or is
    dropped -- silently mislabels the rendered block.  Both
    collection layouts are covered because an element that renders
    across several lines is where that has gone wrong before.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            # first case
            - - a: 1
                b: 2
              - x

            # second case
            - - a: 3
              - y

            # third case
            - - a: 4
              - z
        """
        )
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer:: data.yaml
           :language: python
           :include-delimiters:
           :collection-layout: {collection_layout}
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
    assert literal_block.astext() == expected
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("collection_layout", "expected"),
    argvalues=[
        (
            "compact",
            """\
# first case
check(values={"a": 1, "b": 2}, name="x")
# second case
check(values={"a": 3}, name="y")
# third case
check(values={"a": 4}, name="z")""",
        ),
        (
            "multiline",
            """\
# first case
check(values={
    "a": 1,
    "b": 2,
}, name="x")
# second case
check(values={
    "a": 3,
}, name="y")
# third case
check(values={
    "a": 4,
}, name="z")""",
        ),
    ],
)
def test_literalizer_call_per_element_element_comments(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    collection_layout: str,
    expected: str,
) -> None:
    """Each generated call keeps the comment that labels its element.

    ``:per-element:`` is how a data file of test cases becomes one call
    per case, so a comment landing on the wrong call -- or disappearing
    after the first -- mislabels the generated calls.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.yaml").write_text(
        data=dedent(
            text="""\
            # first case
            - - a: 1
                b: 2
              - x

            # second case
            - - a: 3
              - y

            # third case
            - - a: 4
              - z
        """
        )
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer-call:: data.yaml
           :language: python
           :target-function: check
           :parameter-names: values,name
           :per-element:
           :collection-layout: {collection_layout}
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
    assert literal_block.astext() == expected
    app.cleanup()


def test_unsupported_comment_format_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An unsupported comment-format is reported as a directive error."""
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
           :comment-format: block
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.yaml").write_text(data="- hello\n- 42\n")
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1, "b": 2}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1}),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[255]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1000000]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
