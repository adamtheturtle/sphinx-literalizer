"""Basic literalizer-call integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp


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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[[1, "two"]], [[False, []]]]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2, 3]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42]]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.yaml").write_text(
        data="- 2024-01-15T10:30:00Z\n",
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1]]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[[1]]))
    _ = (source_directory / "zip.json").write_text(
        data=json.dumps(obj=["$call"]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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

    _ = source_file.write_text(
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
