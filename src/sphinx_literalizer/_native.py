"""Declarative native invocation rendering through Literalizer."""

import json
from pathlib import Path
from typing import ClassVar, override

from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import (
    ExistingVariable,
    Language,
    LiteralizeResult,
    NewVariable,
    literalize_invocations,
)

from ._base import _BaseLiteralizerDirective
from ._group import _GeneratedFragment
from ._support import (
    _COMMON_OPTIONS,
    _EMITTER_OPTIONS,
    _FORMAT_OPTION_GETTERS,
    _common_option_args,
    _CommonOptions,
    _DirectiveError,
    _is_string_object_dict,
    _language_types,
    _OptionValidator,
)


def _native_binding(
    options: _CommonOptions, /
) -> NewVariable | ExistingVariable | None:
    """Resolve a native result binding from the common directive
    options.
    """
    if options.variable_name is None:
        if options.existing_variable:
            raise _DirectiveError(
                message="':existing-variable:' requires ':variable-name:'"
            )
        return None
    if options.existing_variable:
        return ExistingVariable(name=options.variable_name)
    return NewVariable(name=options.variable_name, modifiers=frozenset())


class LiteralizerInvocationDirective(_BaseLiteralizerDirective):
    """Render source rows with a structured, typed invocation recipe."""

    supports_initial_column: ClassVar[bool] = True

    option_spec: ClassVar[dict[str, _OptionValidator] | None] = {
        **{
            name: validator
            for name, validator in _COMMON_OPTIONS.items()
            if name
            in {
                *_FORMAT_OPTION_GETTERS,
                *_EMITTER_OPTIONS,
                "language",
                "input-format",
                "pre-indent-level",
                "indent",
                "indent-char",
                "include-preamble",
                "preamble-only",
                "skip-if-unrepresentable",
                "initial-column",
            }
        },
        "invocation-file": directives.unchanged_required,
        "per-element": directives.flag,
        "zip-file": directives.unchanged_required,
        "zip-input-format": directives.unchanged_required,
        "variable-name": directives.unchanged_required,
        "existing-variable": directives.flag,
    }

    def _read(self, name: str, /) -> tuple[Path, str]:
        """Resolve a document-relative path and track every dependency."""
        _, filename = self.env.relfn2path(filename=name)
        path = Path(filename)
        self.env.note_dependency(filename=str(object=path))
        try:
            return path, path.read_text(encoding="utf-8")
        except OSError as exc:
            message = (
                f"Cannot read native invocation dependency {name!r}: {exc}"
            )
            raise _DirectiveError(message=message) from exc

    @override
    def _run(self) -> list[nodes.Node]:
        """Delegate parsing, native syntax, typing, and boxing
        upstream.
        """
        options = _CommonOptions(
            **_common_option_args(
                options=self._options_with_language_defaults()
            )
        )
        recipe_name = self.options.get("invocation-file")
        if recipe_name is None:
            raise _DirectiveError(message="':invocation-file:' is required")
        data_path, source = self._read(self.arguments[0])
        recipe_path, recipe_source = self._read(recipe_name)
        try:
            recipe = json.loads(s=recipe_source)
        except json.JSONDecodeError as exc:
            raise _DirectiveError(
                message=f"{recipe_path}:{exc.lineno}:{exc.colno}: {exc.msg}"
            ) from exc
        if not _is_string_object_dict(recipe):
            raise _DirectiveError(
                message="Native invocation recipe must be a JSON object"
            )
        language_cls = _language_types()[options.language]
        variable_form = _native_binding(options)
        zip_source = None
        zip_format = None
        zip_name = self.options.get("zip-file")
        if zip_name is not None:
            zip_path, zip_source = self._read(zip_name)
            zip_format = self._resolve_format(
                data_path=zip_path,
                explicit=self.options.get("zip-input-format"),
                option_name="zip-input-format",
            )
        elif "zip-input-format" in self.options:
            raise _DirectiveError(
                message="':zip-input-format:' requires ':zip-file:'"
            )
        input_format = self._resolve_input_format(
            data_path=data_path, options=options
        )

        def render(language: Language) -> LiteralizeResult:
            """Render one complete native expression per source row."""
            return literalize_invocations(
                source=source,
                input_format=input_format,
                language=language,
                invocation=recipe,
                per_element="per-element" in self.options,
                zip_source=zip_source,
                zip_input_format=zip_format,
                variable_form=variable_form,
                pre_indent_level=options.pre_indent_level,
                initial_column=options.initial_column,
            )

        rendered = self._render_with_strategy(
            language_name=options.language,
            language_cls=language_cls,
            render=render,
            prepare_language=lambda spec: spec,
            options=options,
        )
        if rendered is None:
            return []
        result, _ = rendered
        include_preamble = options.include_preamble or options.preamble_only
        code = "" if options.preamble_only else result.code
        preamble = result.preamble if include_preamble else ()
        text = "\n\n".join(
            part for part in ("\n".join(preamble), code) if part != ""
        )
        return self._make_node(
            text=text,
            data_path=data_path,
            language_cls=language_cls,
            fragment=_GeneratedFragment(
                preamble=preamble,
                data_dependent_preamble=result.data_dependent_preamble
                if include_preamble
                else (),
                code=code,
            ),
        )
