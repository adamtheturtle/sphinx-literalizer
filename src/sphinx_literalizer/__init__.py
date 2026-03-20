"""Sphinx extension for literalizer.

Provides the ``literalizer`` directive, which reads a JSON file and
renders it as a native language literal block.
"""

from collections.abc import Callable
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

_DEFAULT_DATE_FORMAT_KWARGS: dict[str, dict[str, Any]] = {
    "cpp": {
        "date_format": Cpp.DateFormat.ISO,
        "datetime_format": Cpp.DatetimeFormat.ISO,
    },
    "csharp": {
        "date_format": CSharp.DateFormat.ISO,
        "datetime_format": CSharp.DatetimeFormat.ISO,
    },
    "dart": {
        "date_format": Dart.DateFormat.ISO,
        "datetime_format": Dart.DatetimeFormat.ISO,
    },
    "go": {
        "date_format": Go.DateFormat.ISO,
        "datetime_format": Go.DatetimeFormat.ISO,
    },
    "java": {
        "date_format": Java.DateFormat.ISO,
        "datetime_format": Java.DatetimeFormat.ISO,
    },
    "javascript": {
        "date_format": JavaScript.DateFormat.ISO,
        "datetime_format": JavaScript.DatetimeFormat.ISO,
    },
    "julia": {
        "date_format": Julia.DateFormat.ISO,
        "datetime_format": Julia.DatetimeFormat.ISO,
    },
    "kotlin": {
        "date_format": Kotlin.DateFormat.ISO,
        "datetime_format": Kotlin.DatetimeFormat.ISO,
    },
    "python": {
        "date_format": Python.DateFormat.ISO,
        "datetime_format": Python.DatetimeFormat.ISO,
    },
    "r": {
        "date_format": R.DateFormat.ISO,
        "datetime_format": R.DatetimeFormat.ISO,
    },
    "ruby": {
        "date_format": Ruby.DateFormat.ISO,
        "datetime_format": Ruby.DatetimeFormat.ISO,
    },
    "rust": {
        "date_format": Rust.DateFormat.ISO,
        "datetime_format": Rust.DatetimeFormat.ISO,
    },
    "typescript": {
        "date_format": TypeScript.DateFormat.ISO,
        "datetime_format": TypeScript.DatetimeFormat.ISO,
    },
}

_DATE_FORMAT_KWARGS: dict[str, dict[str, Any]] = {
    "cpp": {
        "date_format": Cpp.DateFormat.CPP,
        "datetime_format": Cpp.DatetimeFormat.CPP,
    },
    "csharp": {
        "date_format": CSharp.DateFormat.CSHARP,
        "datetime_format": CSharp.DatetimeFormat.CSHARP,
    },
    "dart": {
        "date_format": Dart.DateFormat.DART,
        "datetime_format": Dart.DatetimeFormat.DART,
    },
    "epoch": {"datetime_format": Python.DatetimeFormat.EPOCH},
    "go": {
        "date_format": Go.DateFormat.GO,
        "datetime_format": Go.DatetimeFormat.GO,
    },
    "iso": {},
    "java-instant": {
        "date_format": Java.DateFormat.JAVA,
        "datetime_format": Java.DatetimeFormat.INSTANT,
    },
    "java-zoned": {
        "date_format": Java.DateFormat.JAVA,
        "datetime_format": Java.DatetimeFormat.ZONED,
    },
    "javascript": {
        "date_format": JavaScript.DateFormat.JS,
        "datetime_format": JavaScript.DatetimeFormat.JS,
    },
    "julia": {
        "date_format": Julia.DateFormat.JULIA,
        "datetime_format": Julia.DatetimeFormat.JULIA,
    },
    "kotlin": {
        "date_format": Kotlin.DateFormat.KOTLIN,
        "datetime_format": Kotlin.DatetimeFormat.KOTLIN,
    },
    "python": {
        "date_format": Python.DateFormat.PYTHON,
        "datetime_format": Python.DatetimeFormat.PYTHON,
    },
    "r": {
        "date_format": R.DateFormat.R,
        "datetime_format": R.DatetimeFormat.R,
    },
    "ruby": {
        "date_format": Ruby.DateFormat.RUBY,
        "datetime_format": Ruby.DatetimeFormat.RUBY,
    },
    "rust": {
        "date_format": Rust.DateFormat.RUST,
        "datetime_format": Rust.DatetimeFormat.RUST,
    },
    "typescript": {
        "date_format": TypeScript.DateFormat.JS,
        "datetime_format": TypeScript.DatetimeFormat.JS,
    },
}

_DEFAULT_EXTRA_KWARGS: dict[str, dict[str, Any]] = {
    "python": {
        "bytes_format": Python.BytesFormat.HEX,
        "set_format": Python.SetFormat.SET,
        "variable_type_hints": Python.VariableTypeHints.NONE,
    },
    "r": {
        "empty_dict_key": R.EmptyDictKey.ERROR,
    },
}

_DEFAULT_SEQUENCE_FORMAT_KWARGS: dict[str, dict[str, Any]] = {
    "ada": {"sequence_format": Ada.SequenceFormat.LIST},
    "bash": {"sequence_format": Bash.SequenceFormat.ARRAY},
    "c": {"sequence_format": C.SequenceFormat.ARRAY},
    "clojure": {"sequence_format": Clojure.SequenceFormat.VECTOR},
    "cobol": {"sequence_format": Cobol.SequenceFormat.SEQUENCE},
    "common-lisp": {
        "sequence_format": CommonLisp.SequenceFormat.LIST,
    },
    "cpp": {
        "sequence_format": Cpp.SequenceFormat.INITIALIZER_LIST,
    },
    "crystal": {"sequence_format": Crystal.SequenceFormat.ARRAY},
    "csharp": {"sequence_format": CSharp.SequenceFormat.ARRAY},
    "d": {"sequence_format": D.SequenceFormat.ARRAY},
    "dart": {"sequence_format": Dart.SequenceFormat.LIST},
    "elixir": {"sequence_format": Elixir.SequenceFormat.LIST},
    "erlang": {"sequence_format": Erlang.SequenceFormat.LIST},
    "fortran": {"sequence_format": Fortran.SequenceFormat.LIST},
    "fsharp": {"sequence_format": FSharp.SequenceFormat.LIST},
    "go": {"sequence_format": Go.SequenceFormat.SLICE},
    "groovy": {"sequence_format": Groovy.SequenceFormat.LIST},
    "haskell": {"sequence_format": Haskell.SequenceFormat.LIST},
    "hcl": {"sequence_format": Hcl.SequenceFormat.LIST},
    "java": {"sequence_format": Java.SequenceFormat.ARRAY},
    "javascript": {
        "sequence_format": JavaScript.SequenceFormat.ARRAY,
    },
    "julia": {"sequence_format": Julia.SequenceFormat.ARRAY},
    "kotlin": {"sequence_format": Kotlin.SequenceFormat.LIST},
    "lua": {"sequence_format": Lua.SequenceFormat.TABLE},
    "matlab": {"sequence_format": Matlab.SequenceFormat.CELL_ARRAY},
    "mojo": {"sequence_format": Mojo.SequenceFormat.LIST},
    "nim": {"sequence_format": Nim.SequenceFormat.ARRAY},
    "norg": {"sequence_format": Norg.SequenceFormat.ARRAY},
    "objective-c": {
        "sequence_format": ObjectiveC.SequenceFormat.ARRAY,
    },
    "ocaml": {"sequence_format": OCaml.SequenceFormat.LIST},
    "occam": {"sequence_format": Occam.SequenceFormat.LIST},
    "perl": {"sequence_format": Perl.SequenceFormat.ARRAY},
    "php": {"sequence_format": Php.SequenceFormat.ARRAY},
    "powershell": {
        "sequence_format": PowerShell.SequenceFormat.ARRAY,
    },
    "python": {"sequence_format": Python.SequenceFormat.TUPLE},
    "r": {"sequence_format": R.SequenceFormat.LIST},
    "racket": {"sequence_format": Racket.SequenceFormat.LIST},
    "ruby": {"sequence_format": Ruby.SequenceFormat.ARRAY},
    "rust": {"sequence_format": Rust.SequenceFormat.VEC},
    "scala": {"sequence_format": Scala.SequenceFormat.LIST},
    "swift": {"sequence_format": Swift.SequenceFormat.ARRAY},
    "toml": {"sequence_format": Toml.SequenceFormat.ARRAY},
    "typescript": {
        "sequence_format": TypeScript.SequenceFormat.ARRAY,
    },
    "visual-basic": {
        "sequence_format": VisualBasic.SequenceFormat.ARRAY,
    },
    "yaml": {"sequence_format": Yaml.SequenceFormat.SEQUENCE},
    "zig": {"sequence_format": Zig.SequenceFormat.ARRAY},
}

_SEQUENCE_FORMAT_KWARGS: dict[
    tuple[str, str],
    dict[str, Any],
] = {
    ("crystal", "array"): {
        "sequence_format": Crystal.SequenceFormat.ARRAY,
    },
    ("crystal", "tuple"): {
        "sequence_format": Crystal.SequenceFormat.TUPLE,
    },
    ("elixir", "list"): {
        "sequence_format": Elixir.SequenceFormat.LIST,
    },
    ("elixir", "tuple"): {
        "sequence_format": Elixir.SequenceFormat.TUPLE,
    },
    ("erlang", "list"): {
        "sequence_format": Erlang.SequenceFormat.LIST,
    },
    ("erlang", "tuple"): {
        "sequence_format": Erlang.SequenceFormat.TUPLE,
    },
    ("julia", "array"): {
        "sequence_format": Julia.SequenceFormat.ARRAY,
    },
    ("julia", "tuple"): {
        "sequence_format": Julia.SequenceFormat.TUPLE,
    },
    ("python", "list"): {
        "sequence_format": Python.SequenceFormat.LIST,
    },
    ("python", "tuple"): {
        "sequence_format": Python.SequenceFormat.TUPLE,
    },
    ("rust", "array"): {
        "sequence_format": Rust.SequenceFormat.ARRAY,
    },
    ("rust", "tuple"): {
        "sequence_format": Rust.SequenceFormat.TUPLE,
    },
    ("rust", "vec"): {
        "sequence_format": Rust.SequenceFormat.VEC,
    },
}

_SEQUENCE_FORMAT_VALUES: tuple[str, ...] = (
    "array",
    "cell_array",
    "initializer_list",
    "list",
    "sequence",
    "slice",
    "table",
    "tuple",
    "vec",
    "vector",
)

_SET_FORMAT_KWARGS: dict[tuple[str, str], dict[str, Any]] = {
    ("python", "frozenset"): {
        "set_format": Python.SetFormat.FROZENSET,
    },
    ("python", "set"): {
        "set_format": Python.SetFormat.SET,
    },
}

_SET_FORMAT_VALUES: tuple[str, ...] = (
    "frozenset",
    "set",
)

_BYTES_FORMAT_KWARGS: dict[tuple[str, str], dict[str, Any]] = {
    ("python", "hex"): {
        "bytes_format": Python.BytesFormat.HEX,
    },
    ("python", "python"): {
        "bytes_format": Python.BytesFormat.PYTHON,
    },
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
            values=tuple(_DATE_FORMAT_KWARGS),
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
        format_kwargs: dict[str, Any] = {}

        format_kwargs.update(_DEFAULT_SEQUENCE_FORMAT_KWARGS[language_name])

        default_date_kwargs = _DEFAULT_DATE_FORMAT_KWARGS.get(
            language_name,
        )
        if default_date_kwargs is not None:
            format_kwargs.update(default_date_kwargs)

        default_extra_kwargs = _DEFAULT_EXTRA_KWARGS.get(
            language_name,
        )
        if default_extra_kwargs is not None:
            format_kwargs.update(default_extra_kwargs)

        date_format_name: str | None = self.options.get("date-format")
        if date_format_name is not None:
            format_kwargs.update(_DATE_FORMAT_KWARGS[date_format_name])

        seq_fmt: str | None = self.options.get("sequence-format")
        if seq_fmt is not None:
            format_kwargs.update(
                _SEQUENCE_FORMAT_KWARGS[(language_name, seq_fmt)]
            )

        set_fmt: str | None = self.options.get("set-format")
        if set_fmt is not None:
            format_kwargs.update(_SET_FORMAT_KWARGS[(language_name, set_fmt)])

        bytes_fmt: str | None = self.options.get("bytes-format")
        if bytes_fmt is not None:
            format_kwargs.update(
                _BYTES_FORMAT_KWARGS[(language_name, bytes_fmt)]
            )

        language_spec: Language = language_cls(**format_kwargs)
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
