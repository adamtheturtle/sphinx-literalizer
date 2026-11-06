"""Insert callable descriptions from direct Jinja filter parameters."""

from collections.abc import Callable
from typing import Unpack

from beartype import beartype
from literalizer import describe_callable
from literalizer.exceptions import LiteralizerError
from sphinx.application import Sphinx
from sphinx.errors import ConfigError
from typing_extensions import TypedDict

from ._support import _language_types


class _CallableOptions(TypedDict, total=False, closed=True):
    """Presentation options and caller-owned naming policies."""

    selector: str
    return_annotation: str
    space_before_paren: bool
    space_after_paren: bool
    name_renamer: Callable[[str], str]
    parameter_renamer: Callable[[str], str]
    overrides: dict[str, dict[str, object]]


@beartype
def _describe(
    name: str,
    language: str,
    parameter_names: list[str],
    **options: Unpack[_CallableOptions],
) -> str:
    """Render an inline signature using caller-selected naming
    policies.
    """
    languages = _language_types()
    if language not in languages:
        msg = f"Unknown callable description language: {language!r}"
        raise ConfigError(msg)
    presentation = {
        key.replace("_", "-"): value
        for key, value in options.items()
        if key not in {"name_renamer", "parameter_renamer", "overrides"}
    }
    try:
        return describe_callable(
            language=languages[language](),
            description={
                "default": {
                    "name": name,
                    "parameter-names": parameter_names,
                    **presentation,
                },
                "languages": options.get("overrides", {}),
            },
            name_renamer=options.get("name_renamer"),
            parameter_renamer=options.get("parameter_renamer"),
        )
    except LiteralizerError as error:
        msg = f"Invalid callable description {name!r}: {error}"
        raise ConfigError(msg) from error


@beartype
def register_callable_filter(app: Sphinx) -> None:
    """Register only when sphinx-jinja2 is enabled, in either order."""
    if "sphinx_jinja2" not in app.extensions:
        return
    config = app.config
    filters = dict(config.jinja2_filters)
    if "literalizer_callable" in filters:
        msg = "Jinja filter 'literalizer_callable' is already defined"
        raise ConfigError(msg)
    filters["literalizer_callable"] = _describe
    config.jinja2_filters = filters
