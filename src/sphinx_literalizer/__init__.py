"""Sphinx extension for literalizer.

Provides the ``literalizer`` directive, which reads a JSON file and
renders it as a native language literal block.
"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import Language, literalize_yaml
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

_LANGUAGE_TYPES: dict[str, type[Language]] = {
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


@dataclass(frozen=True)
class _DateFormats:
    """Date and datetime format options for a language."""

    date_format: object | None = None
    datetime_format: object | None = None


_DATE_FORMATS: dict[str, _DateFormats] = {
    "cpp": _DateFormats(
        date_format=Cpp.DateFormat.CPP,
        datetime_format=Cpp.DatetimeFormat.CPP,
    ),
    "csharp": _DateFormats(
        date_format=CSharp.DateFormat.CSHARP,
        datetime_format=CSharp.DatetimeFormat.CSHARP,
    ),
    "dart": _DateFormats(
        date_format=Dart.DateFormat.DART,
        datetime_format=Dart.DatetimeFormat.DART,
    ),
    "epoch": _DateFormats(datetime_format=Python.DatetimeFormat.EPOCH),
    "go": _DateFormats(
        date_format=Go.DateFormat.GO,
        datetime_format=Go.DatetimeFormat.GO,
    ),
    "iso": _DateFormats(),
    "java-instant": _DateFormats(
        date_format=Java.DateFormat.JAVA,
        datetime_format=Java.DatetimeFormat.INSTANT,
    ),
    "java-zoned": _DateFormats(
        date_format=Java.DateFormat.JAVA,
        datetime_format=Java.DatetimeFormat.ZONED,
    ),
    "javascript": _DateFormats(
        date_format=JavaScript.DateFormat.JS,
        datetime_format=JavaScript.DatetimeFormat.JS,
    ),
    "julia": _DateFormats(
        date_format=Julia.DateFormat.JULIA,
        datetime_format=Julia.DatetimeFormat.JULIA,
    ),
    "kotlin": _DateFormats(
        date_format=Kotlin.DateFormat.KOTLIN,
        datetime_format=Kotlin.DatetimeFormat.KOTLIN,
    ),
    "python": _DateFormats(
        date_format=Python.DateFormat.PYTHON,
        datetime_format=Python.DatetimeFormat.PYTHON,
    ),
    "r": _DateFormats(
        date_format=R.DateFormat.R,
        datetime_format=R.DatetimeFormat.R,
    ),
    "ruby": _DateFormats(
        date_format=Ruby.DateFormat.RUBY,
        datetime_format=Ruby.DatetimeFormat.RUBY,
    ),
    "rust": _DateFormats(
        date_format=Rust.DateFormat.RUST,
        datetime_format=Rust.DatetimeFormat.RUST,
    ),
    "typescript": _DateFormats(
        date_format=TypeScript.DateFormat.JS,
        datetime_format=TypeScript.DatetimeFormat.JS,
    ),
}

_DEFAULT_SEQUENCE_FORMATS: dict[str, object] = {
    "ada": Ada.SequenceFormat.LIST,
    "bash": Bash.SequenceFormat.ARRAY,
    "c": C.SequenceFormat.ARRAY,
    "clojure": Clojure.SequenceFormat.VECTOR,
    "cobol": Cobol.SequenceFormat.SEQUENCE,
    "common-lisp": CommonLisp.SequenceFormat.LIST,
    "cpp": Cpp.SequenceFormat.INITIALIZER_LIST,
    "crystal": Crystal.SequenceFormat.ARRAY,
    "csharp": CSharp.SequenceFormat.ARRAY,
    "d": D.SequenceFormat.ARRAY,
    "dart": Dart.SequenceFormat.LIST,
    "elixir": Elixir.SequenceFormat.LIST,
    "erlang": Erlang.SequenceFormat.LIST,
    "fortran": Fortran.SequenceFormat.LIST,
    "fsharp": FSharp.SequenceFormat.LIST,
    "go": Go.SequenceFormat.SLICE,
    "groovy": Groovy.SequenceFormat.LIST,
    "haskell": Haskell.SequenceFormat.LIST,
    "hcl": Hcl.SequenceFormat.LIST,
    "java": Java.SequenceFormat.ARRAY,
    "javascript": JavaScript.SequenceFormat.ARRAY,
    "julia": Julia.SequenceFormat.ARRAY,
    "kotlin": Kotlin.SequenceFormat.LIST,
    "lua": Lua.SequenceFormat.TABLE,
    "matlab": Matlab.SequenceFormat.CELL_ARRAY,
    "mojo": Mojo.SequenceFormat.LIST,
    "nim": Nim.SequenceFormat.ARRAY,
    "norg": Norg.SequenceFormat.ARRAY,
    "objective-c": ObjectiveC.SequenceFormat.ARRAY,
    "ocaml": OCaml.SequenceFormat.LIST,
    "occam": Occam.SequenceFormat.LIST,
    "perl": Perl.SequenceFormat.ARRAY,
    "php": Php.SequenceFormat.ARRAY,
    "powershell": PowerShell.SequenceFormat.ARRAY,
    "python": Python.SequenceFormat.TUPLE,
    "r": R.SequenceFormat.LIST,
    "racket": Racket.SequenceFormat.LIST,
    "ruby": Ruby.SequenceFormat.ARRAY,
    "rust": Rust.SequenceFormat.VEC,
    "scala": Scala.SequenceFormat.LIST,
    "swift": Swift.SequenceFormat.ARRAY,
    "toml": Toml.SequenceFormat.ARRAY,
    "typescript": TypeScript.SequenceFormat.ARRAY,
    "visual-basic": VisualBasic.SequenceFormat.ARRAY,
    "yaml": Yaml.SequenceFormat.SEQUENCE,
    "zig": Zig.SequenceFormat.ARRAY,
}

_SEQUENCE_FORMATS: dict[tuple[str, str], object] = {
    ("crystal", "array"): Crystal.SequenceFormat.ARRAY,
    ("crystal", "tuple"): Crystal.SequenceFormat.TUPLE,
    ("elixir", "list"): Elixir.SequenceFormat.LIST,
    ("elixir", "tuple"): Elixir.SequenceFormat.TUPLE,
    ("erlang", "list"): Erlang.SequenceFormat.LIST,
    ("erlang", "tuple"): Erlang.SequenceFormat.TUPLE,
    ("julia", "array"): Julia.SequenceFormat.ARRAY,
    ("julia", "tuple"): Julia.SequenceFormat.TUPLE,
    ("python", "list"): Python.SequenceFormat.LIST,
    ("python", "tuple"): Python.SequenceFormat.TUPLE,
    ("rust", "array"): Rust.SequenceFormat.ARRAY,
    ("rust", "tuple"): Rust.SequenceFormat.TUPLE,
    ("rust", "vec"): Rust.SequenceFormat.VEC,
}

_SEQUENCE_FORMAT_VALUES: tuple[str, ...] = (
    "array",
    "list",
    "tuple",
    "vec",
)

_SET_FORMATS: dict[tuple[str, str], object] = {
    ("python", "frozenset"): Python.SetFormat.FROZENSET,
    ("python", "set"): Python.SetFormat.SET,
}

_SET_FORMAT_VALUES: tuple[str, ...] = (
    "frozenset",
    "set",
)

_BYTES_FORMATS: dict[tuple[str, str], object] = {
    ("python", "hex"): Python.BytesFormat.HEX,
    ("python", "python"): Python.BytesFormat.PYTHON,
}

_BYTES_FORMAT_VALUES: tuple[str, ...] = (
    "hex",
    "python",
)


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
        "language": directives.unchanged_required,
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
        language_cls = _LANGUAGE_TYPES[language_name]
        constructor = partial(language_cls)

        date_format_name: str | None = self.options.get("date-format")
        if date_format_name is not None:
            date_formats = _DATE_FORMATS[date_format_name]
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

        seq_fmt: str | None = self.options.get("sequence-format")
        if seq_fmt is not None:
            sequence_format = _SEQUENCE_FORMATS[(language_name, seq_fmt)]
        else:
            sequence_format = _DEFAULT_SEQUENCE_FORMATS[language_name]
        constructor = partial(
            constructor,
            sequence_format=sequence_format,
        )

        set_fmt: str | None = self.options.get("set-format")
        if set_fmt is not None:
            constructor = partial(
                constructor,
                set_format=_SET_FORMATS[(language_name, set_fmt)],
            )

        bytes_fmt: str | None = self.options.get("bytes-format")
        if bytes_fmt is not None:
            constructor = partial(
                constructor,
                bytes_format=_BYTES_FORMATS[(language_name, bytes_fmt)],
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
