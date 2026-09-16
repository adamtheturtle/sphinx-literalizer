"""Advanced output-option integration tests."""

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_literalizer_call_variable_name_tcl(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:variable-name:`` binds a ``literalizer-call`` result for a
    language that gained call-variable-binding in ``literalizer``
    ``2026.5.17`` (Tcl).
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
           :language: tcl
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
    expected = 'set my_data [make_widget [dict create "count" 42]]'
    assert text == expected
    app.cleanup()


def test_literalizer_call_existing_variable_d(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:existing-variable:`` binds a ``literalizer-call`` result
    without a declaration keyword for a language that gained
    call-variable-binding in ``literalizer`` ``2026.5.17`` (D).
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
           :language: d
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
    expected = 'my_data = make_widget(JSONValue(["count": JSONValue(42)]));'
    assert text == expected
    app.cleanup()


def test_literalizer_call_wrap_in_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:wrap-in-file:`` on ``literalizer-call`` renders a complete,
    self-contained file: an injected no-op stub for the target function
    precedes the generated calls.

    This exercises ``literalizer`` ``2026.5.17.1``'s self-contained
    ``literalize_call`` file mode (previously ``:wrap-in-file:`` was
    parsed but silently ignored by ``literalizer-call``).
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: make_widget
           :parameter-names: count
           :per-element:
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
    expected = (
        "def make_widget(*_args: object, **_kwargs: object) -> object: ...\n"
        "make_widget(count=1)\n"
        "make_widget(count=2)"
    )
    assert text == expected
    app.cleanup()


def test_record_struct_name_prefix_swift(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Swift's :heterogeneous-strategy: record honours
    :record-struct-name-prefix:, exercising the ``RECORD`` strategy
    ``literalizer`` ``2026.5.17`` added for Swift.
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
           :language: swift
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
        "struct Row0 { let x: Int; let y: Int }\n"
        "\n"
        "[\n"
        "    Row0(x: 1, y: 2),\n"
        "    Row0(x: 3, y: 4),\n"
        "]"
    )
    app.cleanup()


def test_json_type_rust_serde_json_value(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:json-type: serde_json_value`` routes Rust through
    ``serde_json::json!`` so heterogeneous data round-trips without
    needing a heterogeneous-strategy fallback.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1, "b": "two"}),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :json-type: serde_json_value
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
    assert literal_block.astext() == (
        'serde_json::json!({\n    "a": 1,\n    "b": "two",\n})'
    )
    app.cleanup()


def test_bool_format_perl_json_pp_ref(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    r"""``:bool-format: json_pp_ref`` renders Perl booleans as ``\1`` /
    ``\0`` scalar references, the conventional form for JSON::PP and
    friends.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[True, False]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: perl
           :bool-format: json_pp_ref
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
    assert literal_block.astext() == "[\n    \\1,\n    \\0,\n]"
    app.cleanup()


def test_json_type_rejected_for_unsupported_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A language whose ``JsonTypes`` enum has no matching member
    (e.g. Python) surfaces a clean directive error rather than
    crashing on the constructor kwarg.
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
           :json-type: serde_json_value
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
            "Language 'python' does not support json-type 'serde_json_value'."
        ),
    )
    app.cleanup()


def test_json_rendering_cpp_inline_document(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:json-rendering: inline_document`` renders the C++ JSON value
    as one inline JSON document handed to ``nlohmann::json::parse``
    instead of structural ``nlohmann::json`` factory expressions.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"a": 1, "b": "two"}),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :json-type: nlohmann_json
           :json-rendering: inline_document
           :variable-name: data
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
    assert literal_block.astext() == (
        'auto data = nlohmann::json::parse(R"json({\n'
        '    "a": 1,\n'
        '    "b": "two"\n'
        '})json");'
    )
    app.cleanup()


def test_json_rendering_rejected_for_unsupported_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A language without a ``JsonRenderings`` enum (e.g. Python)
    surfaces a clean directive error rather than crashing on the
    constructor kwarg.
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
           :json-rendering: inline_document
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
            "Language 'python' does not support json-rendering "
            "'inline_document'."
        ),
    )
    app.cleanup()


def test_json_rendering_requires_json_type(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:json-rendering:`` without ``:json-type:`` surfaces
    literalizer's validation error against the directive.
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
           :language: cpp
           :json-rendering: inline_document
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
            "Cpp json_rendering selects how json_type values are "
            "rendered and requires json_type to be set."
        ),
    )
    app.cleanup()


def _record_map_value_typing_preamble(
    *,
    make_app: Callable[..., SphinxTestApp],
    source_directory: Path,
    second_row_tier: object,
    option_lines: str,
) -> str:
    """Render a ``RECORD`` document whose ``attributes`` field is widened.

    The two rows' ``attributes`` maps have different keys, so the field
    cannot become a record of its own and falls back to a plain map.
    *second_row_tier* varies only the widened values' types, so two
    calls show whether the declared map value type follows the data.
    """
    rows: list[Mapping[str, object]] = [
        {"name": "row_1", "attributes": {"region": "emea", "zone": "z1"}},
        {"name": "row_2", "attributes": {"tier": second_row_tier}},
    ]
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=rows),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: record
           :record-shape-names: name,attributes=Row
           :preamble-only:
        """
        )
        + option_lines,
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    preamble = literal_block.astext()
    app.cleanup()
    return preamble


def test_record_map_value_typing_narrow_is_the_default(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without the option, the widened map's value type follows the
    data, so uniform string values give a ``&'static str`` map.
    """
    preamble = _record_map_value_typing_preamble(
        make_app=make_app,
        source_directory=tmp_path / "source",
        second_row_tier="gold",
        option_lines="",
    )

    assert preamble == (
        "use std::collections::HashMap;\n"
        "struct Row {\n"
        "    name: &'static str,\n"
        "    attributes: HashMap<&'static str, &'static str>,\n"
        "}"
    )


def test_record_map_value_typing_wide(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:record-map-value-typing: wide`` declares the widened map with
    the strategy's value carrier, so the field is declared the same way
    for data whose widened scalars share one type and data whose do not.
    """
    uniform_preamble = _record_map_value_typing_preamble(
        make_app=make_app,
        source_directory=tmp_path / "uniform",
        second_row_tier="gold",
        option_lines="   :record-map-value-typing: wide\n",
    )
    mixed_preamble = _record_map_value_typing_preamble(
        make_app=make_app,
        source_directory=tmp_path / "mixed",
        second_row_tier=1,
        option_lines="   :record-map-value-typing: wide\n",
    )

    assert uniform_preamble == (
        "use std::collections::HashMap;\n"
        "enum Value {\n"
        "    Str(&'static str),\n"
        "}\n"
        "struct Row {\n"
        "    name: &'static str,\n"
        "    attributes: HashMap<&'static str, Value>,\n"
        "}"
    )
    assert mixed_preamble == (
        "use std::collections::HashMap;\n"
        "enum Value {\n"
        "    Str(&'static str),\n"
        "    I32(i32),\n"
        "}\n"
        "struct Row {\n"
        "    name: &'static str,\n"
        "    attributes: HashMap<&'static str, Value>,\n"
        "}"
    )


def test_record_map_value_typing_rejected_for_unsupported_language(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A language without a ``RecordMapValueTypings`` enum (e.g. Python)
    surfaces a clean directive error rather than crashing on the
    constructor kwarg.
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
           :record-map-value-typing: wide
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
            "Language 'python' does not support record-map-value-typing "
            "'wide'."
        ),
    )
    app.cleanup()
