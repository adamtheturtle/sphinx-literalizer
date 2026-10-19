"""Scoped preamble composition through real Sphinx builds."""

import subprocess
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import find_cpp_compiler


def _build_group(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    content: str,
) -> SphinxTestApp:
    """Build a document with two reusable input files."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "logs.json").write_text(data="[[1, 0, 3600]]")
    _ = (source / "machines.json").write_text(data='[[1, "Mainframe1"]]')
    _ = (source / "mixed.json").write_text(data='[[true, "Mainframe1"]]')
    _ = (source / "flat.json").write_text(data='[1, "Mainframe1"]')
    _ = (source / "index.rst").write_text(
        data="Test\n====\n\n" + dedent(text=content),
    )
    app = make_app(
        srcdir=source,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    return app


def _blocks(app: SphinxTestApp) -> list[nodes.literal_block]:
    """Read the actual generated code nodes."""
    return list(
        app.env.get_doctree(docname="index").findall(
            condition=nodes.literal_block,
        ),
    )


def test_cpp_group_compiles(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Different inputs share headers at the top and retain their
    values.
    """
    app = _build_group(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. literalizer-group:: cpp

           |

           .. literalizer:: logs.json
              :language: cpp
              :variable-name: serviceLogs
              :include-preamble:
              :language-version: cpp14

           |

           .. literalizer:: machines.json
              :language: cpp
              :variable-name: serviceToMachines
              :heterogeneous-strategy: tuple
              :include-preamble:
              :language-version: cpp14

           .. code-block:: cpp

              int main() {
                  return serviceLogs[0][2] != 3600 ||
                      std::get<1>(serviceToMachines[0]) != "Mainframe1";
              }
        """,
    )
    assert app.warning.getvalue() == ""
    header, logs, machines, _main = _blocks(app=app)
    code = "\n\n".join(block.astext() for block in _blocks(app=app))
    assert header.astext().count("#include <vector>") == 1
    assert "#include <tuple>" in header.astext()
    assert "#include" not in logs.astext() + machines.astext()
    assert all(block.rawsource == block.astext() for block in _blocks(app=app))
    assert tmp_path / "source/logs.json" in app.env.dependencies["index"]
    assert tmp_path / "source/machines.json" in app.env.dependencies["index"]
    source = tmp_path / "group.cpp"
    binary = tmp_path / "group"
    _ = source.write_text(data=code)
    # Compile the rendered document, then verify its values at runtime.
    _ = subprocess.run(  # noqa: S603
        args=[
            find_cpp_compiler(),
            "-std=c++14",
            "-Wall",
            "-Wextra",
            "-pedantic-errors",
            str(object=source),
            "-o",
            str(object=binary),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    _ = subprocess.run(  # noqa: S603
        args=[str(object=binary)],
        check=True,
        capture_output=True,
        timeout=10,
    )
    app.cleanup()


def test_multiline_helpers_are_atomic(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Identical Rust enums are emitted once without losing braces."""
    app = _build_group(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. literalizer-group:: rust

           .. literalizer:: machines.json
              :language: rust
              :variable-name: first
              :heterogeneous-strategy: tagged_enum
              :include-preamble:

           .. literalizer:: machines.json
              :language: rust
              :variable-name: second
              :heterogeneous-strategy: tagged_enum
              :include-preamble:
        """,
    )
    assert app.warning.getvalue() == ""
    header, first, second = _blocks(app=app)
    assert header.astext().count("enum Value {") == 1
    assert header.astext().endswith("}")
    assert "I32(i32)," in header.astext()
    assert "Str(&'static str)," in header.astext()
    assert "enum Value" not in first.astext() + second.astext()
    app.cleanup()


@pytest.mark.parametrize(argnames="grouped", argvalues=[True, False])
def test_independent_examples_keep_their_preambles(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    grouped: bool,
) -> None:
    """Removing repeated entries affects only the enclosing group."""
    fragment = """\
        .. literalizer:: logs.json
           :language: cpp
           :variable-name: logs
           :include-preamble:
    """
    content = dedent(text=fragment)
    if grouped:
        content = ".. literalizer-group:: cpp\n\n" + "\n".join(
            "   " + line for line in content.splitlines()
        )
    app = _build_group(
        make_app=make_app,
        tmp_path=tmp_path,
        content=content + "\n\n" + content,
    )
    assert app.warning.getvalue() == ""
    text = "\n".join(block.astext() for block in _blocks(app=app))
    assert text.count("#include <vector>") == 2
    app.cleanup()


def test_call_and_preamble_only(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Call preambles join literal preambles; preamble-only adds no
    body.
    """
    app = _build_group(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. literalizer-group:: cpp

           .. literalizer:: logs.json
              :language: cpp
              :include-delimiters:
              :preamble-only:

           .. literalizer-call:: logs.json
              :language: cpp
              :target-function: consume
              :parameter-names: logs
              :include-preamble:
        """,
    )
    assert app.warning.getvalue() == ""
    header, call = _blocks(app=app)
    assert header.astext().count("#include <vector>") == 1
    assert call.astext().startswith("consume(")
    assert "#include" not in call.astext()
    app.cleanup()


def test_no_requested_preamble_and_skipped_input(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Groups retain no-preamble choices and do not revive skipped
    inputs.
    """
    app = _build_group(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. literalizer-group:: python

           .. literalizer:: logs.json
              :language: python
              :variable-name: logs

        .. literalizer-group:: rust

           .. literalizer:: flat.json
              :language: rust
              :heterogeneous-strategy: error
              :skip-if-unrepresentable:
        """,
    )
    assert app.warning.getvalue() == ""
    (block,) = _blocks(app=app)
    assert block.astext() == "logs = (\n    (1, 0, 3600),\n)"
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("content", "message"),
    argvalues=[
        (
            ".. literalizer-group:: cpp\n\n   A paragraph.\n",
            "literalizer-group accepts only code directives.",
        ),
        (
            (
                ".. literalizer-group:: cpp\n\n"
                "   .. code-block:: python\n\n      print(1)\n"
            ),
            "Every code block in literalizer-group must use language 'cpp'.",
        ),
        (
            (
                ".. literalizer-group:: cpp\n\n"
                "   .. literalizer-group:: cpp\n\n"
                "      .. code-block:: cpp\n\n         int x;\n"
            ),
            "literalizer-group cannot be nested.",
        ),
        (
            (
                ".. literalizer-group:: cpp\n\n"
                "   .. literalizer:: logs.json\n      :language: invalid\n"
            ),
            '"invalid" unknown',
        ),
        (
            """\
            .. literalizer-group:: rust

               .. literalizer:: mixed.json
                  :language: rust
                  :heterogeneous-strategy: tagged_enum
                  :include-preamble:

               .. literalizer:: machines.json
                  :language: rust
                  :heterogeneous-strategy: tagged_enum
                  :include-preamble:
            """,
            "literalizer-group cannot reconcile different generated helper",
        ),
    ],
)
def test_group_errors(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    """Invalid groups produce source-located Sphinx diagnostics."""
    app = _build_group(
        make_app=make_app,
        tmp_path=tmp_path,
        content=content,
    )
    assert message in app.warning.getvalue()
    assert "index.rst:" in app.warning.getvalue()
    app.cleanup()
