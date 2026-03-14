"""Sphinx extension for literalizer.

Provides the ``literalizer`` directive, which reads a JSON file and
renders it as a native language literal block.
"""

import json
from pathlib import Path
from typing import ClassVar

from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import convert_json_to_native_literal
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata


class LiteralizerDirective(SphinxDirective):
    """Directive that converts a JSON file to a native literal block.

    Usage::

        .. literalizer:: path/to/data.json
           :language: py
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
    }

    def run(self) -> list[nodes.Node]:
        """Read the JSON file and produce a literal block."""
        env = self.state.document.settings.env
        rel_path = self.arguments[0]
        source_dir = Path(env.srcdir)
        json_path = (source_dir / rel_path).resolve()

        env.note_dependency(str(json_path))

        data = json.loads(json_path.read_text(encoding="utf-8"))

        language: str = self.options["language"]
        prefix_count: int = self.options.get("prefix", 0)
        prefix_char_name: str = self.options.get("prefix-char", "spaces")
        prefix_char = "\t" if prefix_char_name == "tabs" else " "
        prefix = prefix_char * prefix_count
        wrap: bool = "wrap" in self.options

        text = convert_json_to_native_literal(
            data=data,
            language=language,
            prefix=prefix,
            wrap=wrap,
        )

        node = nodes.literal_block(text=text, source=rel_path)
        node["language"] = language
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
