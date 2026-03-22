"""Sphinx extension for literalizer.

Provides the ``literalizer`` directive, which reads a JSON file and
renders it as a native language literal block.
"""

from collections.abc import Callable
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
from sphinx.errors import ExtensionError
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


_DATE_FORMATS: dict[tuple[str, str], object] = {
    (lang_name, member.name.lower()): member
    for lang_name, lang_cls in _LANGUAGE_TYPES.items()
    for member in lang_cls.date_formats
}

_DATE_FORMAT_VALUES: tuple[str, ...] = tuple(
    sorted({fmt_value for _, fmt_value in _DATE_FORMATS})
)

_DATETIME_FORMATS: dict[tuple[str, str], object] = {
    (lang_name, member.name.lower()): member
    for lang_name, lang_cls in _LANGUAGE_TYPES.items()
    for member in lang_cls.datetime_formats
}

_DATETIME_FORMAT_VALUES: tuple[str, ...] = tuple(
    sorted({fmt_value for _, fmt_value in _DATETIME_FORMATS})
)

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

_COMMENT_FORMATS: dict[tuple[str, str], object] = {
    (lang_name, member.name.lower()): member
    for lang_name, lang_cls in _LANGUAGE_TYPES.items()
    for member in lang_cls.CommentFormats
}

_COMMENT_FORMAT_VALUES: tuple[str, ...] = tuple(
    sorted({fmt_value for _, fmt_value in _COMMENT_FORMATS})
)


@beartype
def _apply_format_option(
    constructor: partial[Language],
    language_name: str,
    format_name: str,
    format_value: str,
    formats: dict[tuple[str, str], object],
) -> partial[Language]:
    """Look up a format enum member and apply it to the constructor."""
    try:
        fmt = formats[(language_name, format_value)]
    except KeyError:
        msg = (
            f"Language '{language_name}' does not support "
            f"{format_name} '{format_value}'."
        )
        raise ExtensionError(message=msg) from None
    return partial(constructor, **{format_name.replace("-", "_"): fmt})


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
           :date-format: python
           :datetime-format: python
           :variable-name: my_var
           :existing-variable:
           :sequence-format: list
           :set-format: frozenset
           :bytes-format: python
           :comment-format: block
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
            values=_DATE_FORMAT_VALUES,
        ),
        "datetime-format": lambda x: directives.choice(
            argument=x,
            values=_DATETIME_FORMAT_VALUES,
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
        "comment-format": lambda x: directives.choice(
            argument=x,
            values=_COMMENT_FORMAT_VALUES,
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

        format_options: tuple[
            tuple[str, dict[tuple[str, str], object]], ...
        ] = (
            ("date-format", _DATE_FORMATS),
            ("datetime-format", _DATETIME_FORMATS),
            ("sequence-format", _SEQUENCE_FORMATS),
            ("set-format", _SET_FORMATS),
            ("bytes-format", _BYTES_FORMATS),
            ("comment-format", _COMMENT_FORMATS),
        )
        for format_name, formats in format_options:
            format_value: str | None = self.options.get(format_name)
            if format_value is not None:
                constructor = _apply_format_option(
                    constructor=constructor,
                    language_name=language_name,
                    format_name=format_name,
                    format_value=format_value,
                    formats=formats,
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
