"""Sphinx extension for literalizer.

Provides the ``literalizer`` and ``literalizer-call`` directives, which
read data files and render them as native language code blocks.
"""

from importlib.metadata import version

from beartype import beartype
from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

from ._directives import (
    LiteralizerCallDirective as LiteralizerCallDirective,
)
from ._directives import LiteralizerDirective as LiteralizerDirective
from ._support import _DEFAULT_HETEROGENEOUS_STRATEGY_PRECEDENCE


@beartype
def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the extension with Sphinx."""
    app.add_directive(name="literalizer", cls=LiteralizerDirective)
    app.add_directive(
        name="literalizer-call",
        cls=LiteralizerCallDirective,
    )
    app.add_config_value(
        name="literalizer_heterogeneous_strategy_precedence",
        default=list(_DEFAULT_HETEROGENEOUS_STRATEGY_PRECEDENCE),
        rebuild="env",
        types=frozenset({list, tuple}),
    )
    app.add_config_value(
        name="literalizer_language_defaults",
        default={},
        rebuild="env",
        types=frozenset({dict}),
    )
    return {
        "version": version(distribution_name="sphinx-literalizer"),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
