"""Insert structured callable descriptions into Jinja text blocks."""

from collections.abc import Mapping
from functools import partial

from beartype import beartype
from literalizer import describe_callable
from literalizer.exceptions import LiteralizerError
from sphinx.application import Sphinx
from sphinx.config import Config
from sphinx.errors import ConfigError

from ._support import _is_string_object_dict, _language_types


@beartype
def _describe(
    name: str, language: str, *, descriptions: Mapping[str, object]
) -> str:
    """Resolve one named description using the normal language keys."""
    if name not in descriptions:
        msg = f"Unknown callable description: {name!r}"
        raise ConfigError(msg)
    description = descriptions[name]
    if not _is_string_object_dict(description):
        msg = f"Callable description {name!r} must be a string-keyed mapping"
        raise ConfigError(msg)
    languages = _language_types()
    if language not in languages:
        msg = f"Unknown callable description language: {language!r}"
        raise ConfigError(msg)
    try:
        return describe_callable(
            language=languages[language](), description=description
        )
    except LiteralizerError as error:
        msg = f"Invalid callable description {name!r}: {error}"
        raise ConfigError(msg) from error


@beartype
def register_callable_filter(app: Sphinx, config: Config) -> None:
    """Register only when sphinx-jinja2 is enabled, in either order."""
    if "sphinx_jinja2" not in app.extensions:
        return
    descriptions: object = config.literalizer_callable_descriptions
    if not _is_string_object_dict(descriptions):
        msg = (
            "literalizer_callable_descriptions must be a string-keyed mapping"
        )
        raise ConfigError(msg)
    filters = dict(config.jinja2_filters)
    if "literalizer_callable" in filters:
        msg = "Jinja filter 'literalizer_callable' is already defined"
        raise ConfigError(msg)
    filters["literalizer_callable"] = partial(
        _describe, descriptions=descriptions
    )
    config.jinja2_filters = filters
