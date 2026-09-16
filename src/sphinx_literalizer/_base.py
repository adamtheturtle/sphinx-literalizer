"""Shared implementation for the Sphinx directives."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any, override

from beartype import beartype
from docutils import nodes
from literalizer import (
    BothVariableForms,
    CollectionLayout,
    ExistingVariable,
    IdentifierCase,
    InputFormat,
    Language,
    LanguageCls,
    LiteralizeResult,
    NewVariable,
    VariableForm,
)
from literalizer.exceptions import (
    HeterogeneousCollectionError,
    UnrepresentableEmptyDictError,
    UnrepresentableInputError,
    UnrepresentableIntegerError,
    UnsupportedOptionError,
)
from sphinx.errors import ExtensionError
from sphinx.util.docutils import SphinxDirective

from ._support import (
    _AUTO_STRATEGY,
    _DEFAULT_TYPE_OPTIONS,
    _EXTENSION_TO_INPUT_FORMAT,
    _FORMAT_OPTION_GETTERS,
    _HETEROGENEOUS_VALUE_NAME_PARAMETERS,
    _all_formats,
    _CommonOptions,
    _DirectiveError,
    _enum_member,
    _is_string_list,
    _is_string_object_dict,
    _language_types,
    _literalize_errors_as_directive_errors,
    _lookup_format,
    _make_format_validator,
    _optional_modifiers,
    _parse_record_shape_names,
)

__all__ = ("_BaseLiteralizerDirective",)


@beartype
class _BaseLiteralizerDirective(SphinxDirective, ABC):
    """Shared logic for literalizer directives."""

    required_arguments = 1
    has_content = False

    @override
    def run(self) -> list[nodes.Node]:
        """Render the directive, reporting author errors in place.

        A ``_DirectiveError`` becomes a docutils directive error, so it
        is reported as ``document.rst:<line>: ERROR: <message>`` against
        the offending directive, participates in ``-W``, and lets one
        build surface every bad block instead of aborting at the first.

        The message ends with the data file the directive names.  A
        directive generated inside another directive's content -- a
        ``sphinx-jinja2`` block, say -- is reported against the
        *enclosing* directive's line, so the document and line alone
        identify neither the failing directive nor its input; the data
        file is what an author has to open to fix the error, and within
        one generated block it identifies the directive too.
        """
        try:
            return self._run()
        except _DirectiveError as exc:
            data_file = self.arguments[0]
            message = f"{exc} (in '{data_file}')"
            raise self.error(message=message) from exc

    @abstractmethod
    def _run(self) -> list[nodes.Node]:
        """Produce the nodes for this directive."""

    # types-docutils cannot express a directive's specific option types; see
    # https://github.com/python/typeshed/issues/16400. The merged values are
    # passed directly to the runtime-validating parser above.
    def _options_with_language_defaults(
        self,
    ) -> dict[str, Any]:  # pyrefly: ignore[explicit-any]
        """Merge configured language defaults with explicit options.

        The literalizer_language_defaults setting contains only shared
        format options, keyed by directive language. Values written on a
        directive override those defaults.
        """
        language_name = self.options["language"]
        configured = dict[str, object](
            self.env.config.literalizer_language_defaults,
        )
        defaults = configured.get(language_name, {})
        if not _is_string_object_dict(defaults):
            msg = (
                "'literalizer_language_defaults' entries must be "
                "dictionaries of directive options."
            )
            raise ExtensionError(message=msg)

        validated_defaults: dict[str, str] = {}
        for option_name, value in defaults.items():
            if option_name not in _FORMAT_OPTION_GETTERS:
                msg = (
                    "'literalizer_language_defaults' only supports shared "
                    f"format options; '{option_name}' is not one."
                )
                raise ExtensionError(message=msg)
            if not isinstance(value, str):
                msg = (
                    "'literalizer_language_defaults' option values must be "
                    f"strings; '{option_name}' is not."
                )
                raise ExtensionError(message=msg)
            validated_defaults[option_name] = _make_format_validator(
                option_name=option_name
            )(value)
        return {**validated_defaults, **self.options}

    @staticmethod
    def _apply_format_options(
        language_name: str,
        constructor: partial[Language],
        *,
        options: _CommonOptions,
        heterogeneous_strategy_value: str | None,
    ) -> partial[Language]:
        """Apply all format/enum options.

        ``heterogeneous-strategy`` is taken from
        *heterogeneous_strategy_value* rather than the directive options
        so the caller can vary it per attempt for ``auto``; the resolved
        value is never the ``auto`` sentinel.
        """
        all_formats = _all_formats()
        for option_name in _FORMAT_OPTION_GETTERS:
            if option_name == "heterogeneous-strategy":
                value = heterogeneous_strategy_value
            else:
                value = options.format_options.get(option_name)
            if value is not None:
                param_name = option_name.replace("-", "_")
                constructor = partial(
                    constructor,
                    **{
                        param_name: _lookup_format(
                            language_name=language_name,
                            directive_name=option_name,
                            format_value=value,
                            formats=all_formats[option_name],
                        ),
                    },
                )
        return constructor

    @staticmethod
    def _apply_default_type_options(
        language_name: str,
        constructor: partial[Language],
        *,
        options: _CommonOptions,
    ) -> partial[Language]:
        """Apply default element/key/value type options."""
        language_cls = _language_types()[language_name]
        for option_name, param_name in _DEFAULT_TYPE_OPTIONS.items():
            value = options.default_type_options.get(option_name)
            if value is not None:
                if param_name not in language_cls.__dataclass_fields__:
                    msg = (
                        f"Language '{language_name}' does not support "
                        f"'{option_name}'."
                    )
                    raise _DirectiveError(message=msg)
                constructor = partial(
                    constructor,
                    **{param_name: value},
                )
        return constructor

    @staticmethod
    def _apply_multiline_raw_string_delimiter_base(
        constructor: partial[Language],
        *,
        options: _CommonOptions,
    ) -> partial[Language]:
        """Apply the multiline raw-string delimiter base option.

        A language whose constructor does not accept the parameter
        rejects it with ``UnsupportedOptionError``, reported by
        :meth:`_build_language` as a clean directive error.
        """
        delimiter_base = options.multiline_raw_string_delimiter_base
        if delimiter_base is None:
            return constructor
        return partial(
            constructor,
            multiline_raw_string_delimiter_base=delimiter_base,
        )

    def _build_language(
        self,
        language_name: str,
        language_cls: LanguageCls,
        *,
        options: _CommonOptions,
        heterogeneous_strategy_value: str | None,
    ) -> Language:
        """Build a Language instance from directive options.

        *heterogeneous_strategy_value* is the concrete strategy name (or
        ``None`` for the language default) to apply for this build; it is
        kept separate from the directive options so ``auto`` can rebuild
        the language with a different strategy per attempt.
        """
        constructor = partial(language_cls)

        indent_count = options.indent
        indent_char_name = options.indent_char
        if indent_count is not None or indent_char_name is not None:
            resolved_count: int = 4 if indent_count is None else indent_count
            resolved_char = "\t" if indent_char_name == "tabs" else " "
            constructor = partial(
                constructor,
                indent=resolved_char * resolved_count,
            )

        constructor = self._apply_format_options(
            language_name=language_name,
            constructor=constructor,
            options=options,
            heterogeneous_strategy_value=heterogeneous_strategy_value,
        )
        constructor = self._apply_default_type_options(
            language_name=language_name,
            constructor=constructor,
            options=options,
        )
        constructor = self._apply_multiline_raw_string_delimiter_base(
            constructor=constructor,
            options=options,
        )

        module_name = options.module_name
        if module_name is not None:
            # ``module_name_case`` exists only on languages that accept
            # ``module_name``, so this conversion needs a flag check
            # before the constructor can reject the option itself.
            if not language_cls.supports_module_name:
                msg = (
                    f"Language '{language_name}' does not support "
                    f"':module-name:'."
                )
                raise _DirectiveError(message=msg)
            module_name = language_cls.module_name_case.convert(
                name=module_name,
            )
            constructor = partial(constructor, module_name=module_name)

        prefix = options.record_struct_name_prefix
        if prefix is not None:
            constructor = partial(
                constructor,
                record_struct_name_prefix=prefix,
            )

        shape_names_value = options.record_shape_names
        if shape_names_value is not None:
            constructor = partial(
                constructor,
                record_shape_names=_parse_record_shape_names(
                    value=shape_names_value,
                ),
            )

        heterogeneous_value_name = options.heterogeneous_value_name
        if heterogeneous_value_name is not None:
            parameter_name = next(
                (
                    candidate
                    for candidate in _HETEROGENEOUS_VALUE_NAME_PARAMETERS
                    if candidate in language_cls.__dataclass_fields__
                ),
                None,
            )
            if parameter_name is None:
                msg = (
                    f"Language '{language_name}' does not support "
                    "':heterogeneous-value-name:'."
                )
                raise _DirectiveError(message=msg)
            constructor = partial(
                constructor,
                **{parameter_name: heterogeneous_value_name},
            )

        with _literalize_errors_as_directive_errors():
            try:
                return constructor()
            except UnsupportedOptionError as exc:
                # The constructor is the single authority on which
                # options a language accepts; translate its error back
                # into the directive's option spelling.
                option_name = exc.option.replace("_", "-")
                msg = (
                    f"Language '{language_name}' does not support "
                    f"':{option_name}:'."
                )
                raise _DirectiveError(message=msg) from exc

    @staticmethod
    def _resolve_format(
        data_path: Path,
        *,
        explicit: str | None,
        option_name: str,
    ) -> InputFormat:
        """Determine an input format from *explicit* or the file
        extension.

        *option_name* names the directive option that *explicit* came
        from, used only for the "cannot determine" error message.  It is
        what identifies *which* file could not be resolved: every
        directive error already ends with the directive's data file, so
        naming the file here as well would repeat it for the common case
        of the data file's own format.
        """
        if explicit is not None:
            return _enum_member(cls=InputFormat, value=explicit)
        suffix = data_path.suffix.lower()
        try:
            return _EXTENSION_TO_INPUT_FORMAT[suffix]
        except KeyError:
            msg = (
                "Cannot determine input format from the file extension. "
                f"Use the :{option_name}: option."
            )
            raise _DirectiveError(message=msg) from None

    def _resolve_input_format(
        self,
        data_path: Path,
        *,
        options: _CommonOptions,
    ) -> InputFormat:
        """Determine the input format from the option or file
        extension.
        """
        return self._resolve_format(
            data_path=data_path,
            explicit=options.input_format,
            option_name="input-format",
        )

    def _make_node(
        self,
        text: str,
        data_path: Path,
        language_cls: LanguageCls,
    ) -> list[nodes.Node]:
        """Create a literal_block node."""
        node = nodes.literal_block(
            text,
            text,
            source=str(object=data_path),
        )
        pygments_name = language_cls.pygments_name
        node["language"] = (
            pygments_name
            if pygments_name is not None and pygments_name != ""
            else "text"
        )
        self.add_name(node=node)
        return [node]

    @staticmethod
    def _resolve_ref_options(
        *,
        options: _CommonOptions,
    ) -> tuple[IdentifierCase | None, str]:
        """Resolve reference marker options."""
        ref_case_value = options.ref_case
        ref_case: IdentifierCase | None = (
            None
            if ref_case_value is None
            else _enum_member(cls=IdentifierCase, value=ref_case_value)
        )
        return ref_case, options.ref_key

    @staticmethod
    def _resolve_variable_form(
        language_cls: LanguageCls,
        *,
        options: _CommonOptions,
        both_variable_forms: bool,
    ) -> VariableForm | None:
        """Resolve the variable-form options into a ``VariableForm``.

        *both_variable_forms* is passed in (rather than read from
        *options*) because ``:both-variable-forms:`` only exists on the
        ``literalizer`` directive; the caller supplies ``False`` where the
        directive does not support it.
        """
        variable_name = options.variable_name
        existing_variable = options.existing_variable
        modifiers_value = options.modifiers

        if modifiers_value is not None and variable_name is None:
            msg = "':modifiers:' requires ':variable-name:'."
            raise _DirectiveError(message=msg)
        if modifiers_value is not None and existing_variable:
            msg = (
                "':modifiers:' cannot be combined with ':existing-variable:'."
            )
            raise _DirectiveError(message=msg)
        if modifiers_value is not None and both_variable_forms:
            msg = (
                "':modifiers:' cannot be combined with "
                "':both-variable-forms:'."
            )
            raise _DirectiveError(message=msg)
        if both_variable_forms and variable_name is None:
            msg = "':both-variable-forms:' requires ':variable-name:'."
            raise _DirectiveError(message=msg)
        if both_variable_forms and existing_variable:
            msg = (
                "':both-variable-forms:' cannot be combined with "
                "':existing-variable:'."
            )
            raise _DirectiveError(message=msg)
        if existing_variable and variable_name is None:
            msg = "':existing-variable:' requires ':variable-name:'."
            raise _DirectiveError(message=msg)

        if variable_name is None:
            return None

        modifiers = _optional_modifiers(
            language_cls=language_cls,
            value=modifiers_value,
        )

        if existing_variable:
            return ExistingVariable(name=variable_name)
        if both_variable_forms:
            return BothVariableForms(name=variable_name, modifiers=modifiers)
        return NewVariable(name=variable_name, modifiers=modifiers)

    @staticmethod
    def _resolve_collection_layout(
        *,
        options: _CommonOptions,
    ) -> CollectionLayout:
        """Resolve the nested collection layout option."""
        return _enum_member(
            cls=CollectionLayout,
            value=options.collection_layout,
        )

    def _auto_precedence(self, *, language_cls: LanguageCls) -> list[str]:
        """Strategies ``auto`` falls back through, most preferred first.

        The configured precedence
        (``literalizer_heterogeneous_strategy_precedence``) restricted to
        the strategies the target language exposes.  ``error`` is never
        included -- it is the failure ``auto`` recovers from.
        """
        supported = {
            member.name.lower()
            for member in language_cls.HeterogeneousStrategies
        }
        precedence_value: object = self.env.config[
            "literalizer_heterogeneous_strategy_precedence"
        ]
        if not _is_string_list(precedence_value):
            message = (
                "'literalizer_heterogeneous_strategy_precedence' must be "
                "a list of strings."
            )
            raise ExtensionError(message=message)
        precedence = precedence_value
        return [
            name
            for name in precedence
            if name in supported and name != "error"
        ]

    def _render_with_strategy(
        self,
        *,
        language_name: str,
        language_cls: LanguageCls,
        render: Callable[[Language], LiteralizeResult],
        options: _CommonOptions,
    ) -> tuple[LiteralizeResult, Language] | None:
        """Build the language and render, honoring ``auto`` and
        ``:skip-if-unrepresentable:``.

        For ``:heterogeneous-strategy: auto`` the natural representation
        is tried first -- so homogeneous and genuinely map-shaped data
        keep their native output -- then each strategy from
        :meth:`_auto_precedence` in turn until one represents the data.

        Returns ``(result, language)`` where *result* is what *render*
        produced, or ``None`` when the input cannot be represented in the
        target language and ``:skip-if-unrepresentable:`` is set (the
        caller then emits no node).
        """
        skip = options.skip_if_unrepresentable

        # An unset ``:heterogeneous-strategy:`` defaults to ``auto``
        # rather than falling through to literalizer's per-language
        # default (e.g. ``error`` for Rust): ``auto`` strictly dominates
        # ``error`` as a default since it tries the natural
        # representation first (byte-identical output for homogeneous /
        # map-shaped data) and still raises for genuinely
        # unrepresentable input.  An author who wants a specific
        # representation sets the option explicitly.
        strategy = (
            _AUTO_STRATEGY
            if options.heterogeneous_strategy is None
            else options.heterogeneous_strategy
        )
        if strategy == _AUTO_STRATEGY:
            attempts: list[str | None] = [
                None,
                *self._auto_precedence(language_cls=language_cls),
            ]
        else:
            attempts = [strategy]

        def _build(strategy_value: str | None) -> Language:
            """Build the language for one attempt's strategy."""
            return self._build_language(
                language_name=language_name,
                language_cls=language_cls,
                options=options,
                heterogeneous_strategy_value=strategy_value,
            )

        with _literalize_errors_as_directive_errors():
            for strategy_value in attempts:
                try:
                    language_spec = _build(strategy_value=strategy_value)
                    return render(language_spec), language_spec
                except (
                    UnrepresentableInputError,
                    UnrepresentableEmptyDictError,
                    UnrepresentableIntegerError,
                ):
                    # No heterogeneous strategy can fix a shape-level
                    # rejection (or an out-of-range integer / empty-map
                    # ambiguity), so do not fall back; skip or surface it.
                    if skip:
                        return None
                    raise
                except HeterogeneousCollectionError:
                    # An ``auto`` fallback (or the sole attempt): move on
                    # to the next strategy, if any.
                    continue
            # Every attempt raised ``HeterogeneousCollectionError``.
            if skip:
                return None
            # Re-run the last attempt so its error propagates to the
            # surrounding converter as a clean ``_DirectiveError``.
            language_spec = _build(strategy_value=attempts[-1])
            return render(language_spec), language_spec
