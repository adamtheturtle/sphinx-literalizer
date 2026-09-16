"""String and collection-layout integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_string_format_single(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :string-format: option changes string quoting style."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=["hello"]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
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
    _ = (source_directory / "index.rst").write_text(
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
        # A Java text block strips incidental leading whitespace, so the
        # indented line keeps its spaces as ``\s`` escapes.
        '"""\nfirst\n\n\\s\\sindented\nlast"""',
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj='first\n)"\nlast'),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj="first\nsecond"),
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj="\nfirst\n\n  indented\nlast\n"),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.yaml").write_text(
        data="- |+\n  first\n\n    indented\n  last\n",
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj="first\nsecond"),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj="first\nsecond"),
    )
    _ = (source_directory / "index.rst").write_text(
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
    assert_directive_error(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1]),
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

    _ = source_file.write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"key": "value"}),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1, 2], [3, 4]]),
    )
    _ = (source_directory / "index.rst").write_text(
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
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[[[1, 2], [3, 4]]]]),
    )
    _ = (source_directory / "index.rst").write_text(
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
