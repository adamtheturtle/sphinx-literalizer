"""Sphinx extension for literalizer.

Provides the ``literalizer`` and ``literalizer-call`` directives, which
read data files and render them as native language code blocks.
"""

import enum
from collections.abc import Callable, Iterable
from functools import cache, partial
from pathlib import Path
from typing import Any, ClassVar

from beartype import beartype
from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import (
    ExistingVariable,
    InputFormat,
    Language,
    LanguageCls,
    NewVariable,
    literalize,
    literalize_call,
)
from literalizer.languages import ALL_LANGUAGES
from sphinx.application import Sphinx
from sphinx.errors import ExtensionError
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata


@cache
def _language_types() -> dict[str, LanguageCls]:
    """Map directive language keys to their language classes."""
    return {
        (
            lang_cls.__name__.lower()
            if lang_cls.pygments_name is None
            else lang_cls.pygments_name
        ): lang_cls
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
    "dict-entry-style": lambda cls: cls.DictEntryStyles,
    "dict-format": lambda cls: cls.DictFormats,
    "float-format": lambda cls: cls.FloatFormats,
    "integer-format": lambda cls: cls.IntegerFormats,
    "numeric-literal-suffix": lambda cls: cls.NumericLiteralSuffixes,
    "numeric-separator": lambda cls: cls.NumericSeparators,
    "numeric-style": lambda cls: cls.NumericStyles,
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


def _parse_modifiers(
    language_name: str,
    language_cls: LanguageCls,
    value: str,
) -> frozenset[enum.Enum]:
    """Parse a comma-separated list of modifier names for the language."""
    result: set[enum.Enum] = set()
    for raw in value.split(sep=","):
        name = raw.strip()
        if not name:
            continue
        try:
            result.add(language_cls.Modifiers[name.upper()])
        except KeyError:
            msg = (
                f"Language '{language_name}' does not support "
                f"modifier '{name}'."
            )
            raise ExtensionError(message=msg) from None
    return frozenset(result)


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


_COMMON_OPTIONS: dict[str, Callable[[str], Any]] = {
    "language": lambda x: directives.choice(
        argument=x,
        values=tuple(_language_types()),
    ),
    "input-format": lambda x: directives.choice(
        argument=x,
        values=("json", "json5", "yaml", "toml"),
    ),
    "pre-indent-level": directives.nonnegative_int,
    "indent": directives.nonnegative_int,
    "indent-char": lambda x: directives.choice(
        argument=x,
        values=("spaces", "tabs"),
    ),
    "include-preamble": directives.flag,
    **{
        option_name: _make_format_validator(option_name=option_name)
        for option_name in _FORMAT_OPTION_GETTERS
    },
    "default-set-element-type": directives.unchanged,
    "default-sequence-element-type": directives.unchanged,
    "default-dict-key-type": directives.unchanged,
    "default-dict-value-type": directives.unchanged,
    "default-ordered-map-value-type": directives.unchanged,
}

_EXTENSION_TO_INPUT_FORMAT: dict[str, InputFormat] = {
    ".json": InputFormat.JSON,
    ".json5": InputFormat.JSON5,
    ".yaml": InputFormat.YAML,
    ".yml": InputFormat.YAML,
    ".toml": InputFormat.TOML,
}


@beartype
class _BaseLiteralizerDirective(SphinxDirective):
    """Shared logic for literalizer directives."""

    required_arguments = 1
    has_content = False

    def _apply_format_options(
        self,
        language_name: str,
        constructor: partial[Language],
    ) -> partial[Language]:
        """Apply all format/enum options."""
        all_formats = _all_formats()
        for option_name in _FORMAT_OPTION_GETTERS:
            if (value := self.options.get(option_name)) is not None:
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
            "default-ordered-map-value-type": (
                "default_ordered_map_value_type",
                lambda cls: cls.supports_default_ordered_map_value_type,
            ),
        }
        language_cls = _language_types()[language_name]
        for option_name, (
            param_name,
            supports_check,
        ) in type_option_map.items():
            if (value := self.options.get(option_name)) is not None:
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

    def _resolve_input_format(self, data_path: Path) -> InputFormat:
        """Determine the input format from the option or file
        extension.
        """
        explicit = self.options.get("input-format")
        if explicit is not None:
            return InputFormat[explicit.upper()]
        suffix = data_path.suffix.lower()
        try:
            return _EXTENSION_TO_INPUT_FORMAT[suffix]
        except KeyError:
            msg = (
                f"Cannot determine input format for '{data_path.name}'. "
                f"Use the :input-format: option."
            )
            raise ExtensionError(message=msg) from None

    def _make_node(
        self,
        text: str,
        data_path: Path,
        language_cls: LanguageCls,
    ) -> list[nodes.Node]:
        """Create a literal_block node."""
        node = nodes.literal_block(
            text,
            text,
            source=str(object=data_path),
        )
        node["language"] = language_cls.pygments_name or "text"
        self.add_name(node=node)
        return [node]


@beartype
class LiteralizerDirective(_BaseLiteralizerDirective):
    """Directive that converts a data file to a native literal block.

    Usage::

        .. literalizer:: path/to/data.json
           :language: python
           :input-format: json
           :pre-indent-level: 2
           :indent: 4
           :indent-char: spaces
           :include-delimiters:
           :include-preamble:
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
           :dict-entry-style: rocket
           :dict-format: object
           :float-format: repr
           :integer-format: decimal
           :numeric-literal-suffix: none
           :numeric-separator: none
           :numeric-style: overloaded
           :string-format: double
           :trailing-comma: yes
           :line-ending: semicolon
           :empty-dict-key: positional
           :default-set-element-type: String
           :default-sequence-element-type: String
           :default-dict-key-type: String
           :default-dict-value-type: String
           :default-ordered-map-value-type: any
           :modifiers: public,static,final
    """

    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        **_COMMON_OPTIONS,
        "include-delimiters": directives.flag,
        "variable-name": directives.unchanged,
        "existing-variable": directives.flag,
        "modifiers": directives.unchanged,
    }

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

        pre_indent_level: int = self.options.get("pre-indent-level", 0)
        include_delimiters: bool = "include-delimiters" in self.options
        include_preamble: bool = "include-preamble" in self.options
        variable_name: str | None = self.options.get("variable-name")
        existing_variable: bool = "existing-variable" in self.options
        modifiers_value: str | None = self.options.get("modifiers")

        if modifiers_value is not None and variable_name is None:
            msg = "':modifiers:' requires ':variable-name:'."
            raise ExtensionError(message=msg)
        if modifiers_value is not None and existing_variable:
            msg = (
                "':modifiers:' cannot be combined with ':existing-variable:'."
            )
            raise ExtensionError(message=msg)

        modifiers: frozenset[enum.Enum] = frozenset()
        if modifiers_value is not None:
            modifiers = _parse_modifiers(
                language_name=language_name,
                language_cls=language_cls,
                value=modifiers_value,
            )

        variable_form = None
        if variable_name is not None:
            variable_form = (
                ExistingVariable(name=variable_name)
                if existing_variable
                else NewVariable(name=variable_name, modifiers=modifiers)
            )

        input_format = self._resolve_input_format(data_path=data_path)
        result = literalize(
            source=data_path.read_text(encoding="utf-8"),
            input_format=input_format,
            language=language_spec,
            pre_indent_level=pre_indent_level,
            include_delimiters=include_delimiters,
            variable_form=variable_form,
        )
        parts: list[str] = []
        if include_preamble and result.preamble:
            parts.append("\n".join(result.preamble))
        parts.append(result.code)
        text = "\n\n".join(parts)

        # First positional arg sets rawsource; Sphinx requires
        # rawsource == astext() for syntax highlighting to apply.
        # Use the absolute path for `source` to match the behaviour of
        # Sphinx's built-in LiteralInclude directive, which also stores an
        # absolute path so that downstream code can rely on it without having
        # to resolve relative→absolute itself.
        return self._make_node(
            text=text,
            data_path=data_path,
            language_cls=language_cls,
        )


@beartype
class LiteralizerCallDirective(_BaseLiteralizerDirective):
    """Directive that converts a data file to function call expressions.

    Usage::

        .. literalizer-call:: path/to/data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :call-transform: print($0)
           :input-format: json
           :indent: 4
           :indent-char: spaces
           :include-preamble:
    """

    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        **_COMMON_OPTIONS,
        "target-function": directives.unchanged_required,
        "parameter-names": directives.unchanged_required,
        "per-element": directives.flag,
        "call-transform": directives.unchanged_required,
    }

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce function call expressions."""
        env = self.state.document.settings.env
        data_path = (Path(env.srcdir) / self.arguments[0]).resolve()

        env.note_dependency(str(object=data_path))

        language_name: str = self.options["language"]
        language_cls = _language_types()[language_name]
        language_spec = self._build_language(
            language_name=language_name,
            language_cls=language_cls,
        )

        pre_indent_level: int = self.options.get("pre-indent-level", 0)
        include_preamble: bool = "include-preamble" in self.options
        target_function: str = self.options["target-function"]
        parameter_names = [
            p.strip() for p in self.options["parameter-names"].split(",")
        ]
        per_element: bool = "per-element" in self.options

        call_transform_template: str | None = self.options.get(
            "call-transform",
        )
        call_transform: Callable[[str], str] | None = None
        if call_transform_template is not None:
            template = call_transform_template

            def _call_transform(call_str: str) -> str:
                """Replace ``$0`` with the call expression."""
                return template.replace("$0", call_str)

            call_transform = _call_transform

        input_format = self._resolve_input_format(data_path=data_path)
        result = literalize_call(
            source=data_path.read_text(encoding="utf-8"),
            input_format=input_format,
            language=language_spec,
            target_function=target_function,
            parameter_names=parameter_names,
            call_transform=call_transform,
            per_element=per_element,
        )

        code = result.code
        if pre_indent_level > 0:
            indent = language_spec.indent * pre_indent_level
            code = "\n".join(
                indent + line if line else line for line in code.splitlines()
            )

        parts: list[str] = []
        if include_preamble and result.preamble:
            parts.append("\n".join(result.preamble))
        parts.append(code)
        text = "\n\n".join(parts)

        return self._make_node(
            text=text,
            data_path=data_path,
            language_cls=language_cls,
        )


@beartype
def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the extension with Sphinx."""
    app.add_directive(name="literalizer", cls=LiteralizerDirective)
    app.add_directive(
        name="literalizer-call",
        cls=LiteralizerCallDirective,
    )
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
