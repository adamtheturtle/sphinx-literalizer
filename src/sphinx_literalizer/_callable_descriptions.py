"""Insert file-backed callable descriptions into Jinja text blocks."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from beartype import beartype
from literalizer import describe_callable
from literalizer.exceptions import LiteralizerError
from sphinx.application import Sphinx
from sphinx.environment import BuildEnvironment
from sphinx.errors import ConfigError

from ._support import _is_string_object_dict, _language_types


@beartype
def _load_description(
    source_file: str, name: str, env: BuildEnvironment
) -> dict[str, object]:
    """Read question metadata relative to the current document."""
    _, absolute = env.relfn2path(filename=source_file)
    env.note_dependency(filename=absolute)
    try:
        descriptions: object = json.loads(
            s=Path(absolute).read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as error:
        msg = f"Cannot read callable descriptions {source_file!r}: {error}"
        raise ConfigError(msg) from error
    if not _is_string_object_dict(descriptions):
        msg = (
            f"Callable descriptions {source_file!r} "
            "must be a string-keyed mapping"
        )
        raise ConfigError(msg)
    if name not in descriptions:
        msg = f"Unknown callable description {name!r} in {source_file!r}"
        raise ConfigError(msg)
    description = descriptions[name]
    if not _is_string_object_dict(description):
        msg = (
            f"Callable description {name!r} in {source_file!r} "
            "must be a string-keyed mapping"
        )
        raise ConfigError(msg)
    return description


@dataclass
class _CallableDescriptionFilter:
    """Retain the build environment without capturing the application."""

    env: BuildEnvironment

    @beartype
    def __call__(
        self,
        source_file: str,
        name: str,
        language: str,
        *,
        name_renamer: Callable[[str], str] | None,
        parameter_renamer: Callable[[str], str] | None,
    ) -> str:
        """Apply caller-owned naming conventions to file-backed
        metadata.
        """
        description = _load_description(
            source_file=source_file, name=name, env=self.env
        )
        languages = _language_types()
        if language not in languages:
            msg = f"Unknown callable description language: {language!r}"
            raise ConfigError(msg)
        try:
            return describe_callable(
                language=languages[language](),
                description=description,
                name_renamer=name_renamer,
                parameter_renamer=parameter_renamer,
            )
        except LiteralizerError as error:
            msg = (
                f"Invalid callable description {name!r} "
                f"in {source_file!r}: {error}"
            )
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
    filters["literalizer_callable"] = partial(
        _CallableDescriptionFilter(env=app.env),
        name_renamer=None,
        parameter_renamer=None,
    )
    config.jinja2_filters = filters
