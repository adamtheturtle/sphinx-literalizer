"""Declarative printing delegates native syntax and imports upstream."""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import find_cpp_compiler


def _build(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    content: str,
) -> SphinxTestApp:
    """Build a real directive with a shared numeric input."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "data.json").write_text(data="[[7], [9]]")
    _ = (source / "index.rst").write_text(data="Test\n====\n\n" + content)
    app = make_app(
        srcdir=source, confoverrides={"extensions": ["sphinx_literalizer"]}
    )
    app.build()
    return app


def _code(app: SphinxTestApp) -> str:
    """Read emitted code without rewriting any generated text."""
    return "\n\n".join(
        block.astext()
        for block in app.env.get_doctree(docname="index").findall(
            condition=nodes.literal_block
        )
    )


@pytest.mark.parametrize(
    argnames=("language", "expected"),
    argvalues=[
        ("python", "print(calculate(7))"),
        ("java", "System.out.println(calculate(7));"),
        ("typescript", "console.log(calculate(7));"),
        ("cpp", "std::cout << calculate(7) << '\\n';"),
        ("go", "fmt.Println(calculate(7))"),
        ("csharp", "System.Console.WriteLine(calculate(7));"),
    ],
)
def test_print_result_directive(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    language: str,
    expected: str,
) -> None:
    """The directive exposes the upstream operation without a template."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content=f".. literalizer-call:: data.json\n"
        f"   :language: {language}\n"
        "   :target-function: calculate\n"
        "   :parameter-names: value\n"
        "   :call-style: positional\n"
        "   :per-element:\n"
        "   :print-result:\n"
        "   :include-preamble:\n",
    )
    assert app.warning.getvalue() == ""
    assert expected in _code(app=app)
    if language == "typescript":
        assert '/// <reference lib="dom" />' in _code(app=app)
    app.cleanup()


def test_cpp_printed_group_runs(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Generated print imports appear once and compile under
    C++14.
    """
    call = (
        "   .. literalizer-call:: data.json\n"
        "      :language: cpp\n"
        "      :language-version: cpp14\n"
        "      :target-function: calculate\n"
        "      :parameter-names: value\n"
        "      :per-element:\n"
        "      :print-result:\n"
        "      :include-preamble:\n\n"
    )
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content=".. literalizer-group:: cpp\n\n"
        "   .. code-block:: cpp\n\n"
        "      int calculate(int value) { return value * 2; }\n"
        "      int main() {\n\n" + call + call + "   .. code-block:: cpp\n\n"
        "      }\n",
    )
    assert app.warning.getvalue() == ""
    code = _code(app=app)
    assert code.count("#include <iostream>") == 1
    assert code.index("#include <iostream>") < code.index("int main()")
    source = tmp_path / "printed.cpp"
    binary = tmp_path / "printed"
    _ = source.write_text(data=code)
    _ = subprocess.run(  # noqa: S603
        args=[
            find_cpp_compiler(),
            "-std=c++14",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-pedantic-errors",
            str(object=source),
            "-o",
            str(object=binary),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    result = subprocess.run(  # noqa: S603
        args=[str(object=binary)],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.stdout == "14\n18\n14\n18\n"
    app.cleanup()


def test_print_preamble_only(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Preamble-only printing exposes the header without call text."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content=".. literalizer-call:: data.json\n"
        "   :language: cpp\n"
        "   :target-function: calculate\n"
        "   :parameter-names: value\n"
        "   :per-element:\n"
        "   :print-result:\n"
        "   :preamble-only:\n",
    )
    assert app.warning.getvalue() == ""
    assert _code(app=app) == "#include <iostream>"
    app.cleanup()


@pytest.mark.parametrize(
    argnames="conflict",
    argvalues=[
        ":call-transform: custom($0)",
        ":variable-name: result",
        ":zip-file: data.json",
    ],
)
def test_print_conflicts_report_directive_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    conflict: str,
) -> None:
    """Authors receive an actionable error for ambiguous result
    handling.
    """
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content=".. literalizer-call:: data.json\n"
        "   :language: cpp\n"
        "   :target-function: calculate\n"
        "   :parameter-names: value\n"
        "   :per-element:\n"
        "   :print-result:\n"
        f"   {conflict}\n",
    )
    assert "print_result cannot be combined" in app.warning.getvalue()
    app.cleanup()
