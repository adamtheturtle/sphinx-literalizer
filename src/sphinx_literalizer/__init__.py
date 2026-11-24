"""Sphinx extension for literalizer.

Provides literal, call, and native invocation directives, which read data
files and render combined native language code blocks.
"""

from importlib.metadata import version

from beartype import beartype
from sphinx.application import Sphinx
from sphinx.util.typing import ExtensionMetadata

from ._callable_descriptions import register_callable_filter
from ._directives import LiteralizerCallDirective, LiteralizerDirective
from ._group import LiteralizerGroupDirective
from ._native import LiteralizerInvocationDirective
from ._support import (
    _DEFAULT_HETEROGENEOUS_STRATEGY_PRECEDENCE,
    config_registrar,
)

__all__ = (
    "LiteralizerCallDirective",
    "LiteralizerDirective",
    "LiteralizerGroupDirective",
    "LiteralizerInvocationDirective",
    "setup",
)


@beartype
def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the extension with Sphinx."""
    _ = app.connect(event="builder-inited", callback=register_callable_filter)
    app.add_directive(name="literalizer", cls=LiteralizerDirective)
    app.add_directive(
        name="literalizer-invocation", cls=LiteralizerInvocationDirective
    )
    app.add_directive(name="literalizer-group", cls=LiteralizerGroupDirective)
    app.add_directive(
        name="literalizer-call",
        cls=LiteralizerCallDirective,
    )
    registrar = config_registrar(app)
    registrar.add_config_value(
        "literalizer_heterogeneous_strategy_precedence",
        list(_DEFAULT_HETEROGENEOUS_STRATEGY_PRECEDENCE),
        "env",
        frozenset[type[object]]({list, tuple}),
    )
    registrar.add_config_value(
        "literalizer_language_defaults",
        {},
        "env",
        frozenset[type[object]]({dict}),
    )
    return {
        "version": version(distribution_name="sphinx-literalizer"),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
