"""Check how malformed inputs are rejected at extension boundaries."""

import pytest
from sphinx.config import Config
from sphinx.errors import ExtensionError

from sphinx_literalizer._support import (
    _DirectiveError,
    config_mapping,
    config_registrar,
    typed_option,
)


def test_config_requires_string_keyed_mapping() -> None:
    """Reject a non-mapping language defaults setting."""
    config = Config()
    setting = "literalizer_language_defaults"
    setattr(config, setting, [])
    with pytest.raises(
        expected_exception=ExtensionError, match="must be a dictionary"
    ):
        _ = config_mapping(config=config, name=setting)


def test_config_registrar_requires_setup_interface() -> None:
    """Reject an application without Sphinx's registration method."""
    with pytest.raises(
        expected_exception=TypeError, match="register Sphinx settings"
    ):
        _ = config_registrar(object())


def test_converted_option_requires_declared_type() -> None:
    """Reject a converter result with the wrong type."""
    with pytest.raises(
        expected_exception=_DirectiveError, match="Expected a str option"
    ):
        _ = typed_option(42, expected_type=str)
