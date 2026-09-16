"""Record-strategy integration tests."""

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_heterogeneous_strategy_record_go(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Go's :heterogeneous-strategy: record renders a record-shaped
    mapping as a generated struct with the default name prefix.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"flag": True, "count": 1}),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: go
           :heterogeneous-strategy: record
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
    assert literal_block.astext() == (
        "package main\n"
        "type Record0 struct {\n"
        "\tFlag bool\n"
        "\tCount int\n"
        "}\n"
        "\n"
        "Record0{\n"
        "\tFlag: true,\n"
        "\tCount: 1,\n"
        "}"
    )
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("language", "expected_output"),
    argvalues=[
        (
            "csharp",
            (
                "using System.Collections.Generic;\n"
                "record Record0(string Name, "
                "Dictionary<string, object> Input, "
                "Dictionary<string, object> Expected);\n"
                "\n"
                "new[] {\n"
                '    new Record0("test_1", '
                'new Dictionary<string, object> {["type"] = "create", '
                '["pr_id"] = "pr_1", ["draft"] = true}, '
                'new Dictionary<string, object> {["pr_id"] = "pr_1", '
                '["status"] = "draft"}),\n'
                '    new Record0("test_2", '
                'new Dictionary<string, object> {["type"] = "publish", '
                '["pr_id"] = "pr_1"}, '
                "new Dictionary<string, object> "
                '{["error"] = "invalid_operation"})\n'
                "}"
            ),
        ),
        (
            "cpp",
            (
                "#include <initializer_list>\n"
                "#include <string>\n"
                "#include <map>\n"
                "#include <vector>\n"
                "#include <variant>\n"
                "using LiteralizerRecordValue = "
                "std::variant<std::string, bool>;\n"
                "struct Record0 { std::string name; "
                "std::map<std::string, LiteralizerRecordValue> input; "
                "std::map<std::string, LiteralizerRecordValue> expected; };\n"
                "\n"
                "std::vector{\n"
                '    Record0{.name = "test_1", '
                ".input = "
                '{{"type", LiteralizerRecordValue{"create"}}, '
                '{"pr_id", LiteralizerRecordValue{"pr_1"}}, '
                '{"draft", LiteralizerRecordValue{true}}}, '
                ".expected = "
                '{{"pr_id", LiteralizerRecordValue{"pr_1"}}, '
                '{"status", LiteralizerRecordValue{"draft"}}}},\n'
                '    Record0{.name = "test_2", '
                ".input = "
                '{{"type", LiteralizerRecordValue{"publish"}}, '
                '{"pr_id", LiteralizerRecordValue{"pr_1"}}}, '
                ".expected = "
                '{{"error", LiteralizerRecordValue{"invalid_operation"}}}},\n'
                "}"
            ),
        ),
        (
            "go",
            (
                "package main\n"
                "type Record0 struct {\n"
                "\tName string\n"
                "\tInput map[string]any\n"
                "\tExpected map[string]any\n"
                "}\n"
                "\n"
                "[]Record0{\n"
                '\tRecord0{Name: "test_1", '
                'Input: map[string]any{"type": "create", "pr_id": "pr_1", '
                '"draft": true}, '
                'Expected: map[string]any{"pr_id": "pr_1", '
                '"status": "draft"}},\n'
                '\tRecord0{Name: "test_2", '
                'Input: map[string]any{"type": "publish", "pr_id": "pr_1"}, '
                'Expected: map[string]any{"error": "invalid_operation"}},\n'
                "}"
            ),
        ),
        (
            "java",
            (
                "import java.util.Map;\n"
                "record Record0(String name, "
                "java.util.Map<String, Object> input, "
                "java.util.Map<String, Object> expected) {}\n"
                "\n"
                "new Record0[]{\n"
                '    new Record0("test_1", '
                'Map.ofEntries(Map.entry("type", "create"), '
                'Map.entry("pr_id", "pr_1"), Map.entry("draft", true)), '
                'Map.ofEntries(Map.entry("pr_id", "pr_1"), '
                'Map.entry("status", "draft"))),\n'
                '    new Record0("test_2", '
                'Map.ofEntries(Map.entry("type", "publish"), '
                'Map.entry("pr_id", "pr_1")), '
                'Map.ofEntries(Map.entry("error", "invalid_operation")))\n'
                "}"
            ),
        ),
        (
            "kotlin",
            (
                "data class Record0(val name: String, "
                "val input: Map<String, Any?>, "
                "val expected: Map<String, Any?>)\n"
                "\n"
                "listOf<Record0>(\n"
                '    Record0(name = "test_1", '
                'input = mapOf<String, Any?>("type" to "create", '
                '"pr_id" to "pr_1", "draft" to true), '
                'expected = mapOf<String, Any?>("pr_id" to "pr_1", '
                '"status" to "draft")),\n'
                '    Record0(name = "test_2", '
                'input = mapOf<String, Any?>("type" to "publish", '
                '"pr_id" to "pr_1"), '
                "expected = mapOf<String, Any?>"
                '("error" to "invalid_operation")),\n'
                ")"
            ),
        ),
        (
            "rust",
            (
                "use std::collections::HashMap;\n"
                "enum Value {\n"
                "    Str(&'static str),\n"
                "    Bool(bool),\n"
                "}\n"
                "struct Record0 {\n"
                "    name: &'static str,\n"
                "    input: HashMap<&'static str, Value>,\n"
                "    expected: HashMap<&'static str, Value>,\n"
                "}\n"
                "\n"
                "vec![\n"
                '    Record0 { name: "test_1", '
                'input: HashMap::from([("type", Value::Str("create")), '
                '("pr_id", Value::Str("pr_1")), '
                '("draft", Value::Bool(true))]), '
                'expected: HashMap::from([("pr_id", Value::Str("pr_1")), '
                '("status", Value::Str("draft"))]) },\n'
                '    Record0 { name: "test_2", '
                'input: HashMap::from([("type", Value::Str("publish")), '
                '("pr_id", Value::Str("pr_1"))]), '
                "expected: HashMap::from("
                '[("error", Value::Str("invalid_operation"))]) },\n'
                "]"
            ),
        ),
        (
            "scala",
            (
                "case class Record0(name: String, input: Map[String, Any], "
                "expected: Map[String, Any])\n"
                "\n"
                "List(\n"
                '    Record0(name = "test_1", '
                'input = Map[String, Any]("type" -> "create", '
                '"pr_id" -> "pr_1", "draft" -> true), '
                'expected = Map[String, Any]("pr_id" -> "pr_1", '
                '"status" -> "draft")),\n'
                '    Record0(name = "test_2", '
                'input = Map[String, Any]("type" -> "publish", '
                '"pr_id" -> "pr_1"), '
                'expected = Map[String, Any]("error" -> "invalid_operation")),'
                "\n"
                ")"
            ),
        ),
    ],
)
def test_record_nested_map_fallback(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    language: str,
    expected_output: str,
) -> None:
    """Record rendering keeps one outer shape and falls back to maps
    for incompatible nested sibling shapes in statically typed targets.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[
                {
                    "name": "test_1",
                    "input": {
                        "type": "create",
                        "pr_id": "pr_1",
                        "draft": True,
                    },
                    "expected": {"pr_id": "pr_1", "status": "draft"},
                },
                {
                    "name": "test_2",
                    "input": {"type": "publish", "pr_id": "pr_1"},
                    "expected": {"error": "invalid_operation"},
                },
            ],
        ),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer:: data.json
           :language: {language}
           :heterogeneous-strategy: record
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
    output = literal_block.astext()
    assert output == expected_output
    app.cleanup()


def test_record_struct_name_prefix_python(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Python's :heterogeneous-strategy: record honours
    :record-struct-name-prefix: for the generated dataclass name.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}, {"x": 3, "y": 4}]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :heterogeneous-strategy: record
           :record-struct-name-prefix: Row
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
    assert literal_block.astext() == (
        "from __future__ import annotations\n"
        "import dataclasses\n"
        "@dataclasses.dataclass(frozen=True)\n"
        "class Row0:\n"
        "    x: int\n"
        "    y: int\n"
        "\n"
        "(\n"
        "    Row0(x=1, y=2),\n"
        "    Row0(x=3, y=4),\n"
        ")"
    )
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("strategy", "data", "expected"),
    argvalues=[
        (
            "tuple",
            [1, "Ada", True],
            'std::make_tuple(\n    1,\n    "Ada",\n    true\n)',
        ),
        (
            "record",
            [{"name": "Ada", "score": 42}],
            "struct Candidate0 { std::string name; int score{}; };",
        ),
    ],
)
def test_cpp14_candidate_facing_heterogeneous_strategies(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    strategy: str,
    data: list[object] | dict[str, int | str],
    expected: str,
) -> None:
    """C++14 exposes tuple and named-record alternatives to wrappers."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=data))
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: {strategy}
           :record-struct-name-prefix: Candidate
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
    output = literal_block.astext()
    assert expected in output
    if strategy == "tuple":
        assert "LiteralizerVariant" not in output
    app.cleanup()


def test_cpp14_named_carrier_preamble_only(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Literalizer forwards a carrier name and can omit literal code."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[{"name": "build", "args": [1, "fast", None]}],
        ),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :heterogeneous-value-name: TaskValue
           :record-struct-name-prefix: Task
           :include-delimiters:
           :preamble-only:

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :heterogeneous-value-name: TaskValue
           :record-struct-name-prefix: Task
           :include-delimiters:
           :variable-name: task
           :pre-indent-level: 1
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
    preamble_block, literal_block = doctree.findall(
        condition=nodes.literal_block,
    )
    preamble = preamble_block.astext()
    literal = literal_block.astext()
    assert "struct TaskValue {" in preamble
    assert "struct Task0 {" in preamble
    assert "auto task =" not in preamble
    assert "struct TaskValue {" not in literal
    assert "auto task = std::vector<Task0>{" in literal

    app.cleanup()


def _find_cpp_compiler() -> str:
    """Return an available C++ compiler."""
    compiler = shutil.which(cmd="clang++")
    if compiler is None:
        compiler = shutil.which(cmd="g++")
    if compiler is None:
        msg = "A C++ compiler is required for this test."
        raise RuntimeError(msg)
    return compiler


def test_cpp_compiler_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing C++ compiler fails instead of skipping the composition
    test.
    """
    monkeypatch.setattr(
        target=shutil, name="which", value=Mock(return_value=None)
    )
    with pytest.raises(
        expected_exception=RuntimeError,
        match="A C\\+\\+ compiler is required",
    ):
        _ = _find_cpp_compiler()


def test_literalizer_call_named_carrier_preamble_only(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Literalizer-call composes a named carrier with later C++14 code."""
    compiler = _find_cpp_compiler()

    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[["build", [1, "fast", None]]]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :heterogeneous-value-name: TaskValue
           :target-function: run
           :parameter-names: name,args
           :per-element:
           :preamble-only:

        .. literalizer-call:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :heterogeneous-value-name: TaskValue
           :target-function: run
           :parameter-names: name,args
           :per-element:
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
    preamble_block, call_block = doctree.findall(
        condition=nodes.literal_block,
    )
    assert "struct TaskValue {" in preamble_block.astext()
    assert (
        "std::make_shared<TypedHolder<std::string>>" in preamble_block.astext()
    )
    assert "run(" not in preamble_block.astext()
    assert "struct TaskValue {" not in call_block.astext()
    assert call_block.astext() == (
        'run("build", std::vector<TaskValue>{'
        'TaskValue{1}, TaskValue{"fast"}, TaskValue{nullptr}});'
    )
    combined = (
        "#include <cassert>\n\n"
        f"{preamble_block.astext()}\n\n"
        "void run(const std::string&, "
        "const std::vector<TaskValue>& values) {\n"
        "    assert(values.at(1).is<std::string>());\n"
        '    assert(values.at(1).get<std::string>() == "fast");\n'
        "    assert(!values.at(1).is<const char*>());\n"
        "}\n\n"
        "int main() {\n"
        f"    {call_block.astext()}\n"
        "    return 0;\n"
        "}\n"
    )
    assert combined.count("struct TaskValue {") == 1
    combined_path = tmp_path / "combined.cpp"
    _ = combined_path.write_text(data=combined)
    executable_path = tmp_path / "combined"
    _ = subprocess.run(  # noqa: S603
        args=[
            compiler,
            "-std=c++14",
            str(object=combined_path),
            "-o",
            str(object=executable_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    _ = subprocess.run(  # noqa: S603
        args=[str(object=executable_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    app.cleanup()


def test_heterogeneous_value_name_unsupported_language_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A carrier name on an unsupported language raises a clear error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(data="[1, 2]")
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :heterogeneous-value-name: Value
    """
        ),
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Language 'python' does not support ':heterogeneous-value-name:'.",
    )


@dataclass(frozen=True, kw_only=True)
class _HeterogeneousValueNameCase:
    """A language-specific heterogeneous-value-name expectation."""

    language: str
    strategy: str
    data: list[object]
    expected: str


@pytest.mark.parametrize(
    argnames="case",
    argvalues=[
        _HeterogeneousValueNameCase(
            language="rust",
            strategy="tagged_enum",
            data=[1, "x", None],
            expected="enum TaskValue {",
        ),
        _HeterogeneousValueNameCase(
            language="mojo",
            strategy="variant",
            data=[1, "x"],
            expected="comptime TaskValue = Variant[",
        ),
        _HeterogeneousValueNameCase(
            language="nim",
            strategy="object_variant",
            data=[1, "x", None],
            expected="TaskValueKind = enum",
        ),
        _HeterogeneousValueNameCase(
            language="dhall",
            strategy="union_type",
            data=[1, "x", None],
            expected="let TaskValue = <",
        ),
    ],
)
def test_heterogeneous_value_name_supported_languages(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    case: _HeterogeneousValueNameCase,
) -> None:
    """The general name option reaches each language-specific setting."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=case.data)
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer:: data.json
           :language: {case.language}
           :heterogeneous-strategy: {case.strategy}
           :heterogeneous-value-name: TaskValue
           :include-delimiters:
           :include-preamble:
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
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert case.expected in literal_block.astext()
    app.cleanup()
