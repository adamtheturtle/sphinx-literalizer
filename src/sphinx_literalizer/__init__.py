"""Sphinx extension for literalizer.

Provides the ``literalizer`` directive, which reads a JSON file and
renders it as a native language literal block.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, ClassVar

from beartype import beartype
from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import HasFormatEnums, Language, literalize_yaml
from literalizer.languages import (
    Ada,
    Bash,
    C,
    Clojure,
    Cobol,
    CommonLisp,
    Cpp,
    Crystal,
    CSharp,
    D,
    Dart,
    Elixir,
    Erlang,
    Fortran,
    FSharp,
    Go,
    Groovy,
    Haskell,
    Hcl,
    Java,
    JavaScript,
    Julia,
    Kotlin,
    Lua,
    Matlab,
    Mojo,
    Nim,
    Norg,
    ObjectiveC,
    OCaml,
    Occam,
    Perl,
    Php,
    PowerShell,
    Python,
    R,
    Racket,
    Ruby,
    Rust,
    Scala,
    Swift,
    Toml,
    TypeScript,
    VisualBasic,
    Yaml,
    Zig,
)
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata

_LANGUAGE_TYPES: dict[str, HasFormatEnums] = {
    "ada": Ada,
    "bash": Bash,
    "c": C,
    "clojure": Clojure,
    "cobol": Cobol,
    "common-lisp": CommonLisp,
    "cpp": Cpp,
    "crystal": Crystal,
    "csharp": CSharp,
    "d": D,
    "dart": Dart,
    "elixir": Elixir,
    "erlang": Erlang,
    "fortran": Fortran,
    "fsharp": FSharp,
    "go": Go,
    "groovy": Groovy,
    "haskell": Haskell,
    "hcl": Hcl,
    "java": Java,
    "javascript": JavaScript,
    "julia": Julia,
    "kotlin": Kotlin,
    "lua": Lua,
    "matlab": Matlab,
    "mojo": Mojo,
    "nim": Nim,
    "norg": Norg,
    "objective-c": ObjectiveC,
    "ocaml": OCaml,
    "occam": Occam,
    "perl": Perl,
    "php": Php,
    "powershell": PowerShell,
    "python": Python,
    "r": R,
    "racket": Racket,
    "ruby": Ruby,
    "rust": Rust,
    "scala": Scala,
    "swift": Swift,
    "toml": Toml,
    "typescript": TypeScript,
    "visual-basic": VisualBasic,
    "yaml": Yaml,
    "zig": Zig,
}


@beartype
@dataclass(frozen=True)
class _DateFormats:
    """Date and datetime format options for a language."""

    date_format: object | None = None
    datetime_format: object | None = None


_DATE_FORMATS: dict[str, _DateFormats] = {
    "cpp": _DateFormats(
        date_format=Cpp.date_formats.CPP,
        datetime_format=Cpp.datetime_formats.CPP,
    ),
    "csharp": _DateFormats(
        date_format=CSharp.date_formats.CSHARP,
        datetime_format=CSharp.datetime_formats.CSHARP,
    ),
    "dart": _DateFormats(
        date_format=Dart.date_formats.DART,
        datetime_format=Dart.datetime_formats.DART,
    ),
    "epoch": _DateFormats(datetime_format=Python.datetime_formats.EPOCH),
    "go": _DateFormats(
        date_format=Go.date_formats.GO,
        datetime_format=Go.datetime_formats.GO,
    ),
    "iso": _DateFormats(),
    "java-instant": _DateFormats(
        date_format=Java.date_formats.JAVA,
        datetime_format=Java.datetime_formats.INSTANT,
    ),
    "java-zoned": _DateFormats(
        date_format=Java.date_formats.JAVA,
        datetime_format=Java.datetime_formats.ZONED,
    ),
    "javascript": _DateFormats(
        date_format=JavaScript.date_formats.JS,
        datetime_format=JavaScript.datetime_formats.JS,
    ),
    "julia": _DateFormats(
        date_format=Julia.date_formats.JULIA,
        datetime_format=Julia.datetime_formats.JULIA,
    ),
    "kotlin": _DateFormats(
        date_format=Kotlin.date_formats.KOTLIN,
        datetime_format=Kotlin.datetime_formats.KOTLIN,
    ),
    "python": _DateFormats(
        date_format=Python.date_formats.PYTHON,
        datetime_format=Python.datetime_formats.PYTHON,
    ),
    "r": _DateFormats(
        date_format=R.date_formats.R,
        datetime_format=R.datetime_formats.R,
    ),
    "ruby": _DateFormats(
        date_format=Ruby.date_formats.RUBY,
        datetime_format=Ruby.datetime_formats.RUBY,
    ),
    "rust": _DateFormats(
        date_format=Rust.date_formats.RUST,
        datetime_format=Rust.datetime_formats.RUST,
    ),
    "typescript": _DateFormats(
        date_format=TypeScript.date_formats.JS,
        datetime_format=TypeScript.datetime_formats.JS,
    ),
}

_SEQUENCE_FORMATS: dict[tuple[str, str], object] = {
    (lang_name, member.name.lower()): member
    for lang_name, lang_cls in _LANGUAGE_TYPES.items()
    for member in lang_cls.SequenceFormats
}

_SEQUENCE_FORMAT_VALUES: tuple[str, ...] = tuple(
    sorted({fmt_value for _, fmt_value in _SEQUENCE_FORMATS})
)

_SET_FORMATS: dict[tuple[str, str], object] = {
    (lang_name, member.name.lower()): member
    for lang_name, lang_cls in _LANGUAGE_TYPES.items()
    for member in lang_cls.SetFormats
}

_SET_FORMAT_VALUES: tuple[str, ...] = tuple(
    sorted({fmt_value for _, fmt_value in _SET_FORMATS})
)

_BYTES_FORMATS: dict[tuple[str, str], object] = {
    (lang_name, member.name.lower()): member
    for lang_name, lang_cls in _LANGUAGE_TYPES.items()
    for member in lang_cls.BytesFormats
}

_BYTES_FORMAT_VALUES: tuple[str, ...] = tuple(
    sorted({fmt_value for _, fmt_value in _BYTES_FORMATS})
)


@beartype
def _apply_date_formats(
    constructor: partial[Language],
    date_formats: _DateFormats,
) -> partial[Language]:
    """Apply date and datetime format options to a constructor."""
    if date_formats.date_format is not None:
        constructor = partial(
            constructor,
            date_format=date_formats.date_format,
        )
    if date_formats.datetime_format is not None:
        constructor = partial(
            constructor,
            datetime_format=date_formats.datetime_format,
        )
    return constructor


@beartype
def _default_constructor(
    language_name: str,
) -> partial[Language]:
    """Build a language constructor."""
    language_cls = _LANGUAGE_TYPES[language_name]
    return partial(language_cls)


@beartype
class LiteralizerDirective(SphinxDirective):
    """Directive that converts a JSON file to a native literal block.

    Usage::

        .. literalizer:: path/to/data.json
           :language: python
           :prefix: 8
           :prefix-char: spaces
           :indent: 4
           :wrap:
           :variable-name: my_var
           :existing-variable:
           :sequence-format: list
           :set-format: frozenset
           :bytes-format: python
    """

    required_arguments = 1
    has_content = False
    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        "language": lambda x: directives.choice(
            argument=x,
            values=tuple(_LANGUAGE_TYPES),
        ),
        "prefix": directives.nonnegative_int,
        "prefix-char": lambda x: directives.choice(
            argument=x,
            values=("spaces", "tabs"),
        ),
        "indent": directives.nonnegative_int,
        "wrap": directives.flag,
        "date-format": lambda x: directives.choice(
            argument=x,
            values=tuple(_DATE_FORMATS),
        ),
        "variable-name": directives.unchanged,
        "existing-variable": directives.flag,
        "sequence-format": lambda x: directives.choice(
            argument=x,
            values=_SEQUENCE_FORMAT_VALUES,
        ),
        "set-format": lambda x: directives.choice(
            argument=x,
            values=_SET_FORMAT_VALUES,
        ),
        "bytes-format": lambda x: directives.choice(
            argument=x,
            values=_BYTES_FORMAT_VALUES,
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
        constructor = _default_constructor(language_name=language_name)

        date_format_name: str | None = self.options.get("date-format")
        if date_format_name is not None:
            constructor = _apply_date_formats(
                constructor=constructor,
                date_formats=_DATE_FORMATS[date_format_name],
            )

        sequence_format_option: str | None = self.options.get(
            "sequence-format",
        )
        if sequence_format_option is not None:
            sequence_format_key = (language_name, sequence_format_option)
            constructor = partial(
                constructor,
                sequence_format=_SEQUENCE_FORMATS[sequence_format_key],
            )

        set_format_option: str | None = self.options.get("set-format")
        if set_format_option is not None:
            constructor = partial(
                constructor,
                set_format=_SET_FORMATS[(language_name, set_format_option)],
            )

        bytes_format_option: str | None = self.options.get(
            "bytes-format",
        )
        if bytes_format_option is not None:
            constructor = partial(
                constructor,
                bytes_format=_BYTES_FORMATS[
                    (language_name, bytes_format_option)
                ],
            )

        language_spec: Language = constructor()

        prefix_count: int = self.options.get("prefix", 0)
        prefix_char_name: str = self.options.get("prefix-char", "spaces")
        prefix_char = "\t" if prefix_char_name == "tabs" else " "
        line_prefix = prefix_char * prefix_count
        indent_count: int = self.options.get("indent", 4)
        indent = prefix_char * indent_count
        wrap: bool = "wrap" in self.options
        variable_name: str | None = self.options.get("variable-name")
        existing_variable: bool = "existing-variable" in self.options

        # YAML is a superset of JSON, so literalize_yaml handles both
        # .yaml/.yml files and .json files without any format detection.
        text = literalize_yaml(
            yaml_string=data_path.read_text(encoding="utf-8"),
            language=language_spec,
            line_prefix=line_prefix,
            indent=indent,
            wrap=wrap,
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
        node["language"] = language_name
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
