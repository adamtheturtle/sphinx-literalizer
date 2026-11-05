"""A real composed document rendered without external process access."""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

import pytest
from sphinx.testing.util import SphinxTestApp

from tests.native_invocation_support import NATIVE_RECIPE


def build_canonical_app(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> SphinxTestApp:
    """Compose all three directive families in their actual caller
    scope.
    """
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "prefix.m").write_text(
        data="    id entries = @[\n", encoding="utf-8"
    )
    files: dict[str, object] = {
        "data.json": [{"name": "Ada", "count": 42}],
        "scalar.json": [42],
        "constructor.json": {"constructor": "NativeCounter"},
        "no-args.json": [[]],
        "recipe.json": NATIVE_RECIPE,
        "calls.json": [["user_1", 100.0], ["user_2", 101.0]],
        "expected.json": [[True, "first"], [False, "second"]],
    }
    for name, value in files.items():
        _ = (source / name).write_text(
            data=json.dumps(obj=value), encoding="utf-8"
        )
    _ = (source / "index.rst").write_text(
        data=(Path(__file__).parent / "fixtures/canonical.rst").read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    app = make_app(
        srcdir=source,
        confoverrides={
            "extensions": ["sphinx_literalizer", "sphinx_combine"],
            "literalizer_language_defaults": {
                "objective-c": {"source-format": "canonical", "indent": "2"}
            },
        },
    )
    unavailable = Mock(side_effect=AssertionError("Formatter process access"))
    with monkeypatch.context() as blocked:
        blocked.setenv(name="PATH", value="")
        blocked.setattr(target=subprocess, name="Popen", value=unavailable)
        app.build()
    unavailable.assert_not_called()
    return app
