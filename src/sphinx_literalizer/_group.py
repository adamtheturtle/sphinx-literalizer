"""Explicit, document-local grouping of generated preambles."""

from dataclasses import dataclass
from typing import override

from beartype import beartype
from docutils import nodes
from sphinx.util.docutils import SphinxDirective

__all__ = ("LiteralizerGroupDirective", "_GeneratedFragment")


@dataclass(frozen=True)
class _GeneratedFragment:
    """Requested file-scope entries and the code they support."""

    preamble: tuple[str, ...]
    data_dependent_preamble: tuple[str, ...]
    code: str


@beartype
class LiteralizerGroupDirective(SphinxDirective):
    """Hoist requested preambles before a group of code fragments.

    The argument is the Pygments language of the nested code blocks.
    Identical generated entries are deduplicated as whole entries, never
    as individual lines inside a helper declaration.
    """

    required_arguments = 1
    has_content = True

    @override
    def run(self) -> list[nodes.Node]:
        """Parse the children and gather their generated preambles."""
        container = nodes.container()
        _ = self.state.nested_parse(
            block=self.content,
            input_offset=self.content_offset,
            node=container,
        )
        language = self.arguments[0]
        preamble: dict[str, None] = {}
        helper_blocks: set[tuple[str, ...]] = set()
        blocks: list[nodes.literal_block] = []
        for child in container.children:
            if not isinstance(child, nodes.literal_block):
                if isinstance(child, nodes.system_message):
                    return list(container.children)
                msg = "literalizer-group accepts only code directives."
                raise self.error(message=msg)
            if child.get(key="literalizer_group", failobj=False):
                msg = "literalizer-group cannot be nested."
                raise self.error(message=msg)
            if child.get(key="language", failobj="text") != language:
                msg = (
                    "Every code block in literalizer-group must use "
                    f"language '{language}'."
                )
                raise self.error(message=msg)
            blocks.append(child)
            fragment = child.get(key="literalizer_fragment")
            if not isinstance(fragment, _GeneratedFragment):
                continue
            for entry in fragment.preamble:
                preamble[entry] = None
            helpers = fragment.data_dependent_preamble
            if len(helpers) > 0:
                helper_blocks.add(helpers)
        if len(helper_blocks) > 1:
            msg = (
                "literalizer-group cannot reconcile different generated "
                "helper declarations. Use separate groups."
            )
            raise self.error(message=msg)

        result: list[nodes.Node] = []
        if len(preamble) > 0:
            text = "\n".join(preamble)
            header = nodes.literal_block(text, text, language=language)
            self.set_source_info(node=header)
            header["literalizer_group"] = True
            result.append(header)
        result.extend(self._strip_preambles(blocks=blocks))
        return result

    @staticmethod
    def _strip_preambles(
        *, blocks: list[nodes.literal_block]
    ) -> list[nodes.Node]:
        """Retain source information while replacing grouped block
        text.
        """
        result: list[nodes.Node] = []
        for child in blocks:
            fragment = child.get(key="literalizer_fragment")
            if isinstance(fragment, _GeneratedFragment):
                code = fragment.code
                child.rawsource = code
                child.clear()
                child.append(item=nodes.Text(data=code))
                if code == "":
                    continue
            child["literalizer_group"] = True
            result.append(child)
        return result
