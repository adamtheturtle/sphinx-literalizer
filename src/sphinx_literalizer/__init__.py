"""Sphinx extension for literalizer.

Provides the ``literalizer`` directive, which reads a JSON file and
renders it as a native language literal block.
"""

from collections.abc import Callable
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


@cache
def _date_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to DateFormats enum member."""
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.DateFormats
    }


@cache
def _date_format_values() -> tuple[str, ...]:
    """Return sorted unique DateFormats member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _date_formats()}))


@cache
def _datetime_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to DatetimeFormats enum member."""
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.DatetimeFormats
    }


@cache
def _datetime_format_values() -> tuple[str, ...]:
    """Return sorted unique DatetimeFormats member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _datetime_formats()}))


@cache
def _sequence_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to SequenceFormats enum member."""
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.SequenceFormats
    }


@cache
def _sequence_format_values() -> tuple[str, ...]:
    """Return sorted unique SequenceFormats member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _sequence_formats()}))


@cache
def _set_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to SetFormats enum member."""
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.SetFormats
    }


@cache
def _set_format_values() -> tuple[str, ...]:
    """Return sorted unique SetFormats member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _set_formats()}))


@cache
def _bytes_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to BytesFormats enum member."""
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.BytesFormats
    }


@cache
def _bytes_format_values() -> tuple[str, ...]:
    """Return sorted unique BytesFormats member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _bytes_formats()}))


@cache
def _comment_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to CommentFormats enum member."""
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.CommentFormats
    }


@cache
def _comment_format_values() -> tuple[str, ...]:
    """Return sorted unique CommentFormats member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _comment_formats()}))


@cache
def _variable_type_hints_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to VariableTypeHints enum
    member.
    """
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.VariableTypeHints
    }


@cache
def _variable_type_hints_format_values() -> tuple[str, ...]:
    """Return sorted unique VariableTypeHints member names."""
    return tuple(
        sorted({fmt_value for _, fmt_value in _variable_type_hints_formats()})
    )


@cache
def _declaration_styles() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to DeclarationStyles enum
    member.
    """
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.DeclarationStyles
    }


@cache
def _declaration_style_values() -> tuple[str, ...]:
    """Return sorted unique DeclarationStyles member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _declaration_styles()}))


@cache
def _dict_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to DictFormats enum member."""
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.DictFormats
    }


@cache
def _dict_format_values() -> tuple[str, ...]:
    """Return sorted unique DictFormats member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _dict_formats()}))


@cache
def _integer_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to IntegerFormats enum
    member.
    """
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.IntegerFormats
    }


@cache
def _integer_format_values() -> tuple[str, ...]:
    """Return sorted unique IntegerFormats member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _integer_formats()}))


@cache
def _numeric_separators() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to NumericSeparators enum
    member.
    """
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.NumericSeparators
    }


@cache
def _numeric_separator_values() -> tuple[str, ...]:
    """Return sorted unique NumericSeparators member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _numeric_separators()}))


@cache
def _string_formats() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to StringFormats enum member."""
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.StringFormats
    }


@cache
def _string_format_values() -> tuple[str, ...]:
    """Return sorted unique StringFormats member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _string_formats()}))


@cache
def _trailing_commas() -> dict[tuple[str, str], object]:
    """Map (language_key, member_name) to TrailingCommas enum
    member.
    """
    return {
        (lang_name, member.name.lower()): member
        for lang_name, lang_cls in _language_types().items()
        for member in lang_cls.TrailingCommas
    }


@cache
def _trailing_comma_values() -> tuple[str, ...]:
    """Return sorted unique TrailingCommas member names."""
    return tuple(sorted({fmt_value for _, fmt_value in _trailing_commas()}))


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


@beartype
class LiteralizerDirective(SphinxDirective):
    """Directive that converts a JSON file to a native literal block.

    Usage::

        .. literalizer:: path/to/data.json
           :language: python
           :prefix: 8
           :prefix-char: spaces
           :indent: 4
           :include-delimiters:
           :date-format: python
           :datetime-format: python
           :variable-name: my_var
           :existing-variable:
           :sequence-format: list
           :set-format: frozenset
           :bytes-format: python
           :comment-format: block
           :variable-type-hints: inline
           :declaration-style: const
           :dict-format: object
           :integer-format: decimal
           :numeric-separator: none
           :string-format: double
           :trailing-comma: yes
    """

    required_arguments = 1
    has_content = False
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        "language": lambda x: directives.choice(
            argument=x,
            values=tuple(_language_types()),
        ),
        "prefix": directives.nonnegative_int,
        "prefix-char": lambda x: directives.choice(
            argument=x,
            values=("spaces", "tabs"),
        ),
        "indent": directives.nonnegative_int,
        "include-delimiters": directives.flag,
        "date-format": lambda x: directives.choice(
            argument=x,
            values=_date_format_values(),
        ),
        "datetime-format": lambda x: directives.choice(
            argument=x,
            values=_datetime_format_values(),
        ),
        "variable-name": directives.unchanged,
        "existing-variable": directives.flag,
        "sequence-format": lambda x: directives.choice(
            argument=x,
            values=_sequence_format_values(),
        ),
        "set-format": lambda x: directives.choice(
            argument=x,
            values=_set_format_values(),
        ),
        "bytes-format": lambda x: directives.choice(
            argument=x,
            values=_bytes_format_values(),
        ),
        "comment-format": lambda x: directives.choice(
            argument=x,
            values=_comment_format_values(),
        ),
        "variable-type-hints": lambda x: directives.choice(
            argument=x,
            values=_variable_type_hints_format_values(),
        ),
        "declaration-style": lambda x: directives.choice(
            argument=x,
            values=_declaration_style_values(),
        ),
        "dict-format": lambda x: directives.choice(
            argument=x,
            values=_dict_format_values(),
        ),
        "integer-format": lambda x: directives.choice(
            argument=x,
            values=_integer_format_values(),
        ),
        "numeric-separator": lambda x: directives.choice(
            argument=x,
            values=_numeric_separator_values(),
        ),
        "string-format": lambda x: directives.choice(
            argument=x,
            values=_string_format_values(),
        ),
        "trailing-comma": lambda x: directives.choice(
            argument=x,
            values=_trailing_comma_values(),
        ),
    }

    def _apply_serialization_options(
        self,
        language_name: str,
        constructor: partial[Language],
    ) -> partial[Language]:
        """Apply date, sequence, set, bytes, comment, and type-hint
        options.
        """
        date_format_value = self.options.get("date-format")
        if date_format_value is not None:
            constructor = partial(
                constructor,
                date_format=_lookup_format(
                    language_name=language_name,
                    directive_name="date-format",
                    format_value=date_format_value,
                    formats=_date_formats(),
                ),
            )

        datetime_format_value = self.options.get("datetime-format")
        if datetime_format_value is not None:
            constructor = partial(
                constructor,
                datetime_format=_lookup_format(
                    language_name=language_name,
                    directive_name="datetime-format",
                    format_value=datetime_format_value,
                    formats=_datetime_formats(),
                ),
            )

        sequence_format_value = self.options.get("sequence-format")
        if sequence_format_value is not None:
            constructor = partial(
                constructor,
                sequence_format=_lookup_format(
                    language_name=language_name,
                    directive_name="sequence-format",
                    format_value=sequence_format_value,
                    formats=_sequence_formats(),
                ),
            )

        set_format_value = self.options.get("set-format")
        if set_format_value is not None:
            constructor = partial(
                constructor,
                set_format=_lookup_format(
                    language_name=language_name,
                    directive_name="set-format",
                    format_value=set_format_value,
                    formats=_set_formats(),
                ),
            )

        bytes_format_value = self.options.get("bytes-format")
        if bytes_format_value is not None:
            constructor = partial(
                constructor,
                bytes_format=_lookup_format(
                    language_name=language_name,
                    directive_name="bytes-format",
                    format_value=bytes_format_value,
                    formats=_bytes_formats(),
                ),
            )

        comment_format_value = self.options.get("comment-format")
        if comment_format_value is not None:
            constructor = partial(
                constructor,
                comment_format=_lookup_format(
                    language_name=language_name,
                    directive_name="comment-format",
                    format_value=comment_format_value,
                    formats=_comment_formats(),
                ),
            )

        variable_type_hints_value = self.options.get(
            "variable-type-hints",
        )
        if variable_type_hints_value is not None:
            constructor = partial(
                constructor,
                variable_type_hints=_lookup_format(
                    language_name=language_name,
                    directive_name="variable-type-hints",
                    format_value=variable_type_hints_value,
                    formats=_variable_type_hints_formats(),
                ),
            )

        return constructor

    def _apply_syntax_options(
        self,
        language_name: str,
        constructor: partial[Language],
    ) -> partial[Language]:
        """Apply declaration, dict, integer, numeric, string, and
        trailing-comma options.
        """
        declaration_style_value = self.options.get("declaration-style")
        if declaration_style_value is not None:
            constructor = partial(
                constructor,
                declaration_style=_lookup_format(
                    language_name=language_name,
                    directive_name="declaration-style",
                    format_value=declaration_style_value,
                    formats=_declaration_styles(),
                ),
            )

        dict_format_value = self.options.get("dict-format")
        if dict_format_value is not None:
            constructor = partial(
                constructor,
                dict_format=_lookup_format(
                    language_name=language_name,
                    directive_name="dict-format",
                    format_value=dict_format_value,
                    formats=_dict_formats(),
                ),
            )

        integer_format_value = self.options.get("integer-format")
        if integer_format_value is not None:
            constructor = partial(
                constructor,
                integer_format=_lookup_format(
                    language_name=language_name,
                    directive_name="integer-format",
                    format_value=integer_format_value,
                    formats=_integer_formats(),
                ),
            )

        numeric_separator_value = self.options.get(
            "numeric-separator",
        )
        if numeric_separator_value is not None:
            constructor = partial(
                constructor,
                numeric_separator=_lookup_format(
                    language_name=language_name,
                    directive_name="numeric-separator",
                    format_value=numeric_separator_value,
                    formats=_numeric_separators(),
                ),
            )

        string_format_value = self.options.get("string-format")
        if string_format_value is not None:
            constructor = partial(
                constructor,
                string_format=_lookup_format(
                    language_name=language_name,
                    directive_name="string-format",
                    format_value=string_format_value,
                    formats=_string_formats(),
                ),
            )

        trailing_comma_value = self.options.get("trailing-comma")
        if trailing_comma_value is not None:
            constructor = partial(
                constructor,
                trailing_comma=_lookup_format(
                    language_name=language_name,
                    directive_name="trailing-comma",
                    format_value=trailing_comma_value,
                    formats=_trailing_commas(),
                ),
            )

        return constructor

    def _build_language(
        self,
        language_name: str,
        language_cls: LanguageCls,
    ) -> Language:
        """Build a Language instance from directive options."""
        constructor = partial(language_cls)
        constructor = self._apply_serialization_options(
            language_name=language_name,
            constructor=constructor,
        )
        constructor = self._apply_syntax_options(
            language_name=language_name,
            constructor=constructor,
        )
        return constructor()

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce a literal block."""
        env = self.state.document.settings.env
        rel_path = self.arguments[0]
        source_dir = Path(env.srcdir)
        data_path = (source_dir / rel_path).resolve()

        env.note_dependency(str(object=data_path))

        language_name: str = self.options["language"]
        language_cls = _language_types()[language_name]
        language_spec = self._build_language(
            language_name=language_name,
            language_cls=language_cls,
        )

        prefix_count: int = self.options.get("prefix", 0)
        prefix_char_name: str = self.options.get("prefix-char", "spaces")
        prefix_char = "\t" if prefix_char_name == "tabs" else " "
        line_prefix = prefix_char * prefix_count
        indent_count: int = self.options.get("indent", 4)
        indent = prefix_char * indent_count
        include_delimiters: bool = "include-delimiters" in self.options
        variable_name: str | None = self.options.get("variable-name")
        existing_variable: bool = "existing-variable" in self.options

        # YAML is a superset of JSON, so literalize_yaml handles both
        # .yaml/.yml files and .json files without any format detection.
        result = literalize_yaml(
            yaml_string=data_path.read_text(encoding="utf-8"),
            language=language_spec,
            line_prefix=line_prefix,
            indent=indent,
            include_delimiters=include_delimiters,
            variable_name=variable_name,
            new_variable=not existing_variable,
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
