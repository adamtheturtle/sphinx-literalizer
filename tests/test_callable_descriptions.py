"""Callable signatures are direct Jinja parameters in guide prose."""

from collections.abc import Callable
from pathlib import Path

import pytest
from sphinx.errors import ConfigError
from sphinx.testing.util import SphinxTestApp


def _build(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extensions: list[str],
    template: str,
) -> SphinxTestApp:
    """Render filter arguments through the real Jinja extension."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "index.rst").write_text(
        data="Methods\n=======\n\n.. jinja:: naming\n\n   .. code-block:: text\n\n      "
        + template
        + "\n",
        encoding="utf-8",
    )
    app = make_app(
        srcdir=source,
        confoverrides={
            "extensions": extensions,
            "jinja2_filters": {"existing": str.upper},
            "jinja2_contexts": {"naming": {"renamers": {"upper": str.upper}}},
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
def test_direct_parameters(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extensions: list[str],
) -> None:
    """Direct signatures preserve existing filters and extension order."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=extensions,
        template='{{ "hello" | existing }} '
        '{{ "accept" | literalizer_callable("python", ["value"], '
        'return_annotation="bool", space_before_paren=true, '
        "space_after_paren=true) }} "
        '{{ "accept" | literalizer_callable("objective-c", ["value"], '
        'selector="accept:") }}',
    )
    assert app.warning.getvalue() == ""
    assert (
        "HELLO accept ( value) -> bool accept:"
        in app.env.get_doctree(docname="index").astext()
    )


@pytest.mark.parametrize(
    argnames=("template", "message"),
    argvalues=[
        (
            '{{ "accept" | literalizer_callable("python", ["value"], typo=true) }}',
            "Invalid callable description",
        ),
        (
            '{{ "bad name" | literalizer_callable("python", ["value"]) }}',
            "Invalid callable description",
        ),
        (
            '{{ "accept" | literalizer_callable("unknown", ["value"]) }}',
            "Unknown callable description language",
        ),
        (
            (
                '{{ "accept" | literalizer_callable("python", ["value"], '
                'overrides={"unknown": {"selector": "accept:"}}) }}'
            ),
            "Unknown invocation languages",
        ),
    ],
)
def test_invalid_parameters(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    template: str,
    message: str,
) -> None:
    """Parameter errors surface as useful Jinja build warnings."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=["sphinx_literalizer", "sphinx_jinja2"],
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


@pytest.mark.parametrize(
    argnames=("language", "expected"),
    argvalues=[
        ("python", "ACCEPT_VALUE(ITEM_NAME)"),
        ("objective-c", "acceptURL:"),
    ],
)
def test_configured_renamers_and_overrides(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    language: str,
    expected: str,
) -> None:
    """Explicit native metadata takes precedence over naming callbacks."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        extensions=["sphinx_literalizer", "sphinx_jinja2"],
        template='{{ "accept_value" | literalizer_callable("'
        + language
        + '", ["item_name"], name_renamer=renamers["upper"], '
        'parameter_renamer=renamers["upper"], '
        'overrides={"objective-c": {"selector": "acceptURL:", '
        '"parameter-names": ["requestURL"]}}) }}',
    )
    assert app.warning.getvalue() == ""
    assert expected in app.env.get_doctree(docname="index").astext()
