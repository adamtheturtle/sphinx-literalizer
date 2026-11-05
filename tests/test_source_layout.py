"""Canonical placement survives real Sphinx composition using Python
only.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.canonical_source_support import build_canonical_app

_PROFILE = Path(__file__).parents[1] / "integration/objective-c.clang-format"


def test_composed_source_needs_no_formatter(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Check the untouched composed program, including native receiver
    state.
    """
    app = build_canonical_app(
        make_app=make_app, tmp_path=tmp_path, monkeypatch=monkeypatch
    )
    assert app.warning.getvalue() == ""
    (block,) = app.env.get_doctree(docname="index").findall(
        condition=nodes.literal_block
    )
    code = block.astext() + "\n"
    assert code.count("#import <Foundation/Foundation.h>") == 1
    assert "    consumeObject(@42);" in code
    assert "    NativeCounter *counter" in code
    assert '        @"name" : @"Ada",' in code
    formatted = subprocess.run(  # noqa: S603
        args=[  # noqa: S607
            "clang-format",
            f"--style=file:{_PROFILE}",
            "--assume-filename=example.m",
        ],
        input=code,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert formatted.stdout == code
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("language", "options", "message"),
    argvalues=[
        ("python", "   :source-format: canonical\n", "source-format"),
        ("objective-c", "   :initial-column: 10\n", "requires canonical"),
        (
            "objective-c",
            "   :source-format: canonical\n   :indent-char: tabs\n",
            "made of spaces",
        ),
    ],
)
def test_source_layout_diagnostics(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    language: str,
    options: str,
    message: str,
) -> None:
    """Unsupported placement keeps the source document and input
    location.
    """
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "data.json").write_text(data="[1, 2]", encoding="utf-8")
    _ = (source / "index.rst").write_text(
        data="Layout\n======\n\n.. literalizer:: data.json\n"
        f"   :language: {language}\n" + options,
        encoding="utf-8",
    )
    app = make_app(
        srcdir=source, confoverrides={"extensions": ["sphinx_literalizer"]}
    )
    app.build()
    warning = app.warning.getvalue()
    assert "index.rst:4" in warning
    assert "data.json" in warning
    assert message in warning
    app.cleanup()


def test_profile_defaults_rebuild_and_explicit_override(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> None:
    """Configuration changes invalidate cached documents and respect
    overrides.
    """
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "data.json").write_text(
        data='["first", "second"]', encoding="utf-8"
    )
    _ = (source / "index.rst").write_text(
        data="Layout\n======\n\n"
        ".. literalizer:: data.json\n   :language: objective-c\n   :include-delimiters:\n\n"
        ".. literalizer:: data.json\n   :language: objective-c\n   :include-delimiters:\n"
        "   :source-format: preserve\n   :indent: 2\n",
        encoding="utf-8",
    )
    observed: list[str] = []
    legacy: list[str] = []
    for indent in ("2", "4"):
        app = make_app(
            srcdir=source,
            freshenv=False,
            confoverrides={
                "extensions": ["sphinx_literalizer"],
                "literalizer_language_defaults": {
                    "objective-c": {
                        "source-format": "canonical",
                        "indent": indent,
                    }
                },
            },
        )
        app.build()
        assert app.warning.getvalue() == ""
        canonical, preserved = app.env.get_doctree(docname="index").findall(
            condition=nodes.literal_block
        )
        observed.append(canonical.astext())
        legacy.append(preserved.astext())
        app.cleanup()
    assert observed[0] != observed[1]
    assert '  @"first",' in observed[0]
    assert '    @"first",' in observed[1]
    assert legacy[0] == legacy[1]
