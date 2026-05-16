"""Sphinx extension for literalizer.

Provides the ``literalizer`` and ``literalizer-call`` directives, which
read data files and render them as native language code blocks.
"""

import enum
from collections.abc import Callable, Generator, Iterable
from contextlib import contextmanager
from functools import cache, partial
from importlib.metadata import version
from pathlib import Path
from typing import Any, ClassVar

from beartype import beartype
from docutils import nodes
from docutils.parsers.rst import directives
from literalizer import (
    BothVariableForms,
    CallContext,
    CollectionLayout,
    ExistingVariable,
    IdentifierCase,
    InputFormat,
    Language,
    LanguageCls,
    LiteralizeResult,
    NewVariable,
    VariableForm,
    literalize,
    literalize_call,
)
from literalizer.exceptions import (
    CallArgNotSupportedError,
    CallsNotSupportedByLanguageError,
    CallsNotSupportedByToolError,
    CommentSourceLengthMismatchError,
    CommentSourceMultilineError,
    DottedCallTargetNotSupportedError,
    HeterogeneousCollectionError,
    InvalidRecordNameError,
    ParameterCountMismatchError,
    PerElementNotListError,
    UnrepresentableInputError,
    UnsupportedCallShapeError,
    UnsupportedIdentifierCaseError,
    VariableNameNotSupportedError,
    WrapCombinedInFileNotSupportedError,
    WrapInFileWithoutVariableNotSupportedError,
    ZipSourceWithoutInputFormatError,
    ZipValuesLengthMismatchError,
)
from literalizer.languages import ALL_LANGUAGES
from sphinx.application import Sphinx
from sphinx.errors import ExtensionError
from sphinx.util.docutils import SphinxDirective
from sphinx.util.typing import ExtensionMetadata


def _language_name(lang_cls: LanguageCls) -> str:
    """Return the directive language key for a language class."""
    pygments_name = lang_cls.pygments_name
    if pygments_name is None or pygments_name == "text":
        return lang_cls.__name__.lower()
    return pygments_name


@cache
def _language_types() -> dict[str, LanguageCls]:
    """Map directive language keys to their language classes."""
    return {
        _language_name(lang_cls=lang_cls): lang_cls
        for lang_cls in ALL_LANGUAGES
    }


# Map from directive option name to a typed lambda getter for the enum class.
_FORMAT_OPTION_GETTERS: dict[
    str,
    Callable[[LanguageCls], Iterable[enum.Enum]],
] = {
    "date-format": lambda cls: cls.DateFormats,
    "datetime-format": lambda cls: cls.DatetimeFormats,
    "sequence-format": lambda cls: cls.SequenceFormats,
    "set-format": lambda cls: cls.SetFormats,
    "bytes-format": lambda cls: cls.BytesFormats,
    "comment-format": lambda cls: cls.CommentFormats,
    "variable-type-hints": lambda cls: cls.VariableTypeHints,
    "declaration-style": lambda cls: cls.DeclarationStyles,
    "dict-entry-style": lambda cls: cls.DictEntryStyles,
    "dict-format": lambda cls: cls.DictFormats,
    "float-format": lambda cls: cls.FloatFormats,
    "integer-format": lambda cls: cls.IntegerFormats,
    "numeric-literal-suffix": lambda cls: cls.NumericLiteralSuffixes,
    "numeric-separator": lambda cls: cls.NumericSeparators,
    "numeric-style": lambda cls: cls.NumericStyles,
    "string-format": lambda cls: cls.StringFormats,
    "trailing-comma": lambda cls: cls.TrailingCommas,
    "language-version": lambda cls: cls.VersionFormats,
    "empty-dict-key": lambda cls: cls.EmptyDictKey,
    "heterogeneous-strategy": lambda cls: cls.HeterogeneousStrategies,
    "call-style": lambda cls: cls.CallStyles,
}


_IDENTIFIER_CASE_VALUES: tuple[str, ...] = tuple(
    sorted(m.name.lower() for m in IdentifierCase)
)
_COLLECTION_LAYOUT_VALUES: tuple[str, ...] = tuple(
    sorted(m.name.lower() for m in CollectionLayout)
)


@cache
def _all_formats() -> dict[str, dict[tuple[str, str], object]]:
    """Build format lookup dicts for all format options."""
    return {
        option_name: {
            (lang_name, member.name.lower()): member
            for lang_name, lang_cls in _language_types().items()
            for member in getter(lang_cls)
        }
        for option_name, getter in _FORMAT_OPTION_GETTERS.items()
    }


@cache
def _all_format_values() -> dict[str, tuple[str, ...]]:
    """Build sorted unique value tuples for all format options."""
    return {
        option_name: tuple(sorted({v for _, v in formats}))
        for option_name, formats in _all_formats().items()
    }


@beartype
def _lookup_format(
    language_name: str,
    directive_name: str,
    format_value: str,
    formats: dict[tuple[str, str], object],
) -> object:
    """Look up a format enum member by language and value."""
    try:
        return formats[(language_name, format_value)]
    except KeyError:
        msg = (
            f"Language '{language_name}' does not support "
            f"{directive_name} '{format_value}'."
        )
        raise ExtensionError(message=msg) from None


def _parse_modifiers(
    language_name: str,
    language_cls: LanguageCls,
    value: str,
) -> frozenset[enum.Enum]:
    """Parse a comma-separated list of modifier names for the language."""
    result: set[enum.Enum] = set()
    for raw in value.split(sep=","):
        name = raw.strip()
        if not name:
            continue
        try:
            result.add(language_cls.Modifiers[name.upper()])
        except KeyError:
            msg = (
                f"Language '{language_name}' does not support "
                f"modifier '{name}'."
            )
            raise ExtensionError(message=msg) from None
    return frozenset(result)


def _parse_record_shape_names(value: str) -> dict[frozenset[str], str]:
    """Parse the ``:record-shape-names:`` inline mapping.

    The value is a semicolon-separated list of ``key1,key2=Name``
    entries, each mapping a record's set of keys to the custom struct /
    ``record`` / ``case class`` name used instead of the auto-generated
    one.  Whitespace around keys, names, and separators is ignored, and
    empty entries (e.g. from a trailing semicolon) are skipped.
    """
    result: dict[frozenset[str], str] = {}
    for raw_entry in value.split(sep=";"):
        entry = raw_entry.strip()
        if not entry:
            continue
        if "=" not in entry:
            msg = (
                f"':record-shape-names:' entry {entry!r} is missing the "
                f"'=' between the comma-separated keys and the name."
            )
            raise ExtensionError(message=msg)
        keys_part, name = entry.rsplit(sep="=", maxsplit=1)
        keys = frozenset(
            key.strip() for key in keys_part.split(sep=",") if key.strip()
        )
        name = name.strip()
        if not keys or not name:
            msg = (
                f"':record-shape-names:' entry {entry!r} must have at "
                f"least one key and a non-empty name."
            )
            raise ExtensionError(message=msg)
        if keys in result:
            sorted_keys = ", ".join(sorted(keys))
            msg = (
                f"':record-shape-names:' has multiple entries for the "
                f"key set {{{sorted_keys}}}."
            )
            raise ExtensionError(message=msg)
        result[keys] = name
    return result


def _make_format_validator(
    option_name: str,
) -> Callable[[str], str]:
    """Create a directive choice validator for a format option."""

    def validator(x: str) -> str:
        """Validate that *x* is a known value for this format option."""
        return directives.choice(
            argument=x,
            values=_all_format_values()[option_name],
        )

    return validator


# Sentinel value for ``:heterogeneous-strategy:`` that asks the directive
# to pick a strategy itself instead of naming a literalizer enum member.
_AUTO_STRATEGY = "auto"

# Order in which ``:heterogeneous-strategy: auto`` tries representational
# strategies *after* the natural representation fails.  Restricted per
# directive to the strategies the target language actually exposes;
# overridable via the ``literalizer_heterogeneous_strategy_precedence``
# config value.  ``error`` is never a fallback -- it is the failure that
# ``auto`` is recovering from.
_DEFAULT_HETEROGENEOUS_STRATEGY_PRECEDENCE: tuple[str, ...] = (
    "record",
    "tuple",
    "tagged_enum",
    "object_variant",
    "variant",
    "union_type",
    "interface",
)


def _heterogeneous_strategy_validator(x: str) -> str:
    """Validate ``:heterogeneous-strategy:``, also accepting ``auto``."""
    return directives.choice(
        argument=x,
        values=(
            _AUTO_STRATEGY,
            *_all_format_values()["heterogeneous-strategy"],
        ),
    )


_COMMON_OPTIONS: dict[str, Callable[[str], Any]] = {
    "language": lambda x: directives.choice(
        argument=x,
        values=tuple(_language_types()),
    ),
    "input-format": lambda x: directives.choice(
        argument=x,
        values=("json", "json5", "yaml", "toml"),
    ),
    "pre-indent-level": directives.nonnegative_int,
    "indent": directives.nonnegative_int,
    "indent-char": lambda x: directives.choice(
        argument=x,
        values=("spaces", "tabs"),
    ),
    "include-preamble": directives.flag,
    **{
        option_name: _make_format_validator(option_name=option_name)
        for option_name in _FORMAT_OPTION_GETTERS
    },
    # ``auto`` is not a literalizer enum member, so this option needs a
    # validator that accepts it alongside the per-language values.
    "heterogeneous-strategy": _heterogeneous_strategy_validator,
    "default-set-element-type": directives.unchanged,
    "default-sequence-element-type": directives.unchanged,
    "default-dict-key-type": directives.unchanged,
    "default-dict-value-type": directives.unchanged,
    "default-ordered-map-value-type": directives.unchanged,
    "module-name": directives.unchanged,
    "record-struct-name-prefix": directives.unchanged_required,
    "record-shape-names": directives.unchanged_required,
    "skip-if-unrepresentable": directives.flag,
    "wrap-in-file": directives.flag,
    "ref-case": lambda x: directives.choice(
        argument=x,
        values=_IDENTIFIER_CASE_VALUES,
    ),
    "ref-key": directives.unchanged_required,
    "collection-layout": lambda x: directives.choice(
        argument=x,
        values=_COLLECTION_LAYOUT_VALUES,
    ),
}


@cache
def _languages_supporting_module_name() -> frozenset[str]:
    """Return directive language keys whose class accepts
    ``module_name``.
    """
    return frozenset(
        name
        for name, lang_cls in _language_types().items()
        if lang_cls.supports_module_name
    )


_EXTENSION_TO_INPUT_FORMAT: dict[str, InputFormat] = {
    ".json": InputFormat.JSON,
    ".json5": InputFormat.JSON5,
    ".yaml": InputFormat.YAML,
    ".yml": InputFormat.YAML,
    ".toml": InputFormat.TOML,
}


# Literalizer exceptions that signal a directive option combination the
# selected language cannot represent.  Surfacing these as a clean
# ``ExtensionError`` (rather than a traceback) lets the build report the
# offending directive and continue under ``-W``.  This includes
# ``HeterogeneousCollectionError`` so a record-shaped or mixed-scalar
# input rendered with a concrete (non-``auto``) strategy that cannot
# represent it fails loudly rather than with a traceback.
_USER_FACING_LITERALIZER_ERRORS: tuple[type[Exception], ...] = (
    CallArgNotSupportedError,
    CallsNotSupportedByLanguageError,
    CallsNotSupportedByToolError,
    CommentSourceLengthMismatchError,
    CommentSourceMultilineError,
    DottedCallTargetNotSupportedError,
    HeterogeneousCollectionError,
    InvalidRecordNameError,
    PerElementNotListError,
    UnrepresentableInputError,
    UnsupportedCallShapeError,
    UnsupportedIdentifierCaseError,
    VariableNameNotSupportedError,
    WrapCombinedInFileNotSupportedError,
    WrapInFileWithoutVariableNotSupportedError,
    ZipSourceWithoutInputFormatError,
    ZipValuesLengthMismatchError,
)


@contextmanager
def _literalize_errors_as_extension_errors() -> Generator[None]:
    """Convert user-facing literalizer exceptions into
    ``ExtensionError``.
    """
    try:
        yield
    except _USER_FACING_LITERALIZER_ERRORS as exc:
        raise ExtensionError(message=str(object=exc)) from exc


@beartype
class _BaseLiteralizerDirective(SphinxDirective):
    """Shared logic for literalizer directives."""

    required_arguments = 1
    has_content = False

    def _apply_format_options(
        self,
        language_name: str,
        constructor: partial[Language],
        *,
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
                value = self.options.get(option_name)
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

    def _apply_default_type_options(
        self,
        language_name: str,
        constructor: partial[Language],
    ) -> partial[Language]:
        """Apply default element/key/value type options."""
        type_option_map: dict[
            str,
            tuple[str, Callable[[LanguageCls], bool]],
        ] = {
            "default-set-element-type": (
                "default_set_element_type",
                lambda cls: cls.supports_default_set_element_type,
            ),
            "default-sequence-element-type": (
                "default_sequence_element_type",
                lambda cls: cls.supports_default_sequence_element_type,
            ),
            "default-dict-key-type": (
                "default_dict_key_type",
                lambda cls: cls.supports_default_dict_key_type,
            ),
            "default-dict-value-type": (
                "default_dict_value_type",
                lambda cls: cls.supports_default_dict_value_type,
            ),
            "default-ordered-map-value-type": (
                "default_ordered_map_value_type",
                lambda cls: cls.supports_default_ordered_map_value_type,
            ),
        }
        language_cls = _language_types()[language_name]
        for option_name, (
            param_name,
            supports_check,
        ) in type_option_map.items():
            if (value := self.options.get(option_name)) is not None:
                if not supports_check(language_cls):
                    msg = (
                        f"Language '{language_name}' does not support "
                        f"'{option_name}'."
                    )
                    raise ExtensionError(message=msg)
                constructor = partial(
                    constructor,
                    **{param_name: value},
                )
        return constructor

    def _build_language(
        self,
        language_name: str,
        language_cls: LanguageCls,
        *,
        heterogeneous_strategy_value: str | None,
    ) -> Language:
        """Build a Language instance from directive options.

        *heterogeneous_strategy_value* is the concrete strategy name (or
        ``None`` for the language default) to apply for this build; it is
        kept separate from the directive options so ``auto`` can rebuild
        the language with a different strategy per attempt.
        """
        constructor = partial(language_cls)

        indent_count = self.options.get("indent")
        indent_char_name = self.options.get("indent-char")
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
            heterogeneous_strategy_value=heterogeneous_strategy_value,
        )
        constructor = self._apply_default_type_options(
            language_name=language_name,
            constructor=constructor,
        )

        module_name = self.options.get("module-name")
        if module_name is not None:
            if language_name not in _languages_supporting_module_name():
                msg = (
                    f"Language '{language_name}' does not support "
                    f"':module-name:'."
                )
                raise ExtensionError(message=msg)
            module_name = language_cls.module_name_case.convert(
                name=module_name,
            )
            constructor = partial(constructor, module_name=module_name)

        prefix = self.options.get("record-struct-name-prefix")
        if prefix is not None:
            if not language_cls.supports_record_struct_name_prefix:
                msg = (
                    f"Language '{language_name}' does not support "
                    f"':record-struct-name-prefix:'."
                )
                raise ExtensionError(message=msg)
            constructor = partial(
                constructor,
                record_struct_name_prefix=prefix,
            )

        shape_names_value = self.options.get("record-shape-names")
        if shape_names_value is not None:
            if not language_cls.supports_record_shape_names:
                msg = (
                    f"Language '{language_name}' does not support "
                    f"':record-shape-names:'."
                )
                raise ExtensionError(message=msg)
            constructor = partial(
                constructor,
                record_shape_names=_parse_record_shape_names(
                    value=shape_names_value,
                ),
            )

        with _literalize_errors_as_extension_errors():
            return constructor()

    def _resolve_format(
        self,
        data_path: Path,
        *,
        option_name: str,
    ) -> InputFormat:
        """Determine an input format from *option_name* or the file
        extension.
        """
        explicit = self.options.get(option_name)
        if explicit is not None:
            return InputFormat[explicit.upper()]
        suffix = data_path.suffix.lower()
        try:
            return _EXTENSION_TO_INPUT_FORMAT[suffix]
        except KeyError:
            msg = (
                f"Cannot determine input format for '{data_path.name}'. "
                f"Use the :{option_name}: option."
            )
            raise ExtensionError(message=msg) from None

    def _resolve_input_format(self, data_path: Path) -> InputFormat:
        """Determine the input format from the option or file
        extension.
        """
        return self._resolve_format(
            data_path=data_path,
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
        node["language"] = language_cls.pygments_name or "text"
        self.add_name(node=node)
        return [node]

    def _resolve_ref_options(self) -> tuple[IdentifierCase | None, str]:
        """Resolve reference marker options."""
        ref_case_value: str | None = self.options.get("ref-case")
        ref_case: IdentifierCase | None = (
            None
            if ref_case_value is None
            else IdentifierCase[ref_case_value.upper()]
        )
        ref_key: str = self.options.get("ref-key", "$ref")
        return ref_case, ref_key

    def _resolve_variable_form(
        self,
        language_name: str,
        language_cls: LanguageCls,
        *,
        allow_both: bool,
    ) -> VariableForm | None:
        """Resolve the variable-form options into a ``VariableForm``."""
        variable_name: str | None = self.options.get("variable-name")
        existing_variable: bool = "existing-variable" in self.options
        both_variable_forms: bool = (
            allow_both and "both-variable-forms" in self.options
        )
        modifiers_value: str | None = self.options.get("modifiers")

        if modifiers_value is not None and variable_name is None:
            msg = "':modifiers:' requires ':variable-name:'."
            raise ExtensionError(message=msg)
        if modifiers_value is not None and existing_variable:
            msg = (
                "':modifiers:' cannot be combined with ':existing-variable:'."
            )
            raise ExtensionError(message=msg)
        if modifiers_value is not None and both_variable_forms:
            msg = (
                "':modifiers:' cannot be combined with "
                "':both-variable-forms:'."
            )
            raise ExtensionError(message=msg)
        if both_variable_forms and variable_name is None:
            msg = "':both-variable-forms:' requires ':variable-name:'."
            raise ExtensionError(message=msg)
        if both_variable_forms and existing_variable:
            msg = (
                "':both-variable-forms:' cannot be combined with "
                "':existing-variable:'."
            )
            raise ExtensionError(message=msg)

        if variable_name is None:
            return None

        modifiers: frozenset[enum.Enum] = (
            frozenset()
            if modifiers_value is None
            else _parse_modifiers(
                language_name=language_name,
                language_cls=language_cls,
                value=modifiers_value,
            )
        )

        if existing_variable:
            return ExistingVariable(name=variable_name)
        if both_variable_forms:
            return BothVariableForms(name=variable_name, modifiers=modifiers)
        return NewVariable(name=variable_name, modifiers=modifiers)

    def _resolve_collection_layout(self) -> CollectionLayout:
        """Resolve the nested collection layout option."""
        collection_layout_value: str = self.options.get(
            "collection-layout",
            "compact",
        )
        return CollectionLayout[collection_layout_value.upper()]

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
        precedence: list[str] = (
            self.env.config.literalizer_heterogeneous_strategy_precedence
        )
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
        hs_value: str | None = self.options.get("heterogeneous-strategy")
        skip = "skip-if-unrepresentable" in self.options

        if hs_value == _AUTO_STRATEGY:
            attempts: list[str | None] = [
                None,
                *self._auto_precedence(language_cls=language_cls),
            ]
        else:
            attempts = [hs_value]

        for index, strategy_value in enumerate(iterable=attempts):
            is_last = index == len(attempts) - 1
            language_spec = self._build_language(
                language_name=language_name,
                language_cls=language_cls,
                heterogeneous_strategy_value=strategy_value,
            )
            try:
                return render(language_spec), language_spec
            except HeterogeneousCollectionError as exc:
                if hs_value == _AUTO_STRATEGY and not is_last:
                    continue
                if skip:
                    return None
                raise ExtensionError(message=str(object=exc)) from exc
            except UnrepresentableInputError as exc:
                if skip:
                    return None
                raise ExtensionError(message=str(object=exc)) from exc
            except _USER_FACING_LITERALIZER_ERRORS as exc:
                raise ExtensionError(message=str(object=exc)) from exc
        # ``attempts`` is always non-empty, so the loop always returns or
        # raises; this is unreachable and only satisfies the type checker.
        msg = "no heterogeneous strategy produced a result"
        raise ExtensionError(message=msg)


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
           :default-set-element-type: String
           :default-sequence-element-type: String
           :default-dict-key-type: String
           :default-dict-value-type: String
           :default-ordered-map-value-type: any
           :modifiers: public,static,final
           :module-name: MyModule
           :record-struct-name-prefix: Record
           :record-shape-names: x,y=Point; a,b,c=Vec3
           :skip-if-unrepresentable:
           :wrap-in-file:
           :ref-case: camel
           :ref-key: $reference
           :collection-layout: multiline

    ``:heterogeneous-strategy: auto`` renders the input with its natural
    representation and, only if that raises because the data is
    heterogeneous, retries with each strategy the target language
    supports in the order configured by the
    ``literalizer_heterogeneous_strategy_precedence`` config value
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

    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        **_COMMON_OPTIONS,
        "include-delimiters": directives.flag,
        "variable-name": directives.unchanged,
        "existing-variable": directives.flag,
        "both-variable-forms": directives.flag,
        "modifiers": directives.unchanged,
    }

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce a literal block."""
        env = self.state.document.settings.env
        data_path = (Path(env.srcdir) / self.arguments[0]).resolve()

        env.note_dependency(str(object=data_path))

        language_name: str = self.options["language"]
        language_cls = _language_types()[language_name]

        pre_indent_level: int = self.options.get("pre-indent-level", 0)
        include_delimiters: bool = "include-delimiters" in self.options
        include_preamble: bool = "include-preamble" in self.options
        variable_form = self._resolve_variable_form(
            language_name=language_name,
            language_cls=language_cls,
            allow_both=True,
        )
        wrap_in_file: bool = "wrap-in-file" in self.options
        ref_case, ref_key = self._resolve_ref_options()
        collection_layout = self._resolve_collection_layout()

        input_format = self._resolve_input_format(data_path=data_path)
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
                collection_layout=collection_layout,
            )

        rendered = self._render_with_strategy(
            language_name=language_name,
            language_cls=language_cls,
            render=_do,
        )
        if rendered is None:
            return []
        result, _ = rendered
        parts: list[str] = []
        if include_preamble and result.preamble:
            parts.append("\n".join(result.preamble))
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
           :omit-code:
           :ref-case: camel
           :ref-key: $reference
           :module-name: MyModule
           :record-struct-name-prefix: Record
           :record-shape-names: x,y=Point; a,b,c=Vec3
           :consumable-refs: my_var,other_var
           :collection-layout: multiline
           :heterogeneous-strategy: auto
           :skip-if-unrepresentable:
           :variable-name: my_data
           :existing-variable:
           :modifiers: public,static

    ``:call-transform:`` substitutes these placeholders in the template:
    ``$call`` (and the ``$0`` alias) for the rendered call expression,
    ``$index`` for the zero-based call position, and ``$zipped`` for the
    matching ``:zip-file:`` element rendered as a native literal (empty
    when no ``:zip-file:`` is given).

    ``:comment-file:`` is a text file with one line per generated call;
    each non-blank line is emitted as a trailing source comment after
    that call (using the target language's comment syntax), and a blank
    line emits no comment.  The line count must match the number of
    generated calls.
    """

    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        **_COMMON_OPTIONS,
        "target-function": directives.unchanged_required,
        "parameter-names": directives.unchanged_required,
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

    def _build_call_transform(
        self,
    ) -> Callable[[CallContext], str] | None:
        """Build the ``:call-transform:`` callback from the template.

        ``$index`` and ``$zipped`` are resolved before ``$call`` / ``$0``
        so a placeholder-like substring inside the rendered call
        expression is never re-expanded.
        """
        template: str | None = self.options.get("call-transform")
        if template is None:
            return None
        resolved_template = template

        def _call_transform(context: CallContext) -> str:
            """Substitute call-context placeholders in the template."""
            zipped = "" if context.zipped is None else context.zipped
            result = resolved_template.replace(
                "$index",
                str(object=context.index),
            )
            result = result.replace("$zipped", zipped)
            result = result.replace("$call", context.call)
            return result.replace("$0", context.call)

        return _call_transform

    def _resolve_zip_source(
        self,
    ) -> tuple[str | None, InputFormat | None]:
        """Read the optional ``:zip-file:`` and resolve its format."""
        zip_file_value: str | None = self.options.get("zip-file")
        if zip_file_value is None:
            return None, None
        env = self.state.document.settings.env
        zip_path = (Path(env.srcdir) / zip_file_value).resolve()
        env.note_dependency(str(object=zip_path))
        zip_input_format = self._resolve_format(
            data_path=zip_path,
            option_name="zip-input-format",
        )
        return zip_path.read_text(encoding="utf-8"), zip_input_format

    def _resolve_comment_source(self) -> list[str] | None:
        """Read the optional ``:comment-file:`` as one comment per call.

        Each line becomes one ``comment_source`` entry, paired
        positionally with a generated call; a blank line emits no
        comment for that call.  A trailing newline does not add an
        extra (empty) entry.
        """
        comment_file_value: str | None = self.options.get("comment-file")
        if comment_file_value is None:
            return None
        env = self.state.document.settings.env
        comment_path = (Path(env.srcdir) / comment_file_value).resolve()
        env.note_dependency(str(object=comment_path))
        return comment_path.read_text(encoding="utf-8").splitlines()

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce function call expressions."""
        env = self.state.document.settings.env
        data_path = (Path(env.srcdir) / self.arguments[0]).resolve()

        env.note_dependency(str(object=data_path))

        language_name: str = self.options["language"]
        language_cls = _language_types()[language_name]

        pre_indent_level: int = self.options.get("pre-indent-level", 0)
        include_preamble: bool = "include-preamble" in self.options
        omit_code: bool = "omit-code" in self.options
        target_function: str = self.options["target-function"]
        parameter_names = [
            p.strip() for p in self.options["parameter-names"].split(",")
        ]
        per_element: bool = "per-element" in self.options

        call_transform = self._build_call_transform()

        ref_case, ref_key = self._resolve_ref_options()
        collection_layout = self._resolve_collection_layout()
        variable_form = self._resolve_variable_form(
            language_name=language_name,
            language_cls=language_cls,
            allow_both=False,
        )

        consumable_refs_value: str | None = self.options.get("consumable-refs")
        consumable_refs: frozenset[str] = (
            frozenset()
            if consumable_refs_value is None
            else frozenset(
                r.strip()
                for r in consumable_refs_value.split(sep=",")
                if r.strip()
            )
        )

        zip_source, zip_input_format = self._resolve_zip_source()
        comment_source = self._resolve_comment_source()

        input_format = self._resolve_input_format(data_path=data_path)
        source = data_path.read_text(encoding="utf-8")

        def _do(language_spec: Language) -> LiteralizeResult:
            """Render the calls for *source* with the built language."""
            return literalize_call(
                source=source,
                input_format=input_format,
                language=language_spec,
                target_function=target_function,
                parameter_names=parameter_names,
                call_transform=call_transform,
                zip_source=zip_source,
                zip_input_format=zip_input_format,
                comment_source=comment_source,
                per_element=per_element,
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
            )
        except ParameterCountMismatchError as exc:
            msg = (
                f"':parameter-names:' has {len(parameter_names)} entries "
                f"but the data provides a different number of values: {exc}"
            )
            raise ExtensionError(message=msg) from exc

        if rendered is None:
            return []
        result, language_spec = rendered

        code = result.code
        if pre_indent_level > 0:
            indent = language_spec.indent * pre_indent_level
            code = "\n".join(
                indent + line if line else line for line in code.splitlines()
            )

        parts: list[str] = []
        if include_preamble and result.preamble:
            parts.append("\n".join(result.preamble))
        if not omit_code:
            parts.append(code)
        text = "\n\n".join(parts)

        return self._make_node(
            text=text,
            data_path=data_path,
            language_cls=language_cls,
        )


@beartype
def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the extension with Sphinx."""
    app.add_directive(name="literalizer", cls=LiteralizerDirective)
    app.add_directive(
        name="literalizer-call",
        cls=LiteralizerCallDirective,
    )
    app.add_config_value(
        name="literalizer_heterogeneous_strategy_precedence",
        default=list(_DEFAULT_HETEROGENEOUS_STRATEGY_PRECEDENCE),
        rebuild="env",
        types=frozenset({list, tuple}),
    )
    return {
        "version": version(distribution_name="sphinx-literalizer"),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
