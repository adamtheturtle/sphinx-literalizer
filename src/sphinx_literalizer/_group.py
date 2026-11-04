"""Explicit, document-local grouping of generated preambles."""

from contextvars import ContextVar
from dataclasses import dataclass, fields, replace
from typing import ClassVar, override

from beartype import beartype
from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import IdentifierCase, Language, ValueInput
from sphinx.util.docutils import SphinxDirective

from ._support import _DirectiveError, _OptionValidator

__all__ = (
    "_CURRENT_REFERENCES",
    "LiteralizerGroupDirective",
    "_GeneratedFragment",
)


@dataclass(frozen=True)
class _ReferenceBinding:
    """An actual declaration and the options that produced it."""

    name: str
    value: ValueInput
    language: Language


@dataclass
class _ReferenceScope:
    """Binding knowledge confined to one explicitly opted-in group."""

    bindings: dict[str, _ReferenceBinding]

    def add(
        self,
        *,
        reference: str,
        name: str,
        value: ValueInput,
        language: Language,
    ) -> None:
        """Register one declaration, rejecting ambiguous names."""
        if reference in self.bindings or any(
            binding.name == name for binding in self.bindings.values()
        ):
            msg = f"Duplicate shared reference declaration '{reference}'."
            raise _DirectiveError(message=msg)
        self.bindings[reference] = _ReferenceBinding(
            name=name,
            value=value,
            language=language,
        )

    def values(self) -> dict[str, ValueInput]:
        """Return original source values keyed by raw reference name."""
        return {name: binding.value for name, binding in self.bindings.items()}

    def prepare_language(self, language: Language, /) -> Language:
        """Retain a common representation selected for prior bindings.

        A reference-only call may succeed with the language's natural
        strategy even though its declaration required a different one.
        Reuse actual declaration metadata when automatic selection is
        requested; validate all other constructor options afterwards.
        """
        bindings = tuple(self.bindings.values())
        if len(bindings) == 0 or any(
            type(binding.language) is not type(language)
            for binding in bindings
        ):
            return language
        strategies = {
            binding.language.heterogeneous_strategy for binding in bindings
        }
        if len(strategies) != 1:
            msg = (
                "Shared declarations require one explicit common "
                "heterogeneous strategy."
            )
            raise _DirectiveError(message=msg)
        return replace(
            language,
            heterogeneous_strategy=bindings[0].language.heterogeneous_strategy,
        )

    def validate(
        self,
        *,
        language: Language,
        ref_case: IdentifierCase | None,
    ) -> None:
        """Require the call to describe the actual emitted bindings.

        Constructor options are compared before any rendering caches.
        Call style affects invocation syntax rather than storage.
        Other differences are conservatively rejected: callers can use
        separate groups when they need different representations.
        """
        for reference, binding in self.bindings.items():
            name = (
                reference
                if ref_case is None
                else ref_case.convert(name=reference)
            )
            if name != binding.name:
                msg = (
                    f"Shared reference '{reference}' resolves to '{name}', "
                    f"but its declaration is named '{binding.name}'. "
                    "Use :reference-name: and matching :ref-case: options."
                )
                raise _DirectiveError(message=msg)
            if type(language) is not type(binding.language) or any(
                vars(language)[item.name] != vars(binding.language)[item.name]
                for item in fields(class_or_instance=language)
                if item.init and item.name != "call_style"
            ):
                msg = (
                    f"Shared reference '{reference}' uses different language "
                    "representation options. Use matching options on its "
                    "declaration and calls, including an explicit "
                    "heterogeneous strategy when auto selects different forms."
                )
                raise _DirectiveError(message=msg)


_CURRENT_REFERENCES: ContextVar[_ReferenceScope | None] = ContextVar(
    "literalizer_group_references",
    default=None,
)


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
    Repeated generated entries are removed as whole entries, never as
    individual lines inside a helper declaration.

    ``:share-references:`` additionally supplies earlier generated
    declarations' source values to calls in this group. No names are
    inferred from handwritten code or shared with other groups.
    """

    required_arguments = 1
    has_content = True
    option_spec: ClassVar[dict[str, _OptionValidator] | None] = {
        "share-references": directives.flag,
    }

    @override
    def run(self) -> list[nodes.Node]:
        """Parse the children and gather their generated preambles."""
        if _CURRENT_REFERENCES.get() is not None:
            msg = "literalizer-group cannot be nested."
            raise self.error(message=msg)
        container = nodes.container()
        scope = (
            _ReferenceScope(bindings={})
            if "share-references" in self.options
            else None
        )
        token = _CURRENT_REFERENCES.set(scope)
        try:
            _ = self.state.nested_parse(
                block=self.content,
                input_offset=self.content_offset,
                node=container,
            )
        finally:
            _CURRENT_REFERENCES.reset(token)
        language = self.arguments[0]
        if any(
            isinstance(child, nodes.system_message)
            for child in container.children
        ):
            return list(container.children)
        blocks = self._validate_blocks(
            children=container.children, language=language
        )
        preamble: dict[str, None] = {}
        helper_blocks: set[tuple[str, ...]] = set()
        for child in blocks:
            fragment = child.get(key="literalizer_fragment")
            if not isinstance(fragment, _GeneratedFragment):
                continue
            for entry in fragment.preamble:
                preamble[entry] = None
            # C++ selects headers from each input's inferred types. These
            # imports can differ without introducing conflicting helpers.
            helpers = tuple(
                entry
                for entry in fragment.data_dependent_preamble
                if not (language == "cpp" and entry.startswith("#include "))
            )
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

    def _validate_blocks(
        self, *, children: list[nodes.Node], language: str
    ) -> list[nodes.Element]:
        """Require code in one language, allowing blank line
        separators.
        """
        blocks: list[nodes.Element] = []
        for child in children:
            if isinstance(child, nodes.line_block) and child.astext() == "":
                blocks.append(child)
                continue
            if not isinstance(child, nodes.literal_block):
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
        return blocks

    @staticmethod
    def _strip_preambles(*, blocks: list[nodes.Element]) -> list[nodes.Node]:
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
