"""Sphinx extension for literalizer.

Provides the ``literalizer`` and ``literalizer-call`` directives, which
read data files and render them as native language code blocks.
"""

import enum
import re
from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache, partial
from importlib.metadata import version
from pathlib import Path
from typing import Any, ClassVar, TypedDict

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
    UnrepresentableEmptyDictError,
    UnrepresentableInputError,
    UnrepresentableIntegerError,
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
    "json-type": lambda cls: cls.JsonTypes,
    "bool-format": lambda cls: cls.BoolFormats,
}


# Format options whose enum is defined on *every* language but whose
# constructor keyword only some languages accept.  Membership in the enum
# (which is all ``_lookup_format`` checks) is therefore not enough to know
# the option is applicable, so these are gated on a ``supports_*``
# capability flag -- mirroring :data:`_DEFAULT_TYPE_OPTIONS` -- to raise a
# clean ``ExtensionError`` rather than letting an unexpected keyword reach
# the language constructor as an uncaught ``TypeError``.
_FORMAT_OPTION_SUPPORTS_CHECKS: dict[str, Callable[[LanguageCls], bool]] = {
    "empty-dict-key": lambda cls: cls.supports_empty_dict_key,
    "call-style": lambda cls: cls.supports_call_style,
}


_IDENTIFIER_CASE_VALUES: tuple[str, ...] = tuple(
    sorted(m.name.lower() for m in IdentifierCase)
)
_COLLECTION_LAYOUT_VALUES: tuple[str, ...] = tuple(
    sorted(m.name.lower() for m in CollectionLayout)
)


@cache
def _all_formats() -> dict[str, dict[tuple[str, str], enum.Enum]]:
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
    formats: dict[tuple[str, str], enum.Enum],
) -> enum.Enum:
    """Look up a format enum member by language and value."""
    try:
        return formats[(language_name, format_value)]
    except KeyError:
        msg = (
            f"Language '{language_name}' does not support "
            f"{directive_name} '{format_value}'."
        )
        raise ExtensionError(message=msg) from None


@beartype
def _enum_member[E: enum.Enum](cls: type[E], value: str) -> E:
    """Look up an enum member by its case-insensitive name.

    Raises a clean ``ExtensionError`` (rather than the ``KeyError`` from
    a bare ``cls[value.upper()]``) when *value* is not a member name, so
    callers need not rely on an upstream ``directives.choice`` validator
    to constrain the string.
    """
    try:
        return cls[value.upper()]
    except KeyError:
        choices = sorted(member.name.lower() for member in cls)
        detail = f" Choose from: {', '.join(choices)}." if choices else ""
        msg = f"'{value}' is not a valid value.{detail}"
        raise ExtensionError(message=msg) from None


def _parse_modifiers(
    language_cls: LanguageCls,
    value: str,
) -> frozenset[enum.Enum]:
    """Parse a comma-separated list of modifier names for the language."""
    result: set[enum.Enum] = set()
    for raw in value.split(sep=","):
        name = raw.strip()
        if not name:
            continue
        result.add(_enum_member(cls=language_cls.Modifiers, value=name))
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
# configuration value.  ``error`` is never a fallback -- it is the
# failure that ``auto`` is recovering from.
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


@dataclass(frozen=True, kw_only=True)
class _DefaultTypeOption:
    """Directive option metadata for default element/key/value types."""

    param_name: str
    supports_check: Callable[[LanguageCls], bool]


# Default element/key/value type options, lifted to module scope so the
# typed-options parse boundary and ``_apply_default_type_options`` share
# one source of truth.
_DEFAULT_TYPE_OPTIONS: dict[str, _DefaultTypeOption] = {
    "default-set-element-type": _DefaultTypeOption(
        param_name="default_set_element_type",
        supports_check=lambda cls: cls.supports_default_set_element_type,
    ),
    "default-sequence-element-type": _DefaultTypeOption(
        param_name="default_sequence_element_type",
        supports_check=lambda cls: cls.supports_default_sequence_element_type,
    ),
    "default-dict-key-type": _DefaultTypeOption(
        param_name="default_dict_key_type",
        supports_check=lambda cls: cls.supports_default_dict_key_type,
    ),
    "default-dict-value-type": _DefaultTypeOption(
        param_name="default_dict_value_type",
        supports_check=lambda cls: cls.supports_default_dict_value_type,
    ),
    "default-ordered-map-value-type": _DefaultTypeOption(
        param_name="default_ordered_map_value_type",
        supports_check=lambda cls: cls.supports_default_ordered_map_value_type,
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
    UnrepresentableEmptyDictError,
    UnrepresentableInputError,
    UnrepresentableIntegerError,
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
@dataclass(frozen=True, kw_only=True)
class _CommonOptions:
    """Typed view of the directive options shared by both directives.

    Built once from ``self.options`` (``dict[str, Any]``) at the start of
    ``run()``.  Because the constructor is ``@beartype``-wrapped, every
    field is validated at this single boundary, so the rest of the module
    operates on fully-typed fields instead of ``Any``.

    ``format_options`` and ``default_type_options`` hold the options that
    are applied by iterating :data:`_FORMAT_OPTION_GETTERS` /
    :data:`_DEFAULT_TYPE_OPTIONS`; they map the present option names to
    their (string) values.  ``heterogeneous-strategy`` is excluded from
    ``format_options`` because it is supplied per build attempt (it may be
    the ``auto`` sentinel) -- the raw option value lives in
    ``heterogeneous_strategy`` instead.
    """

    language: str
    input_format: str | None
    pre_indent_level: int
    indent: int | None
    indent_char: str | None
    include_preamble: bool
    format_options: Mapping[str, str]
    heterogeneous_strategy: str | None
    default_type_options: Mapping[str, str]
    module_name: str | None
    record_struct_name_prefix: str | None
    record_shape_names: str | None
    skip_if_unrepresentable: bool
    wrap_in_file: bool
    ref_case: str | None
    ref_key: str
    collection_layout: str
    variable_name: str | None
    existing_variable: bool
    modifiers: str | None


@beartype
@dataclass(frozen=True, kw_only=True)
class _LiteralizerOptions(_CommonOptions):
    """Typed options for the ``literalizer`` directive."""

    include_delimiters: bool
    both_variable_forms: bool


@beartype
@dataclass(frozen=True, kw_only=True)
class _LiteralizerCallOptions(_CommonOptions):
    """Typed options for the ``literalizer-call`` directive."""

    target_function: str | None
    constructor_class: str | None
    parameter_names: str
    per_element: bool
    call_transform: str | None
    zip_file: str | None
    zip_input_format: str | None
    comment_file: str | None
    consumable_refs: str | None
    omit_code: bool


class _CommonOptionArgs(TypedDict):
    """Keyword arguments for the :class:`_CommonOptions` base.

    Mirrors the :class:`_CommonOptions` fields so the per-directive
    factories can splat the shared extraction in a type-safe way; the two
    must be kept in sync.
    """

    language: str
    input_format: str | None
    pre_indent_level: int
    indent: int | None
    indent_char: str | None
    include_preamble: bool
    format_options: Mapping[str, str]
    heterogeneous_strategy: str | None
    default_type_options: Mapping[str, str]
    module_name: str | None
    record_struct_name_prefix: str | None
    record_shape_names: str | None
    skip_if_unrepresentable: bool
    wrap_in_file: bool
    ref_case: str | None
    ref_key: str
    collection_layout: str
    variable_name: str | None
    existing_variable: bool
    modifiers: str | None


@beartype
def _common_option_args(options: dict[str, Any]) -> _CommonOptionArgs:
    """Extract the shared options from a directive's raw ``options``.

    This is the sole place ``self.options``'s ``Any`` values are read;
    the ``@beartype``-wrapped :class:`_CommonOptions` constructor then
    validates them.
    """
    return _CommonOptionArgs(
        language=options["language"],
        input_format=options.get("input-format"),
        pre_indent_level=options.get("pre-indent-level", 0),
        indent=options.get("indent"),
        indent_char=options.get("indent-char"),
        include_preamble="include-preamble" in options,
        format_options={
            name: options[name]
            for name in _FORMAT_OPTION_GETTERS
            if name != "heterogeneous-strategy" and name in options
        },
        heterogeneous_strategy=options.get("heterogeneous-strategy"),
        default_type_options={
            name: options[name]
            for name in _DEFAULT_TYPE_OPTIONS
            if name in options
        },
        module_name=options.get("module-name"),
        record_struct_name_prefix=options.get("record-struct-name-prefix"),
        record_shape_names=options.get("record-shape-names"),
        skip_if_unrepresentable="skip-if-unrepresentable" in options,
        wrap_in_file="wrap-in-file" in options,
        ref_case=options.get("ref-case"),
        ref_key=options.get("ref-key", "$ref"),
        collection_layout=options.get("collection-layout", "compact"),
        variable_name=options.get("variable-name"),
        existing_variable="existing-variable" in options,
        modifiers=options.get("modifiers"),
    )


@beartype
class _BaseLiteralizerDirective(SphinxDirective):  # pylint: disable=abstract-method
    """Shared logic for literalizer directives."""

    required_arguments = 1
    has_content = False

    def _options_with_language_defaults(self) -> dict[str, Any]:
        """Merge configured language defaults with explicit options.

        The literalizer_language_defaults setting contains only shared
        format options, keyed by directive language. Values written on a
        directive override those defaults.
        """
        language_name = self.options["language"]
        configured = self.env.config.literalizer_language_defaults
        defaults = configured.get(language_name, {})
        if not isinstance(defaults, dict):
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
            validated_defaults[option_name] = _COMMON_OPTIONS[option_name](
                value
            )
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
        language_cls = _language_types()[language_name]
        for option_name in _FORMAT_OPTION_GETTERS:
            if option_name == "heterogeneous-strategy":
                value = heterogeneous_strategy_value
            else:
                value = options.format_options.get(option_name)
            if value is not None:
                supports_check = _FORMAT_OPTION_SUPPORTS_CHECKS.get(
                    option_name
                )
                if supports_check is not None and not supports_check(
                    language_cls
                ):
                    msg = (
                        f"Language '{language_name}' does not support "
                        f"'{option_name}'."
                    )
                    raise ExtensionError(message=msg)
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
        for option_name, type_option in _DEFAULT_TYPE_OPTIONS.items():
            value = options.default_type_options.get(option_name)
            if value is not None:
                if not type_option.supports_check(language_cls):
                    msg = (
                        f"Language '{language_name}' does not support "
                        f"'{option_name}'."
                    )
                    raise ExtensionError(message=msg)
                constructor = partial(
                    constructor,
                    **{type_option.param_name: value},
                )
        return constructor

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

        module_name = options.module_name
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

        prefix = options.record_struct_name_prefix
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

        shape_names_value = options.record_shape_names
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
        from, used only for the "cannot determine" error message.
        """
        if explicit is not None:
            return _enum_member(cls=InputFormat, value=explicit)
        suffix = data_path.suffix.lower()
        try:
            return _EXTENSION_TO_INPUT_FORMAT[suffix]
        except KeyError:
            msg = (
                f"Cannot determine input format for '{data_path.name}'. "
                f"Use the :{option_name}: option."
            )
            raise ExtensionError(message=msg) from None

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
        node["language"] = language_cls.pygments_name or "text"
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
        if existing_variable and variable_name is None:
            msg = "':existing-variable:' requires ':variable-name:'."
            raise ExtensionError(message=msg)

        if variable_name is None:
            return None

        modifiers: frozenset[enum.Enum] = (
            frozenset()
            if modifiers_value is None
            else _parse_modifiers(
                language_cls=language_cls,
                value=modifiers_value,
            )
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

        with _literalize_errors_as_extension_errors():
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
            # surrounding converter as a clean ``ExtensionError``.
            language_spec = _build(strategy_value=attempts[-1])
            return render(language_spec), language_spec


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
           :json-type: serde_json_value
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

    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
        **_COMMON_OPTIONS,
        "include-delimiters": directives.flag,
        "variable-name": directives.unchanged,
        "existing-variable": directives.flag,
        "both-variable-forms": directives.flag,
        "modifiers": directives.unchanged,
    }

    def _parse_options(self) -> _LiteralizerOptions:
        """Parse ``self.options`` into the typed options dataclass."""
        options = self._options_with_language_defaults()
        return _LiteralizerOptions(
            **_common_option_args(options=options),
            include_delimiters="include-delimiters" in self.options,
            both_variable_forms="both-variable-forms" in self.options,
        )

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce a literal block."""
        options = self._parse_options()
        env = self.state.document.settings.env
        data_path = (Path(env.srcdir) / self.arguments[0]).resolve()

        env.note_dependency(str(object=data_path))

        language_name = options.language
        language_cls = _language_types()[language_name]

        pre_indent_level = options.pre_indent_level
        include_delimiters = options.include_delimiters
        include_preamble = options.include_preamble
        variable_form = self._resolve_variable_form(
            language_cls=language_cls,
            options=options,
            both_variable_forms=options.both_variable_forms,
        )
        wrap_in_file = options.wrap_in_file
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

    option_spec: ClassVar[dict[str, Callable[[str], Any]] | None] = {
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
                repl=lambda match: replacements[match.group()],
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
        env = self.state.document.settings.env
        zip_path = (Path(env.srcdir) / zip_file_value).resolve()
        env.note_dependency(str(object=zip_path))
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
        env = self.state.document.settings.env
        comment_path = (Path(env.srcdir) / comment_file_value).resolve()
        env.note_dependency(str(object=comment_path))
        return comment_path.read_text(encoding="utf-8").splitlines()

    def _parse_options(self) -> _LiteralizerCallOptions:
        """Parse ``self.options`` into the typed options dataclass."""
        options = self._options_with_language_defaults()
        target_function = self.options.get("target-function")
        constructor_class = self.options.get("constructor-class")
        if target_function is None and constructor_class is None:
            msg = (
                "Use exactly one of ':target-function:' and "
                "':constructor-class:'."
            )
            raise ExtensionError(message=msg)
        if target_function is not None and constructor_class is not None:
            msg = (
                "':target-function:' cannot be combined with "
                "':constructor-class:'."
            )
            raise ExtensionError(message=msg)
        return _LiteralizerCallOptions(
            **_common_option_args(options=options),
            target_function=target_function,
            constructor_class=constructor_class,
            parameter_names=self.options.get("parameter-names", ""),
            per_element="per-element" in self.options,
            call_transform=self.options.get("call-transform"),
            zip_file=self.options.get("zip-file"),
            zip_input_format=self.options.get("zip-input-format"),
            comment_file=self.options.get("comment-file"),
            consumable_refs=self.options.get("consumable-refs"),
            omit_code="omit-code" in self.options,
        )

    @staticmethod
    def _resolve_target_function(
        *,
        language_spec: Language,
        options: _LiteralizerCallOptions,
    ) -> str:
        """Resolve the explicit or constructor-derived call target."""
        target_function = options.target_function
        if target_function is not None:
            return target_function

        constructor_class = options.constructor_class
        if constructor_class is None:  # pragma: no cover
            msg = "target source options are validated during parsing"
            raise AssertionError(msg)
        return language_spec.format_constructor_target(constructor_class)

    def run(self) -> list[nodes.Node]:
        """Read the data file and produce function call expressions."""
        options = self._parse_options()
        env = self.state.document.settings.env
        data_path = (Path(env.srcdir) / self.arguments[0]).resolve()

        env.note_dependency(str(object=data_path))

        language_name = options.language
        language_cls = _language_types()[language_name]

        pre_indent_level = options.pre_indent_level
        include_preamble = options.include_preamble
        omit_code = options.omit_code
        # An empty (or omitted) ``:parameter-names:`` means *no*
        # arguments rather than one empty-named argument: splitting ``""``
        # on ``,`` would yield ``['']`` (a single argument), so the
        # zero-argument call -- e.g. a no-argument constructor bound to
        # ``:variable-name:`` -- would be unreachable.  An empty value
        # therefore parses to ``[]``.
        if options.parameter_names.strip():
            parameter_names = [
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
        consumable_refs: frozenset[str] = (
            frozenset()
            if consumable_refs_value is None
            else frozenset(
                r.strip()
                for r in consumable_refs_value.split(sep=",")
                if r.strip()
            )
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
            target_function = self._resolve_target_function(
                language_spec=language_spec,
                options=options,
            )
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
    app.add_config_value(
        name="literalizer_language_defaults",
        default={},
        rebuild="env",
        types=frozenset({dict}),
    )
    return {
        "version": version(distribution_name="sphinx-literalizer"),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
