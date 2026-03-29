"""Sphinx extension for literalizer.

Provides the ``literalizer`` directive, which reads a JSON file and
renders it as a native language literal block.
"""

import enum
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cache, partial
from pathlib import Path
from typing import Any, ClassVar

from beartype import beartype
from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import Language, LanguageCls, literalize_yaml
from literalizer.languages import ALL_LANGUAGES
from sphinx.application import Sphinx
from sphinx.errors import ExtensionError
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata


def _language_key(lang_cls: LanguageCls) -> str:
    """Derive the directive key for a language class."""
    if lang_cls.pygments_name == "text":
        return lang_cls.__name__.lower()
    return lang_cls.pygments_name


@cache
def _language_types() -> dict[str, LanguageCls]:
    """Map directive language keys to their language classes."""
    return {
        _language_key(lang_cls=lang_cls): lang_cls
        for lang_cls in ALL_LANGUAGES
    }


# Map from directive option name to a typed lambda getter for the enum class.
_FORMAT_OPTION_GETTERS: dict[
    str,
    Callable[[LanguageCls], Iterable[enum.Enum]],
] = {
    "date-format": lambda cls: cls.DateFormats,
    "datetime-format": lambda cls: cls.DatetimeFormats,
    "sequence-format": lambda cls: cls.SequenceFormats,
    "set-format": lambda cls: cls.SetFormats,
    "bytes-format": lambda cls: cls.BytesFormats,
    "comment-format": lambda cls: cls.CommentFormats,
    "variable-type-hints": lambda cls: cls.VariableTypeHints,
    "declaration-style": lambda cls: cls.DeclarationStyles,
    "dict-format": lambda cls: cls.DictFormats,
    "integer-format": lambda cls: cls.IntegerFormats,
    "numeric-separator": lambda cls: cls.NumericSeparators,
    "string-format": lambda cls: cls.StringFormats,
    "trailing-comma": lambda cls: cls.TrailingCommas,
    "line-ending": lambda cls: cls.LineEndings,
    "empty-dict-key": lambda cls: cls.EmptyDictKey,
}


@cache
def _all_formats() -> dict[str, dict[tuple[str, str], object]]:
    """Build format lookup dicts for all format options."""
    return {
        option_name: {
            (lang_name, member.name.lower()): member
            for lang_name, lang_cls in _language_types().items()
            for member in getter(lang_cls)
        }
        for option_name, getter in _FORMAT_OPTION_GETTERS.items()
    }


@cache
def _all_format_values() -> dict[str, tuple[str, ...]]:
    """Build sorted unique value tuples for all format options."""
    return {
        option_name: tuple(sorted({v for _, v in formats}))
        for option_name, formats in _all_formats().items()
    }


@beartype
def _lookup_format(
    language_name: str,
    directive_name: str,
    format_value: str,
    formats: dict[tuple[str, str], object],
) -> object:
    """Look up a format enum member by language and value."""
    try:
        return formats[(language_name, format_value)]
    except KeyError:
        msg = (
            f"Language '{language_name}' does not support "
            f"{directive_name} '{format_value}'."
        )
        raise ExtensionError(message=msg) from None


def _make_format_validator(
    option_name: str,
) -> Callable[[str], str]:
    """Create a directive choice validator for a format option."""

    def validator(x: str) -> str:
        """Validate that *x* is a known value for this format option."""
        return directives.choice(
            argument=x,
            values=_all_format_values()[option_name],
        )

    return validator


def _format_option_specs() -> dict[str, Callable[[str], str]]:
    """Build option_spec entries for all format options."""
    return {
        option_name: _make_format_validator(option_name=option_name)
        for option_name in _FORMAT_OPTION_GETTERS
    }


@dataclass(frozen=True)
class _RenderingOptions:
    """Rendering options derived from directive flags."""

    pre_indent_level: int
    include_delimiters: bool
    variable_name: str | None
    existing_variable: bool


@beartype
class LiteralizerDirective(SphinxDirective):
    """Directive that converts a JSON file to a native literal block.

    Usage::

        .. literalizer:: path/to/data.json
           :language: python
           :pre-indent-level: 2
           :indent: 4
           :indent-char: spaces
           :include-delimiters:
           :date-format: python
           :datetime-format: python
           :variable-name: my_var
           :existing-variable:
           :sequence-format: list
           :set-format: frozenset
           :bytes-format: python
           :comment-format: block
           :variable-type-hints: always
           :declaration-style: const
           :dict-format: object
           :integer-format: decimal
           :numeric-separator: none
           :string-format: double
           :trailing-comma: yes
           :line-ending: semicolon
           :empty-dict-key: positional
           :default-set-element-type: String
           :default-sequence-element-type: String
           :default-dict-key-type: String
           :default-dict-value-type: String
    """

    required_arguments = 1
    has_content = False
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        "language": lambda x: directives.choice(
            argument=x,
            values=tuple(_language_types()),
        ),
        "pre-indent-level": directives.nonnegative_int,
        "indent": directives.nonnegative_int,
        "indent-char": lambda x: directives.choice(
            argument=x,
            values=("spaces", "tabs"),
        ),
        "include-delimiters": directives.flag,
        **_format_option_specs(),
        "variable-name": directives.unchanged,
        "existing-variable": directives.flag,
        "default-set-element-type": directives.unchanged,
        "default-sequence-element-type": directives.unchanged,
        "default-dict-key-type": directives.unchanged,
        "default-dict-value-type": directives.unchanged,
    }

    def _apply_format_options(
        self,
        language_name: str,
        constructor: partial[Language],
    ) -> partial[Language]:
        """Apply all format/enum options."""
        all_formats = _all_formats()
        for option_name in _FORMAT_OPTION_GETTERS:
            value = self.options.get(option_name)
            if value is not None:
                param_name = option_name.replace("-", "_")
                constructor = partial(
                    constructor,
                    **{
                        param_name: _lookup_format(
                            language_name=language_name,
                            directive_name=option_name,
                            format_value=value,
                            formats=all_formats[option_name],
                        ),
                    },
                )
        return constructor

    def _apply_default_type_options(
        self,
        language_name: str,
        constructor: partial[Language],
    ) -> partial[Language]:
        """Apply default element/key/value type options."""
        type_option_map: dict[
            str,
            tuple[str, Callable[[LanguageCls], bool]],
        ] = {
            "default-set-element-type": (
                "default_set_element_type",
                lambda cls: cls.supports_default_set_element_type,
            ),
            "default-sequence-element-type": (
                "default_sequence_element_type",
                lambda cls: cls.supports_default_sequence_element_type,
            ),
            "default-dict-key-type": (
                "default_dict_key_type",
                lambda cls: cls.supports_default_dict_key_type,
            ),
            "default-dict-value-type": (
                "default_dict_value_type",
                lambda cls: cls.supports_default_dict_value_type,
            ),
        }
        language_cls = _language_types()[language_name]
        for option_name, (
            param_name,
            supports_check,
        ) in type_option_map.items():
            value = self.options.get(option_name)
            if value is not None:
                if not supports_check(language_cls):
                    msg = (
                        f"Language '{language_name}' does not support "
                        f"'{option_name}'."
                    )
                    raise ExtensionError(message=msg)
                constructor = partial(
                    constructor,
                    **{param_name: value},
                )
        return constructor

    def _build_language(
        self,
        language_name: str,
        language_cls: LanguageCls,
    ) -> Language:
        """Build a Language instance from directive options."""
        constructor = partial(language_cls)

        indent_count = self.options.get("indent")
        indent_char_name = self.options.get("indent-char")
        if indent_count is not None or indent_char_name is not None:
            resolved_count: int = 4 if indent_count is None else indent_count
            resolved_char = "\t" if indent_char_name == "tabs" else " "
            constructor = partial(
                constructor,
                indent=resolved_char * resolved_count,
            )

        constructor = self._apply_format_options(
            language_name=language_name,
            constructor=constructor,
        )
        constructor = self._apply_default_type_options(
            language_name=language_name,
            constructor=constructor,
        )
        return constructor()

    def _rendering_options(self) -> _RenderingOptions:
        """Return the rendering options derived from directive flags."""
        pre_indent_level: int = self.options.get("pre-indent-level", 0)
        include_delimiters: bool = "include-delimiters" in self.options
        variable_name: str | None = self.options.get("variable-name")
        existing_variable: bool = "existing-variable" in self.options
        return _RenderingOptions(
            pre_indent_level=pre_indent_level,
            include_delimiters=include_delimiters,
            variable_name=variable_name,
            existing_variable=existing_variable,
        )

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce a literal block."""
        env = self.state.document.settings.env
        data_path = (Path(env.srcdir) / self.arguments[0]).resolve()

        env.note_dependency(str(object=data_path))

        language_name: str = self.options["language"]
        language_cls = _language_types()[language_name]
        language_spec = self._build_language(
            language_name=language_name,
            language_cls=language_cls,
        )

        rendering = self._rendering_options()

        # YAML is a superset of JSON, so literalize_yaml handles both
        # .yaml/.yml files and .json files without any format detection.
        result = literalize_yaml(
            yaml_string=data_path.read_text(encoding="utf-8"),
            language=language_spec,
            pre_indent_level=rendering.pre_indent_level,
            include_delimiters=rendering.include_delimiters,
            variable_name=rendering.variable_name,
            new_variable=not rendering.existing_variable,
            error_on_coercion=False,
        )
        text = result.code

        # First positional arg sets rawsource; Sphinx requires
        # rawsource == astext() for syntax highlighting to apply.
        # Use the absolute path for `source` to match the behaviour of
        # Sphinx's built-in LiteralInclude directive, which also stores an
        # absolute path so that downstream code can rely on it without having
        # to resolve relative→absolute itself.
        node = nodes.literal_block(
            text,
            text,
            source=str(object=data_path),
        )
        node["language"] = language_cls.pygments_name
        self.add_name(node=node)
        return [node]


@beartype
def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the extension with Sphinx."""
    app.add_directive(name="literalizer", cls=LiteralizerDirective)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
