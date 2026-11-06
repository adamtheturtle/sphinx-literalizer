"""Jinja descriptions keep question metadata in dependency-tracked
files.
"""

import json
import os
from collections.abc import Callable
from pathlib import Path

import pytest
from sphinx.errors import ConfigError
from sphinx.testing.util import SphinxTestApp

_RECIPE: dict[str, object] = {
    "accept": {
        "default": {"name": "accept", "parameter-names": ["value"]},
        "languages": {"objective-c": {"selector": "accept:"}},
    },
}
_TEMPLATE = '{{ "recipes.json" | literalizer_callable("accept", "python") }}'


def _build(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extensions: list[str],
    content: bytes | None,
    template: str,
) -> SphinxTestApp:
    """Build a nested document using the real sphinx-jinja2 extension."""
    source = tmp_path / "source"
    nested = source / "nested"
    nested.mkdir(parents=True)
    (source / "conf.py").touch()
    _ = (source / "index.rst").write_text(
        data="Reference\n=========\n\n.. toctree::\n\n   nested/page\n",
        encoding="utf-8",
    )
    _ = (nested / "page.rst").write_text(
        data="Methods\n=======\n\n.. jinja::\n\n   .. code-block:: text\n\n      "
        + template
        + "\n",
        encoding="utf-8",
    )
    if content is not None:
        _ = (nested / "recipes.json").write_bytes(data=content)
    app = make_app(
        srcdir=source,
        confoverrides={
            "extensions": extensions,
            "jinja2_filters": {"existing": str.upper},
            "suppress_warnings": ["config.cache"],
        },
    )
    app.build()
    return app


@pytest.mark.parametrize(
    argnames="extensions",
    argvalues=[
        ["sphinx_literalizer", "sphinx_jinja2"],
        ["sphinx_jinja2", "sphinx_literalizer"],
    ],
)
def test_jinja_filter_and_incremental_dependency(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extensions: list[str],
) -> None:
    """File changes rebuild nested documents without config or prose edits."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=extensions,
        content=json.dumps(obj=_RECIPE).encode(encoding="utf-8"),
        template='{{ "hello" | existing }} '
        + _TEMPLATE
        + ' {{ "recipes.json" | literalizer_callable("accept", "objective-c") }}',
    )
    assert app.warning.getvalue() == ""
    assert (
        "HELLO accept(value) accept:"
        in app.env.get_doctree(docname="nested/page").astext()
    )
    assert any(
        Path(str(object=dependency)).as_posix().endswith("nested/recipes.json")
        for dependency in app.env.dependencies["nested/page"]
    )
    path = tmp_path / "source/nested/recipes.json"
    _ = path.write_text(
        data=json.dumps(
            obj={"accept": {"name": "take", "parameter-names": ["value"]}}
        ),
        encoding="utf-8",
    )
    timestamp = app.env.all_docs["nested/page"] + 2
    os.utime(path=path, times=(timestamp, timestamp))
    app.build()
    assert (
        "HELLO take(value) take(value)"
        in app.env.get_doctree(docname="nested/page").astext()
    )
    assert app.warning.getvalue() == ""


@pytest.mark.parametrize(
    argnames=("content", "template", "message"),
    argvalues=[
        (None, _TEMPLATE, "Cannot read callable descriptions"),
        (b"\xff", _TEMPLATE, "Cannot read callable descriptions"),
        (b"{", _TEMPLATE, "Cannot read callable descriptions"),
        (b"[]", _TEMPLATE, "string-keyed mapping"),
        (b"{}", _TEMPLATE, "Unknown callable description"),
        (b'{"accept":"bad"}', _TEMPLATE, "string-keyed mapping"),
        (
            b'{"accept":{"name":"accept"}}',
            _TEMPLATE,
            "Invalid callable description",
        ),
        (
            json.dumps(obj=_RECIPE).encode(encoding="utf-8"),
            '{{ "recipes.json" | literalizer_callable("accept", "unknown") }}',
            "language",
        ),
    ],
)
def test_invalid_metadata(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    content: bytes | None,
    template: str,
    message: str,
) -> None:
    """Read and schema errors identify the file or description."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=["sphinx_literalizer", "sphinx_jinja2"],
        content=content,
        template=template,
    )
    assert message in app.warning.getvalue()


def test_filter_collision(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An existing filter is never silently replaced."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    with pytest.raises(
        expected_exception=ConfigError, match="already defined"
    ):
        _ = make_app(
            srcdir=source,
            confoverrides={
                "extensions": ["sphinx_literalizer", "sphinx_jinja2"],
                "jinja2_filters": {"literalizer_callable": str.upper},
            },
        )
