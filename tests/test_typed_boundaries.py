"""Check how malformed inputs are rejected at extension boundaries."""

from collections.abc import Callable
from pathlib import Path
from textwrap import dedent
from typing import ClassVar

import pytest
from docutils.parsers.rst import directives
from sphinx.config import Config
from sphinx.errors import ExtensionError
from sphinx.testing.util import SphinxTestApp

from sphinx_literalizer import LiteralizerDirective
from sphinx_literalizer._support import config_mapping, config_registrar
from tests.test_helpers import assert_directive_error


def test_config_requires_string_keyed_mapping() -> None:
    """Reject a non-mapping language defaults setting."""
    config = Config()
    setting = "literalizer_language_defaults"
    config.literalizer_language_defaults = []
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


def test_converted_option_requires_declared_type(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> None:
    """Reject a converter result with the wrong type during a build."""
    registered_options = LiteralizerDirective.option_spec
    assert registered_options is not None
    base_options = dict(registered_options)

    class TextIndentDirective(LiteralizerDirective):
        """A directive with an incompatible indent converter."""

        option_spec: ClassVar[dict[str, Callable[[str], object]] | None] = {
            **base_options,
            "indent": directives.unchanged,
        }

    (tmp_path / "conf.py").touch()
    _ = (tmp_path / "data.json").write_text(data="1", encoding="utf-8")
    _ = (tmp_path / "index.rst").write_text(
        data=dedent(
            text="""\
            .. literalizer:: data.json
               :language: python
               :indent: two
            """
        ),
        encoding="utf-8",
    )
    app = make_app(
        srcdir=tmp_path, confoverrides={"extensions": ["sphinx_literalizer"]}
    )
    app.add_directive(
        name="literalizer", cls=TextIndentDirective, override=True
    )
    assert_directive_error(
        app=app,
        source_directory=tmp_path,
        line=1,
        message="Expected an option of type int",
    )
