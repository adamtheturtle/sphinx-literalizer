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
    }

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce a literal block."""
        env = self.state.document.settings.env
        rel_path = self.arguments[0]
        source_dir = Path(env.srcdir)
        data_path = (source_dir / rel_path).resolve()

        env.note_dependency(str(object=data_path))

        language_name: str = self.options["language"]
        language_cls = _language_types()[language_name]
        constructor = partial(language_cls)

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

        variable_type_hints_value = self.options.get("variable-type-hints")
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

        language_spec: Language = constructor()

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
        text = literalize_yaml(
            yaml_string=data_path.read_text(encoding="utf-8"),
            language=language_spec,
            line_prefix=line_prefix,
            indent=indent,
            include_delimiters=include_delimiters,
            variable_name=variable_name,
            new_variable=not existing_variable,
            error_on_coercion=False,
        )

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
