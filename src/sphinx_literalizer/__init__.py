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
    Cpp,
    Crystal,
    CSharp,
    D,
    Dart,
    Elixir,
    Erlang,
    FSharp,
    Go,
    Groovy,
    Haskell,
    Java,
    JavaScript,
    Julia,
    Kotlin,
    Lua,
    Matlab,
    Nim,
    OCaml,
    Occam,
    Perl,
    Php,
    PowerShell,
    Python,
    R,
    Ruby,
    Rust,
    Scala,
    Swift,
    TypeScript,
    Zig,
)
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata

_LANGUAGE_TYPES: dict[str, Any] = {
    "ada": Ada,
    "bash": Bash,
    "c": C,
    "clojure": Clojure,
    "cpp": Cpp,
    "crystal": Crystal,
    "csharp": CSharp,
    "d": D,
    "dart": Dart,
    "elixir": Elixir,
    "erlang": Erlang,
    "fsharp": FSharp,
    "go": Go,
    "groovy": Groovy,
    "haskell": Haskell,
    "java": Java,
    "javascript": JavaScript,
    "julia": Julia,
    "kotlin": Kotlin,
    "lua": Lua,
    "matlab": Matlab,
    "nim": Nim,
    "ocaml": OCaml,
    "occam": Occam,
    "perl": Perl,
    "php": Php,
    "powershell": PowerShell,
    "python": Python,
    "r": R,
    "ruby": Ruby,
    "rust": Rust,
    "scala": Scala,
    "swift": Swift,
    "typescript": TypeScript,
    "zig": Zig,
}

_DATE_FORMAT_KWARGS: dict[str, dict[str, str]] = {
    "cpp": {"date_format": "cpp", "datetime_format": "cpp"},
    "csharp": {"date_format": "csharp", "datetime_format": "csharp"},
    "dart": {"date_format": "dart", "datetime_format": "dart"},
    "epoch": {"datetime_format": "epoch"},
    "go": {"date_format": "go", "datetime_format": "go"},
    "iso": {},
    "java-instant": {"date_format": "java", "datetime_format": "instant"},
    "java-zoned": {"date_format": "java", "datetime_format": "zoned"},
    "javascript": {"date_format": "js", "datetime_format": "js"},
    "julia": {"date_format": "julia", "datetime_format": "julia"},
    "kotlin": {"date_format": "kotlin", "datetime_format": "kotlin"},
    "python": {"date_format": "python", "datetime_format": "python"},
    "r": {"date_format": "r", "datetime_format": "r"},
    "ruby": {"date_format": "ruby", "datetime_format": "ruby"},
    "rust": {"date_format": "rust", "datetime_format": "rust"},
    "typescript": {"date_format": "js", "datetime_format": "js"},
}


class LiteralizerDirective(SphinxDirective):
    """Directive that converts a JSON file to a native literal block.

    Usage::

        .. literalizer:: path/to/data.json
           :language: python
           :prefix: 8
           :prefix-char: spaces
           :wrap:
           :variable-name: my_var
           :existing-variable:
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
            values=tuple(_DATE_FORMAT_KWARGS),
        ),
        "variable-name": directives.unchanged,
        "existing-variable": directives.flag,
    }

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce a literal block."""
        env = self.state.document.settings.env
        rel_path = self.arguments[0]
        source_dir = Path(env.srcdir)
        data_path = (source_dir / rel_path).resolve()

        env.note_dependency(str(object=data_path))

        language_name: str = self.options["language"]
        date_format_name: str | None = self.options.get("date-format")
        if date_format_name is not None:
            date_format_kwargs = _DATE_FORMAT_KWARGS[date_format_name]
        else:
            date_format_kwargs = {}
        language_spec: Language = _LANGUAGE_TYPES[language_name](
            **date_format_kwargs
        )
        prefix_count: int = self.options.get("prefix", 0)
        prefix_char_name: str = self.options.get("prefix-char", "spaces")
        prefix_char = "\t" if prefix_char_name == "tabs" else " "
        prefix = prefix_char * prefix_count
        wrap: bool = "wrap" in self.options
        variable_name: str | None = self.options.get("variable-name")
        existing_variable: bool = "existing-variable" in self.options

        # YAML is a superset of JSON, so literalize_yaml handles both
        # .yaml/.yml files and .json files without any format detection.
        text = literalize_yaml(
            yaml_string=data_path.read_text(encoding="utf-8"),
            language=language_spec,
            prefix=prefix,
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
