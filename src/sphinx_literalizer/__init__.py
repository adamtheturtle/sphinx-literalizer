"""Sphinx extension for literalizer."""

from sphinx.application import Sphinx


def setup(app: Sphinx) -> dict:
    """Register the extension with Sphinx."""
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
