"""Native directives tested against the actual copied program."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.native_invocation_support import (
    NATIVE_RECIPE,
    build_native_app,
    native_program,
)


def test_native_group_and_dependencies(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> None:
    """Typed constructors/messages compose without source transforms."""
    app = build_native_app(
        make_app=make_app, tmp_path=tmp_path, recipe=NATIVE_RECIPE
    )
    assert app.warning.getvalue() == ""
    program = native_program(app=app)
    assert program.count("#import <Foundation/Foundation.h>") == 1
    assert "NativeCounter *counter = [[NativeCounter alloc] init];" in program
    assert (
        'checkResult([counter accept:@"user_1" timestamp:100.0], @[' in program
    )
    assert (
        'checkResult([counter accept:@"user_2" timestamp:101.0], @[' in program
    )
    assert "kCounter" not in program
    dependencies = app.env.dependencies["guide/native"]
    for name in (
        "constructor.json",
        "no-args.json",
        "recipe.json",
        "calls.json",
        "expected.json",
    ):
        assert tmp_path / "source/guide" / name in dependencies
    app.cleanup()


@pytest.mark.parametrize(
    argnames="recipe",
    argvalues=[
        {"function": "bad;source"},
        {**NATIVE_RECIPE, "unknown-field": True},
        {**NATIVE_RECIPE, "parameter-types": []},
    ],
)
def test_native_errors_identify_document_and_data(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path, recipe: object
) -> None:
    """Author mistakes retain document and data-file locations."""
    app = build_native_app(make_app=make_app, tmp_path=tmp_path, recipe=recipe)
    warning = app.warning.getvalue()
    document = tmp_path / "source/guide/native.rst"
    assert f"{document}:" in warning
    assert "calls.json" in warning
    assert "Native" in warning or "native" in warning
    app.cleanup()


def _small_build(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    options: str,
    recipe_source: str | None,
) -> SphinxTestApp:
    """Build one directive to exercise located author diagnostics."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "calls.json").write_text(data="[[]]", encoding="utf-8")
    if recipe_source is not None:
        _ = (source / "recipe.json").write_text(
            data=recipe_source, encoding="utf-8"
        )
    _ = (source / "index.rst").write_text(
        data="Native\n======\n\n.. literalizer-invocation:: calls.json\n   :language: objective-c\n   :per-element:\n"
        + options,
        encoding="utf-8",
    )
    app = make_app(
        srcdir=source, confoverrides={"extensions": ["sphinx_literalizer"]}
    )
    app.build()
    return app


@pytest.mark.parametrize(
    argnames=("options", "recipe_source", "message"),
    argvalues=[
        ("", "{}", "invocation-file"),
        (
            "   :invocation-file: missing.json\n",
            None,
            "Cannot read native invocation dependency",
        ),
        ("   :invocation-file: recipe.json\n", "{", "recipe.json:1:2"),
        ("   :invocation-file: recipe.json\n", "[]", "must be a JSON object"),
        (
            "   :invocation-file: recipe.json\n   :existing-variable:\n",
            '{"constructor":"NSObject"}',
            "requires ':variable-name:'",
        ),
        (
            "   :invocation-file: recipe.json\n   :zip-input-format: json\n",
            '{"constructor":"NSObject"}',
            "requires ':zip-file:'",
        ),
    ],
)
def test_native_author_diagnostics(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    options: str,
    recipe_source: str | None,
    message: str,
) -> None:
    """Invalid options/files retain document and data-file locations."""
    app = _small_build(
        make_app=make_app,
        tmp_path=tmp_path,
        options=options,
        recipe_source=recipe_source,
    )
    warnings = app.warning.getvalue()
    assert "index.rst:" in warnings
    assert "calls.json" in warnings
    assert message in warnings
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("extra", "expected"),
    argvalues=[
        (
            "   :variable-name: object\n   :existing-variable:\n",
            "object = [[NSObject alloc] init];",
        ),
        ("   :preamble-only:\n", "#import <Foundation/Foundation.h>"),
    ],
)
def test_native_binding_and_preamble_views(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extra: str,
    expected: str,
) -> None:
    """Existing bindings and preamble-only views retain complete fragments."""
    app = _small_build(
        make_app=make_app,
        tmp_path=tmp_path,
        options="   :invocation-file: recipe.json\n" + extra,
        recipe_source='{"constructor":"NSObject"}',
    )
    assert app.warning.getvalue() == ""
    blocks = list(
        app.env.get_doctree(docname="index").findall(
            condition=nodes.literal_block
        )
    )
    assert [block.astext() for block in blocks] == [expected]
    app.cleanup()


def test_native_unrepresentable_literal_can_be_skipped(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The shared skip policy applies to native literal conversion
    errors.
    """
    recipe = {
        "function": "consume",
        "parameter-types": ["NSNumber"],
        "return-type": "void",
        "arguments": [{"literal": 1 << 200}],
    }
    app = _small_build(
        make_app=make_app,
        tmp_path=tmp_path,
        options="   :invocation-file: recipe.json\n   :skip-if-unrepresentable:\n",
        recipe_source=json.dumps(obj=recipe),
    )
    assert app.warning.getvalue() == ""
    blocks = app.env.get_doctree(docname="index").findall(
        condition=nodes.literal_block
    )
    assert next(blocks, None) is None
    app.cleanup()
