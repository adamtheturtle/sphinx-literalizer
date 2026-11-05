"""One directive renders shared recipes for generic and native
backends.
"""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

_RECIPE: dict[str, object] = {
    "default": {
        "target-function": "counter.accept",
        "parameter-names": ["user", "timestamp"],
        "result-function": "checkResult",
    },
    "languages": {
        "python": {"result-function": "check_result"},
        "objective-c": {
            "native": {
                "function": "checkResult",
                "parameter-types": ["bool", "NSArray"],
                "return-type": "void",
                "arguments": [
                    {
                        "receiver": {
                            "reference": "counter",
                            "type": "Counter",
                        },
                        "selector": "accept:timestamp:",
                        "parameter-types": ["NSString", "float"],
                        "return-type": "bool",
                        "arguments": [{"input": 0}, {"input": 1}],
                    },
                    {"zipped": True},
                ],
            },
        },
    },
}


def _build_shared(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    recipe: dict[str, object],
    extra: str,
) -> SphinxTestApp:
    """Build identical invocation directives for three real backends."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "calls.json").write_text(
        data='[["user_1",100.0]]', encoding="utf-8"
    )
    _ = (source / "expected.json").write_text(
        data='[[true,"first"]]', encoding="utf-8"
    )
    _ = (source / "recipe.json").write_text(
        data=json.dumps(obj=recipe), encoding="utf-8"
    )
    directives = [
        f".. literalizer-invocation:: calls.json\n"
        f"   :language: {language}\n"
        "   :invocation-file: recipe.json\n"
        "   :zip-file: expected.json\n"
        "   :per-element:\n" + extra
        for language in ("python", "javascript", "objective-c")
    ]
    _ = (source / "index.rst").write_text(
        data="Shared\n======\n\n" + "\n\n".join(directives),
        encoding="utf-8",
    )
    app = make_app(
        srcdir=source,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    return app


def _blocks(app: SphinxTestApp, /) -> list[str]:
    """Read the exact rendered fragments exposed to consumers."""
    return [
        node.astext()
        for node in app.env.get_doctree(docname="index").findall(
            condition=nodes.literal_block
        )
    ]


def test_shared_recipe_and_incremental_dependency(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> None:
    """One file controls spelling, native dispatch, and subsequent
    rebuilds.
    """
    app = _build_shared(
        make_app=make_app, tmp_path=tmp_path, recipe=_RECIPE, extra=""
    )
    assert app.warning.getvalue() == ""
    blocks = _blocks(app)
    assert (
        'check_result(counter.accept(user="user_1", timestamp=100.0),'
        in blocks[0]
    )
    assert (
        'checkResult(counter.accept({ user: "user_1", timestamp: 100.0 }),'
        in blocks[1]
    )
    assert (
        'checkResult([counter accept:@"user_1" timestamp:100.0],' in blocks[2]
    )
    recipe_path = tmp_path / "source/recipe.json"
    for name in ("calls.json", "expected.json", "recipe.json"):
        assert tmp_path / "source" / name in app.env.dependencies["index"]
    _ = recipe_path.write_text(
        data=json.dumps(obj=_RECIPE).replace("check_result", "verify_result"),
        encoding="utf-8",
    )
    app.env.all_docs["index"] = 0
    app.build()
    assert "verify_result(" in _blocks(app)[0]
    assert "check_result(" not in _blocks(app)[0]
    assert app.warning.getvalue() == ""
    app.cleanup()


@pytest.mark.parametrize(
    argnames="recipe",
    argvalues=[
        {"default": {}, "languages": {"pyhton": {}}},
        {"default": {"parameter-names": [], "target-functon": "consume"}},
    ],
)
def test_shared_recipe_diagnostics(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    recipe: dict[str, object],
) -> None:
    """Upstream recipe errors retain the Sphinx document and data location."""
    app = _build_shared(
        make_app=make_app, tmp_path=tmp_path, recipe=recipe, extra=""
    )
    warning = app.warning.getvalue()
    assert "index.rst:" in warning
    assert "calls.json" in warning
    assert "invocation" in warning or "native fields" in warning
    app.cleanup()
