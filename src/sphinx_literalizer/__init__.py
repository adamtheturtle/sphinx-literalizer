"""Sphinx extension for literalizer.

Provides the ``literalizer`` directive, which reads a JSON file and
renders it as a native language literal block.
"""

import dataclasses
import datetime
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import LanguageSpec, literalize_yaml
from literalizer.formatters import (
    format_date_cpp,
    format_date_csharp,
    format_date_go,
    format_date_iso,
    format_date_java,
    format_date_js,
    format_date_kotlin,
    format_date_php,
    format_date_python,
    format_date_ruby,
    format_datetime_cpp,
    format_datetime_csharp,
    format_datetime_epoch,
    format_datetime_go,
    format_datetime_iso,
    format_datetime_java_instant,
    format_datetime_java_zoned,
    format_datetime_js,
    format_datetime_kotlin,
    format_datetime_php,
    format_datetime_python,
    format_datetime_ruby,
)
from literalizer.languages import (
    CPP,
    CSHARP,
    GO,
    JAVA,
    JAVASCRIPT,
    KOTLIN,
    PHP,
    PYTHON,
    RUBY,
    SWIFT,
    TYPESCRIPT,
)
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata

_LANGUAGES: dict[str, LanguageSpec] = {
    "cpp": CPP,
    "csharp": CSHARP,
    "go": GO,
    "java": JAVA,
    "javascript": JAVASCRIPT,
    "kotlin": KOTLIN,
    "php": PHP,
    "python": PYTHON,
    "ruby": RUBY,
    "swift": SWIFT,
    "typescript": TYPESCRIPT,
}


@dataclasses.dataclass(frozen=True)
class _DateFormat:
    """Date formatting functions for a specific date format."""

    format_date: Callable[[datetime.date], str]
    format_datetime: Callable[[datetime.datetime], str]


_DATE_FORMATS: dict[str, _DateFormat] = {
    "iso": _DateFormat(
        format_date=format_date_iso,
        format_datetime=format_datetime_iso,
    ),
    "python": _DateFormat(
        format_date=format_date_python,
        format_datetime=format_datetime_python,
    ),
    "epoch": _DateFormat(
        format_date=format_date_iso,
        format_datetime=format_datetime_epoch,
    ),
    "java-instant": _DateFormat(
        format_date=format_date_java,
        format_datetime=format_datetime_java_instant,
    ),
    "java-zoned": _DateFormat(
        format_date=format_date_java,
        format_datetime=format_datetime_java_zoned,
    ),
    "ruby": _DateFormat(
        format_date=format_date_ruby,
        format_datetime=format_datetime_ruby,
    ),
    "javascript": _DateFormat(
        format_date=format_date_js,
        format_datetime=format_datetime_js,
    ),
    "csharp": _DateFormat(
        format_date=format_date_csharp,
        format_datetime=format_datetime_csharp,
    ),
    "go": _DateFormat(
        format_date=format_date_go,
        format_datetime=format_datetime_go,
    ),
    "kotlin": _DateFormat(
        format_date=format_date_kotlin,
        format_datetime=format_datetime_kotlin,
    ),
    "cpp": _DateFormat(
        format_date=format_date_cpp,
        format_datetime=format_datetime_cpp,
    ),
    "php": _DateFormat(
        format_date=format_date_php,
        format_datetime=format_datetime_php,
    ),
}


class LiteralizerDirective(SphinxDirective):
    """Directive that converts a JSON file to a native literal block.

    Usage::

        .. literalizer:: path/to/data.json
           :language: python
           :prefix: 8
           :prefix-char: spaces
           :wrap:
    """

    required_arguments = 1
    has_content = False
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        "language": directives.unchanged_required,
        "prefix": directives.nonnegative_int,
        "prefix-char": lambda x: directives.choice(
            argument=x,
            values=("spaces", "tabs"),
        ),
        "wrap": directives.flag,
        "date-format": lambda x: directives.choice(
            argument=x,
            values=tuple(_DATE_FORMATS),
        ),
        "variable-name": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce a literal block."""
        env = self.state.document.settings.env
        rel_path = self.arguments[0]
        source_dir = Path(env.srcdir)
        data_path = (source_dir / rel_path).resolve()

        env.note_dependency(str(object=data_path))

        language_name: str = self.options["language"]
        language_spec: LanguageSpec = _LANGUAGES[language_name]
        date_format_name: str | None = self.options.get("date-format")
        if date_format_name is not None:
            date_format_pair = _DATE_FORMATS[date_format_name]
            language_spec = dataclasses.replace(
                language_spec,
                format_date=date_format_pair.format_date,
                format_datetime=date_format_pair.format_datetime,
            )
        prefix_count: int = self.options.get("prefix", 0)
        prefix_char_name: str = self.options.get("prefix-char", "spaces")
        prefix_char = "\t" if prefix_char_name == "tabs" else " "
        prefix = prefix_char * prefix_count
        wrap: bool = "wrap" in self.options
        variable_name: str | None = self.options.get("variable-name")

        # YAML is a superset of JSON, so literalize_yaml handles both
        # .yaml/.yml files and .json files without any format detection.
        text = literalize_yaml(
            yaml_string=data_path.read_text(encoding="utf-8"),
            language=language_spec,
            prefix=prefix,
            wrap=wrap,
            variable_name=variable_name,
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
        node["language"] = language_name
        self.add_name(node=node)
        return [node]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the extension with Sphinx."""
    app.add_directive(name="literalizer", cls=LiteralizerDirective)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
