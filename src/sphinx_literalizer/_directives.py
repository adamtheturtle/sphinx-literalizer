"""Concrete Sphinx directives provided by the extension."""

import re
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import ClassVar, override

from beartype import beartype
from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import (
    CallContext,
    InputFormat,
    Language,
    LiteralizeResult,
    literalize,
    literalize_call,
)
from literalizer.exceptions import (
    ParameterCountMismatchError,
)

from ._base import _BaseLiteralizerDirective
from ._support import (
    _COMMON_OPTIONS,
    _common_option_args,
    _DirectiveError,
    _language_types,
    _LiteralizerCallOptions,
    _LiteralizerOptions,
    _OptionValidator,
    _parse_record_null_substitutions,
    _substitute_placeholder,
)


@beartype
class LiteralizerDirective(_BaseLiteralizerDirective):
    """Directive that converts a data file to a native literal block.

    Usage::

        .. literalizer:: path/to/data.json
           :language: python
           :input-format: json
           :pre-indent-level: 2
           :indent: 4
           :indent-char: spaces
           :include-delimiters:
           :include-preamble:
           :preamble-only:
           :date-format: python
           :datetime-format: python
           :variable-name: my_var
           :existing-variable:
           :both-variable-forms:
           :sequence-format: list
           :set-format: frozenset
           :bytes-format: python
           :comment-format: block
           :variable-type-hints: always
           :declaration-style: const
           :dict-entry-style: rocket
           :dict-format: object
           :float-format: repr
           :integer-format: decimal
           :numeric-literal-suffix: none
           :numeric-separator: none
           :numeric-style: overloaded
           :string-format: double
           :trailing-comma: yes
           :language-version: py39
           :empty-dict-key: positional
           :heterogeneous-strategy: auto
           :json-type: serde_json_value
           :json-rendering: inline_document
           :record-map-value-typing: wide
           :bool-format: json_pp_ref
           :default-set-element-type: String
           :default-sequence-element-type: String
           :default-dict-key-type: String
           :default-dict-value-type: String
           :default-ordered-map-value-type: any
           :modifiers: public,static,final
           :module-name: MyModule
           :record-struct-name-prefix: Record
           :record-shape-names: x,y=Point; a,b,c=Vec3
           :heterogeneous-value-name: Value
           :record-null-substitutions: {"id": -1, "assignee": ""}
           :skip-if-unrepresentable:
           :wrap-in-file:
           :ref-case: camel
           :ref-key: $reference
           :collection-layout: multiline

    ``:heterogeneous-strategy: auto`` renders the input with its natural
    representation and, only if that raises because the data is
    heterogeneous, retries with each strategy the target language
    supports in the order configured by the
    ``literalizer_heterogeneous_strategy_precedence`` configuration value
    (default: ``record``, ``tuple``, ``tagged_enum``, ``object_variant``,
    ``variant``, ``union_type``, ``interface``).  This keeps homogeneous
    and genuinely map-shaped data in its native form while still
    representing record-shaped or mixed-scalar inputs.

    ``:skip-if-unrepresentable:`` makes the directive emit no node at all
    (instead of failing the build) when the input cannot be represented
    in the target language -- including after ``auto`` exhausts its
    precedence -- so a per-language loop can skip the languages a given
    input does not fit without leaking data-shape concerns into prose.
    """

    option_spec: ClassVar[dict[str, _OptionValidator] | None] = {
        **_COMMON_OPTIONS,
        "include-delimiters": directives.flag,
        "variable-name": directives.unchanged,
        "existing-variable": directives.flag,
        "both-variable-forms": directives.flag,
        "modifiers": directives.unchanged,
        "record-null-substitutions": directives.unchanged_required,
    }

    def _parse_options(self) -> _LiteralizerOptions:
        """Parse ``self.options`` into the typed options dataclass."""
        options = self._options_with_language_defaults()
        return _LiteralizerOptions(
            **_common_option_args(options=options),
            include_delimiters="include-delimiters" in self.options,
            both_variable_forms="both-variable-forms" in self.options,
            record_null_substitutions=(
                None
                if "record-null-substitutions" not in self.options
                else _parse_record_null_substitutions(
                    value=self.options["record-null-substitutions"],
                )
            ),
        )

    @override
    def _run(self) -> list[nodes.Node]:
        """Read the data file and produce a literal block."""
        options = self._parse_options()
        env = self.env
        data_path = (Path(env.srcdir) / self.arguments[0]).resolve()

        env.note_dependency(filename=str(object=data_path))

        language_name = options.language
        language_cls = _language_types()[language_name]

        pre_indent_level = options.pre_indent_level
        include_delimiters = options.include_delimiters
        include_preamble = options.include_preamble
        preamble_only = options.preamble_only
        variable_form = self._resolve_variable_form(
            language_cls=language_cls,
            options=options,
            both_variable_forms=options.both_variable_forms,
        )
        # literalizer 2026.8.16+ rejects variable forms without delimiters.
        if variable_form is not None:
            include_delimiters = True
        wrap_in_file = options.wrap_in_file
        # literalizer 2026.8.29+ rejects a wrapped file without
        # delimiters, which would present a bare collection fragment as a
        # complete source file.
        if wrap_in_file:
            include_delimiters = True
        ref_case, ref_key = self._resolve_ref_options(options=options)
        collection_layout = self._resolve_collection_layout(options=options)

        input_format = self._resolve_input_format(
            data_path=data_path,
            options=options,
        )
        source = data_path.read_text(encoding="utf-8")

        def _do(language_spec: Language) -> LiteralizeResult:
            """Render *source* with the built language."""
            return literalize(
                source=source,
                input_format=input_format,
                language=language_spec,
                pre_indent_level=pre_indent_level,
                include_delimiters=include_delimiters,
                variable_form=variable_form,
                wrap_in_file=wrap_in_file,
                ref_case=ref_case,
                ref_key=ref_key,
                record_null_substitutions=options.record_null_substitutions,
                collection_layout=collection_layout,
            )

        rendered = self._render_with_strategy(
            language_name=language_name,
            language_cls=language_cls,
            render=_do,
            options=options,
        )
        if rendered is None:
            return []
        result, _ = rendered
        parts: list[str] = []
        if (include_preamble or preamble_only) and len(result.preamble) > 0:
            parts.append("\n".join(result.preamble))
        if not preamble_only:
            parts.append(result.code)
        text = "\n\n".join(parts)

        # First positional arg sets rawsource; Sphinx requires
        # rawsource == astext() for syntax highlighting to apply.
        # Use the absolute path for `source` to match the behaviour of
        # Sphinx's built-in LiteralInclude directive, which also stores an
        # absolute path so that downstream code can rely on it without having
        # to resolve relative→absolute itself.
        return self._make_node(
            text=text,
            data_path=data_path,
            language_cls=language_cls,
        )


@beartype
class LiteralizerCallDirective(_BaseLiteralizerDirective):
    """Directive that converts a data file to function call expressions.

    Usage::

        .. literalizer-call:: path/to/data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :call-style: keyword
           :call-transform: print($call)  # $call ($0), $index, $zipped
           :zip-file: expected.json
           :zip-input-format: json
           :comment-file: comments.txt
           :input-format: json
           :indent: 4
           :indent-char: spaces
           :include-preamble:
           :preamble-only:
           :omit-code:
           :ref-case: camel
           :ref-key: $reference
           :module-name: MyModule
           :record-struct-name-prefix: Record
           :record-shape-names: x,y=Point; a,b,c=Vec3
           :heterogeneous-value-name: Value
           :consumable-refs: my_var,other_var
           :collection-layout: multiline
           :heterogeneous-strategy: auto
           :skip-if-unrepresentable:
           :variable-name: my_data
           :existing-variable:
           :modifiers: public,static

        .. literalizer-call:: path/to/no_args.yaml
           :language: rust
           :constructor-class: Widget
           :per-element:
           :variable-name: widget

    ``:call-transform:`` substitutes these placeholders in the template:
    ``$call`` (and the ``$0`` alias) for the rendered call expression,
    ``$index`` for the zero-based call position, and ``$zipped`` for the
    matching ``:zip-file:`` element rendered as a native literal (empty
    when no ``:zip-file:`` is given).

    Use exactly one of ``:target-function:`` and
    ``:constructor-class:``.  ``:constructor-class:`` formats a
    language-specific zero-argument constructor target and then renders
    through the same call machinery as ``:target-function:``.

    ``:comment-file:`` is a text file with one line per generated call;
    each non-blank line is emitted as a trailing source comment after
    that call (using the target language's comment syntax), and a blank
    line emits no comment.  The line count must match the number of
    generated calls.

    An empty (or omitted) ``:parameter-names:`` means the call takes *no*
    arguments.  Combined with ``:per-element:`` over a single-element
    source (e.g. ``- []``) and ``:variable-name:``, this renders a
    no-argument constructor bound to a variable -- ``p1 = Playlist()`` /
    ``let p1 = Playlist::new();`` / ``auto p1 = Playlist();`` -- in the
    target language's idiom.
    """

    option_spec: ClassVar[dict[str, _OptionValidator] | None] = {
        **_COMMON_OPTIONS,
        "target-function": directives.unchanged_required,
        "constructor-class": directives.unchanged_required,
        "parameter-names": directives.unchanged,
        "per-element": directives.flag,
        "call-transform": directives.unchanged_required,
        "zip-file": directives.unchanged_required,
        "zip-input-format": lambda x: directives.choice(
            argument=x,
            values=("json", "json5", "yaml", "toml"),
        ),
        "comment-file": directives.unchanged_required,
        "consumable-refs": directives.unchanged,
        "omit-code": directives.flag,
        "variable-name": directives.unchanged,
        "existing-variable": directives.flag,
        "modifiers": directives.unchanged,
    }

    @staticmethod
    def _build_call_transform(
        *,
        options: _LiteralizerCallOptions,
    ) -> Callable[[CallContext], str] | None:
        """Build the ``:call-transform:`` callback from the template.

        All placeholders are substituted in a single pass so that text
        inserted for one placeholder -- a ``$zipped`` literal rendered
        from user data, or a rendered ``$call`` expression that itself
        contains a ``$0`` -- is never re-scanned and re-expanded.
        """
        template = options.call_transform
        if template is None:
            return None

        # Longer tokens first so alternation never matches a prefix; none
        # of these actually share a prefix, but this keeps it robust.
        placeholder = re.compile(pattern=r"\$index|\$zipped|\$call|\$0")

        def _call_transform(context: CallContext) -> str:
            """Substitute call-context placeholders in the template."""
            zipped = "" if context.zipped is None else context.zipped
            replacements = {
                "$index": str(object=context.index),
                "$zipped": zipped,
                "$call": context.call,
                "$0": context.call,
            }
            return placeholder.sub(
                repl=partial(
                    _substitute_placeholder, replacements=replacements
                ),
                string=template,
            )

        return _call_transform

    def _resolve_zip_source(
        self,
        *,
        options: _LiteralizerCallOptions,
    ) -> tuple[str | None, InputFormat | None]:
        """Read the optional ``:zip-file:`` and resolve its format."""
        zip_file_value = options.zip_file
        if zip_file_value is None:
            return None, None
        env = self.env
        zip_path = (Path(env.srcdir) / zip_file_value).resolve()
        env.note_dependency(filename=str(object=zip_path))
        zip_input_format = self._resolve_format(
            data_path=zip_path,
            explicit=options.zip_input_format,
            option_name="zip-input-format",
        )
        return zip_path.read_text(encoding="utf-8"), zip_input_format

    def _resolve_comment_source(
        self,
        *,
        options: _LiteralizerCallOptions,
    ) -> list[str] | None:
        """Read the optional ``:comment-file:`` as one comment per call.

        Each line becomes one ``comment_source`` entry, paired
        positionally with a generated call; a blank line emits no
        comment for that call.  A trailing newline does not add an
        extra (empty) entry.
        """
        comment_file_value = options.comment_file
        if comment_file_value is None:
            return None
        env = self.env
        comment_path = (Path(env.srcdir) / comment_file_value).resolve()
        env.note_dependency(filename=str(object=comment_path))
        return comment_path.read_text(encoding="utf-8").splitlines()

    def _parse_options(self) -> _LiteralizerCallOptions:
        """Parse ``self.options`` into the typed options dataclass."""
        options = self._options_with_language_defaults()
        target_function = self.options.get("target-function")
        constructor_class = self.options.get("constructor-class")
        if constructor_class is not None:
            if target_function is not None:
                msg = (
                    "':target-function:' cannot be combined with "
                    "':constructor-class:'."
                )
                raise _DirectiveError(message=msg)
            target_name = constructor_class
        else:
            if target_function is None:
                msg = (
                    "Use exactly one of ':target-function:' and "
                    "':constructor-class:'."
                )
                raise _DirectiveError(message=msg)
            target_name = target_function
        return _LiteralizerCallOptions(
            **_common_option_args(options=options),
            target_name=target_name,
            constructor_call=constructor_class is not None,
            parameter_names=self.options.get("parameter-names", ""),
            per_element="per-element" in self.options,
            call_transform=self.options.get("call-transform"),
            zip_file=self.options.get("zip-file"),
            zip_input_format=self.options.get("zip-input-format"),
            comment_file=self.options.get("comment-file"),
            consumable_refs=self.options.get("consumable-refs"),
            omit_code="omit-code" in self.options,
        )

    @override
    def _run(self) -> list[nodes.Node]:
        """Read the data file and produce function call expressions."""
        options = self._parse_options()
        env = self.env
        data_path = (Path(env.srcdir) / self.arguments[0]).resolve()

        env.note_dependency(filename=str(object=data_path))

        language_name = options.language
        language_cls = _language_types()[language_name]

        pre_indent_level = options.pre_indent_level
        include_preamble = options.include_preamble
        preamble_only = options.preamble_only
        omit_code = options.omit_code
        # An empty (or omitted) ``:parameter-names:`` means *no*
        # arguments rather than one empty-named argument: splitting ``""``
        # on ``,`` would yield ``['']`` (a single argument), so the
        # zero-argument call -- e.g. a no-argument constructor bound to
        # ``:variable-name:`` -- would be unreachable.  An empty value
        # therefore parses to ``[]``.
        if options.parameter_names.strip() != "":
            parameter_names: list[str] = [
                p.strip() for p in options.parameter_names.split(sep=",")
            ]
        else:
            parameter_names = []
        per_element = options.per_element
        wrap_in_file = options.wrap_in_file

        call_transform = self._build_call_transform(options=options)

        ref_case, ref_key = self._resolve_ref_options(options=options)
        collection_layout = self._resolve_collection_layout(options=options)
        variable_form = self._resolve_variable_form(
            language_cls=language_cls,
            options=options,
            both_variable_forms=False,
        )

        consumable_refs_value = options.consumable_refs
        if consumable_refs_value is None:
            consumable_refs = frozenset[str]()
        else:
            consumable_refs = frozenset(
                r.strip()
                for r in consumable_refs_value.split(sep=",")
                if r.strip() != ""
            )

        zip_source, zip_input_format = self._resolve_zip_source(
            options=options,
        )
        comment_source = self._resolve_comment_source(options=options)

        input_format = self._resolve_input_format(
            data_path=data_path,
            options=options,
        )
        source = data_path.read_text(encoding="utf-8")

        def _do(language_spec: Language) -> LiteralizeResult:
            """Render the calls for *source* with the built language."""
            format_constructor = language_spec.format_constructor_target
            return literalize_call(
                source=source,
                input_format=input_format,
                language=language_spec,
                target_function=(
                    format_constructor(options.target_name)
                    if options.constructor_call
                    else options.target_name
                ),
                parameter_names=parameter_names,
                call_transform=call_transform,
                zip_source=zip_source,
                zip_input_format=zip_input_format,
                comment_source=comment_source,
                per_element=per_element,
                wrap_in_file=wrap_in_file,
                ref_case=ref_case,
                consumable_refs=consumable_refs,
                ref_key=ref_key,
                collection_layout=collection_layout,
                variable_form=variable_form,
            )

        try:
            rendered = self._render_with_strategy(
                language_name=language_name,
                language_cls=language_cls,
                render=_do,
                options=options,
            )
        except ParameterCountMismatchError as exc:
            msg = (
                f"':parameter-names:' has {len(parameter_names)} entries "
                f"but the data provides a different number of values: {exc}"
            )
            raise _DirectiveError(message=msg) from exc

        if rendered is None:
            return []
        result, language_spec = rendered

        code = result.code
        if pre_indent_level > 0:
            indent = language_spec.indent * pre_indent_level
            code = "\n".join(
                indent + line if line != "" else line
                for line in code.splitlines()
            )

        parts: list[str] = []
        if (include_preamble or preamble_only) and len(result.preamble) > 0:
            parts.append("\n".join(result.preamble))
        if not omit_code and not preamble_only:
            parts.append(code)
        text = "\n\n".join(parts)

        return self._make_node(
            text=text,
            data_path=data_path,
            language_cls=language_cls,
        )
