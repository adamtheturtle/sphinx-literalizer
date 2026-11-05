"""Jinja descriptions share Literalizer metadata without syntax
branches.
"""

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


def _build(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extensions: list[str],
    extra: dict[str, object],
    template: str,
) -> SphinxTestApp:
    """Build a text block using the real sphinx-jinja2 extension."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "index.rst").write_text(
        data="Reference\n=========\n\n.. jinja::\n\n   .. code-block:: text\n\n      "
        + template
        + "\n",
        encoding="utf-8",
    )
    app = make_app(
        srcdir=source,
        confoverrides={
            "extensions": extensions,
            "literalizer_callable_descriptions": _RECIPE,
            "jinja2_filters": {"existing": str.upper},
            "suppress_warnings": ["config.cache"],
            **extra,
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
def test_jinja_filter(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extensions: list[str],
) -> None:
    """Both extension orders preserve existing filters and exact text."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=extensions,
        extra={},
        template='{{ "hello" | existing }} {{ "accept" | literalizer_callable("python") }} {{ "accept" | literalizer_callable("objective-c") }}',
    )
    assert app.warning.getvalue() == ""
    assert (
        "HELLO accept(value) accept:"
        in app.env.get_doctree(docname="index").astext()
    )


@pytest.mark.parametrize(
    argnames=("extra", "template", "message"),
    argvalues=[
        (
            {},
            '{{ "missing" | literalizer_callable("python") }}',
            "Unknown callable description",
        ),
        ({}, '{{ "accept" | literalizer_callable("unknown") }}', "language"),
        (
            {"literalizer_callable_descriptions": {"accept": "bad"}},
            '{{ "accept" | literalizer_callable("python") }}',
            "mapping",
        ),
        (
            {
                "literalizer_callable_descriptions": {
                    "accept": {"name": "accept"}
                }
            },
            '{{ "accept" | literalizer_callable("python") }}',
            "Invalid callable description",
        ),
        (
            {"literalizer_callable_descriptions": {1: "bad"}},
            "Hello",
            "string-keyed mapping",
        ),
        (
            {"jinja2_filters": {"literalizer_callable": str.upper}},
            "Hello",
            "already defined",
        ),
    ],
)
def test_invalid_configuration(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extra: dict[str, object],
    template: str,
    message: str,
) -> None:
    """Configuration errors identify the description or conflicting filter."""
    if template == "Hello":
        with pytest.raises(expected_exception=ConfigError, match=message):
            _ = _build(
                make_app=make_app,
                tmp_path=tmp_path,
                extensions=["sphinx_literalizer", "sphinx_jinja2"],
                extra=extra,
                template=template,
            )
    else:
        app = _build(
            make_app=make_app,
            tmp_path=tmp_path,
            extensions=["sphinx_literalizer", "sphinx_jinja2"],
            extra=extra,
            template=template,
        )
        assert message in app.warning.getvalue()
