"""Sphinx extension for literalizer.

Provides the ``literalizer`` directive, which reads a JSON file and
renders it as a native language literal block.
"""

import dataclasses
import datetime
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import (
    CPP,
    CSHARP,
    GO,
    JAVA,
    JAVASCRIPT,
    KOTLIN,
    PYTHON,
    RUBY,
    TYPESCRIPT,
    LanguageSpec,
    format_date_cpp,
    format_date_csharp,
    format_date_go,
    format_date_iso,
    format_date_java,
    format_date_js,
    format_date_kotlin,
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
    format_datetime_python,
    format_datetime_ruby,
    literalize_yaml,
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
    "python": PYTHON,
    "ruby": RUBY,
    "typescript": TYPESCRIPT,
}

@dataclasses.dataclass(frozen=True)
class _DateFormatPair:
    format_date: Callable[[datetime.date], str]
    format_datetime: Callable[[datetime.datetime], str]


_DATE_FORMATS: dict[str, _DateFormatPair] = {
    "iso": _DateFormatPair(
        format_date=format_date_iso,
        format_datetime=format_datetime_iso,
    ),
    "python": _DateFormatPair(
        format_date=format_date_python,
        format_datetime=format_datetime_python,
    ),
    "epoch": _DateFormatPair(
        format_date=format_date_iso,
        format_datetime=format_datetime_epoch,
    ),
    "java-instant": _DateFormatPair(
        format_date=format_date_java,
        format_datetime=format_datetime_java_instant,
    ),
    "java-zoned": _DateFormatPair(
        format_date=format_date_java,
        format_datetime=format_datetime_java_zoned,
    ),
    "ruby": _DateFormatPair(
        format_date=format_date_ruby,
        format_datetime=format_datetime_ruby,
    ),
    "javascript": _DateFormatPair(
        format_date=format_date_js,
        format_datetime=format_datetime_js,
    ),
    "csharp": _DateFormatPair(
        format_date=format_date_csharp,
        format_datetime=format_datetime_csharp,
    ),
    "go": _DateFormatPair(
        format_date=format_date_go,
        format_datetime=format_datetime_go,
    ),
    "kotlin": _DateFormatPair(
        format_date=format_date_kotlin,
        format_datetime=format_datetime_kotlin,
    ),
    "cpp": _DateFormatPair(
        format_date=format_date_cpp,
        format_datetime=format_datetime_cpp,
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
    option_spec: ClassVar[dict[str, object]] = {
        "language": directives.unchanged_required,
        "prefix": directives.nonnegative_int,
        "prefix-char": lambda x: directives.choice(x, ("spaces", "tabs")),
        "wrap": directives.flag,
        "date-format": lambda x: directives.choice(x, tuple(_DATE_FORMATS)),
    }

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce a literal block."""
        env = self.state.document.settings.env
        rel_path = self.arguments[0]
        source_dir = Path(env.srcdir)
        data_path = (source_dir / rel_path).resolve()

        env.note_dependency(str(data_path))

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

        # YAML is a superset of JSON, so literalize_yaml handles both
        # .yaml/.yml files and .json files without any format detection.
        text = literalize_yaml(
            yaml_string=data_path.read_text(encoding="utf-8"),
            language=language_spec,
            prefix=prefix,
            wrap=wrap,
        )

        # First positional arg sets rawsource; Sphinx requires
        # rawsource == astext() for syntax highlighting to apply.
        # Use the absolute path for `source` to match the behaviour of
        # Sphinx's built-in LiteralInclude directive, which also stores an
        # absolute path so that downstream code can rely on it without having
        # to resolve relative→absolute itself.
        node = nodes.literal_block(text, text, source=str(data_path))
        node["language"] = language_name
        self.add_name(node=node)
        return [node]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the extension with Sphinx."""
    app.add_directive("literalizer", LiteralizerDirective)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
