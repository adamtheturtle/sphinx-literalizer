"""Validation of converted directive option shapes."""

# This module exercises the private option-validation boundary directly.
# pylint: disable=protected-access,wrong-spelling-in-comment
# ruff: noqa: SLF001

import pytest
from sphinx.errors import ExtensionError

import sphinx_literalizer._support as support
from sphinx_literalizer._directives import (
    LiteralizerCallDirective,
    LiteralizerDirective,
)


def test_raw_option_shapes_match_option_specs() -> None:
    """The static keys stay aligned with Docutils option converters."""
    literalizer_spec = LiteralizerDirective.option_spec
    assert literalizer_spec is not None
    assert set(support._RawLiteralizerOptions.__annotations__) == set(
        literalizer_spec
    )
    call_spec = LiteralizerCallDirective.option_spec
    assert call_spec is not None
    assert set(support._RawLiteralizerCallOptions.__annotations__) == set(
        call_spec
    )


@pytest.mark.parametrize(
    argnames="value",
    argvalues=[
        None,
        {"language": 1},
        {"language": "python", "ref-key": 1},
        {"language": "python", "indent": "2"},
        {"language": "python", "include-preamble": True},
    ],
)
def test_invalid_raw_common_options(value: object) -> None:
    """A present common field must have its converted value type."""
    assert not support._is_raw_common_options(value)


def test_invalid_merged_options() -> None:
    """Merged options are checked before being exposed as a TypedDict."""
    with pytest.raises(
        expected_exception=ExtensionError,
        match="Invalid merged directive options",
    ):
        _ = support._validated_raw_common_options(value={"language": 1})


def test_invalid_dynamic_string_option() -> None:
    """A dynamic format option must carry a converted string value."""
    with pytest.raises(
        expected_exception=TypeError,
        match="Directive option 'date-format' must be a string",
    ):
        _ = support._raw_string_option(
            options={"date-format": 1}, name="date-format"
        )
