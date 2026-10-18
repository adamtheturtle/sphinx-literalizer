"""Nested call-input selection through Literalizer's public API."""

from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from literalizer.exceptions import (
    InputRootKeyNotFoundError,
    InputRootNotMappingError,
)
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


@pytest.mark.parametrize(
    argnames=("extension", "source"),
    argvalues=[
        ("json", '{"calls": [["Ada"], ["Grace"]]}'),
        ("json5", "{calls: [['Ada'], ['Grace']]}"),
        ("yaml", "calls:\n  - [Ada]\n  - [Grace]\n"),
        ("toml", 'calls = [["Ada"], ["Grace"]]'),
    ],
)
def test_nested_call_rows(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    extension: str,
    source: str,
) -> None:
    """Call rows can be selected without discarding parse metadata."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / f"data.{extension}").write_text(data=source)
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text=f"""\
        Test
        ====

        .. literalizer-call:: data.{extension}
           :language: python
           :target-function: welcome
           :parameter-names: name
           :per-element:
           :input-root-key: calls
        """
        )
    )
    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    assert app.warning.getvalue() == ""
    doctree = app.env.get_doctree(docname="index")
    (block,) = doctree.findall(condition=nodes.literal_block)
    assert block.astext() == 'welcome(name="Ada")\nwelcome(name="Grace")'
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("source", "message"),
    argvalues=[
        (
            '{"other": []}',
            str(object=InputRootKeyNotFoundError(input_root_key="calls")),
        ),
        (
            "[]",
            str(
                object=InputRootNotMappingError(
                    input_root_key="calls", root_type=list
                )
            ),
        ),
    ],
)
def test_invalid_input_root_is_a_directive_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    """Selection failures identify the directive and its data file."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(data=source)
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: welcome
           :parameter-names: name
           :per-element:
           :input-root-key: calls
        """
        )
    )
    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=message,
    )
    app.cleanup()
