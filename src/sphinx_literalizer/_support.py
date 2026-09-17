"""Option parsing and validation for the Sphinx directives."""

import enum
import json
import re
from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from typing import Required, TypeGuard

from beartype import beartype
from beartype.door import TypeHint
from docutils.parsers.rst import directives
from literalizer import (
    CollectionLayout,
    IdentifierCase,
    InputFormat,
    LanguageCls,
)
from literalizer.exceptions import (
    LiteralizerError,
    ParameterCountMismatchError,
    ParseError,
)
from literalizer.languages import ALL_LANGUAGES
from sphinx.errors import ExtensionError
from typing_extensions import TypedDict

__all__ = (
    "_AUTO_STRATEGY",
    "_COMMON_OPTIONS",
    "_DEFAULT_HETEROGENEOUS_STRATEGY_PRECEDENCE",
    "_DEFAULT_TYPE_OPTIONS",
    "_EXTENSION_TO_INPUT_FORMAT",
    "_FORMAT_OPTION_GETTERS",
    "_HETEROGENEOUS_VALUE_NAME_PARAMETERS",
    "_CommonOptions",
    "_DirectiveError",
    "_LiteralizerCallOptions",
    "_LiteralizerOptions",
    "_OptionValidator",
    "_RawCommonOptions",
    "_RawLiteralizerCallOptions",
    "_RawLiteralizerOptions",
    "_all_formats",
    "_common_option_args",
    "_enum_member",
    "_is_raw_common_options",
    "_is_string_list",
    "_is_string_object_dict",
    "_language_types",
    "_literalize_errors_as_directive_errors",
    "_lookup_format",
    "_make_format_validator",
    "_optional_modifiers",
    "_parse_record_null_substitutions",
    "_parse_record_shape_names",
    "_raw_string_option",
    "_substitute_placeholder",
    "_validated_raw_common_options",
)

type _OptionValidator = Callable[[str], object]


_FormatDefaults = TypedDict(
    "_FormatDefaults",
    {
        "date-format": str,
        "datetime-format": str,
        "sequence-format": str,
        "set-format": str,
        "bytes-format": str,
        "comment-format": str,
        "variable-type-hints": str,
        "declaration-style": str,
        "dict-entry-style": str,
        "dict-format": str,
        "float-format": str,
        "integer-format": str,
        "numeric-literal-suffix": str,
        "numeric-separator": str,
        "numeric-style": str,
        "string-format": str,
        "trailing-comma": str,
        "language-version": str,
        "empty-dict-key": str,
        "heterogeneous-strategy": str,
        "call-style": str,
        "json-type": str,
        "json-rendering": str,
        "record-map-value-typing": str,
        "bool-format": str,
        "annotation-evaluation": str,
        "union-format": str,
    },
    total=False,
)

_CommonRawFields = TypedDict(
    "_CommonRawFields",
    {
        "language": Required[str],
        "input-format": str,
        "pre-indent-level": int,
        "indent": int,
        "indent-char": str,
        "include-preamble": None,
        "preamble-only": None,
        "default-set-element-type": str,
        "default-sequence-element-type": str,
        "default-dict-key-type": str,
        "default-dict-value-type": str,
        "default-ordered-map-value-type": str,
        "module-name": str,
        "multiline-raw-string-delimiter-base": str,
        "record-struct-name-prefix": str,
        "record-shape-names": str,
        "heterogeneous-value-name": str,
        "skip-if-unrepresentable": None,
        "wrap-in-file": None,
        "ref-case": str,
        "ref-key": str,
        "collection-layout": str,
        "variable-name": str,
        "existing-variable": None,
        "modifiers": str,
    },
    total=False,
)


class _RawCommonOptions(_FormatDefaults, _CommonRawFields):  # pylint: disable=duplicate-bases
    """Option values after Docutils applies ``option_spec`` converters."""


_LiteralizerRawFields = TypedDict(
    "_LiteralizerRawFields",
    {
        "include-delimiters": None,
        "both-variable-forms": None,
        "record-null-substitutions": str,
    },
    total=False,
)


class _RawLiteralizerOptions(_RawCommonOptions, _LiteralizerRawFields):  # pylint: disable=duplicate-bases
    """Converted values accepted by ``literalizer``."""


_LiteralizerCallRawFields = TypedDict(
    "_LiteralizerCallRawFields",
    {
        "target-function": str,
        "constructor-class": str,
        "parameter-names": str,
        "per-element": None,
        "call-transform": str,
        "zip-file": str,
        "zip-input-format": str,
        "comment-file": str,
        "consumable-refs": str,
        "omit-code": None,
    },
    total=False,
)


class _RawLiteralizerCallOptions(_RawCommonOptions, _LiteralizerCallRawFields):  # pylint: disable=duplicate-bases
    """Converted values accepted by ``literalizer-call``."""


@beartype
class _DirectiveError(Exception):
    """A failure attributable to a single directive in a document.

    Raised anywhere under a directive's ``run()`` for input the author
    wrote -- a bad option combination, a language that cannot represent
    the data, an unreadable format.  The base directive converts these
    into docutils directive errors, so they are reported with the
    document and line of the offending directive rather than aborting
    the build with an ``ExtensionError`` traceback.

    Failures that are *not* attributable to a directive -- an invalid
    ``conf.py`` value, for instance -- keep raising ``ExtensionError``.
    """

    def __init__(self, *, message: str) -> None:
        """Report *message* as the directive's error text."""
        super().__init__(message)


@beartype
def _is_string_object_dict(value: object, /) -> TypeGuard[dict[str, object]]:
    """Return whether a value is a dictionary with string keys."""
    return TypeHint(hint=dict[str, object]).is_bearable(obj=value)


type _JSONValue = (
    bool | int | float | str | list[_JSONValue] | dict[str, _JSONValue] | None
)


@beartype
def _is_json_object(value: object, /) -> TypeGuard[dict[str, _JSONValue]]:
    """Return whether a value is a JSON object."""
    return TypeHint(hint=dict[str, _JSONValue]).is_bearable(obj=value)


@beartype
def _is_string_list(value: object, /) -> TypeGuard[list[str]]:
    """Return whether a value is a list of strings."""
    return TypeHint(hint=list[str]).is_bearable(obj=value)


@beartype
def _language_name(lang_cls: LanguageCls) -> str:
    """Return the directive language key for a language class."""
    pygments_name = lang_cls.pygments_name
    if pygments_name is None or pygments_name == "text":
        return lang_cls.__name__.lower()
    return pygments_name


@beartype
def _language_owned_enum_members(
    *, lang_cls: LanguageCls, name: str
) -> tuple[enum.Enum, ...]:
    """Return the members of an enum defined only by some language
    classes.

    A language without the enum contributes no members, so the format
    lookup tables derive an option's availability from the language
    class itself rather than a hand-maintained capability table.
    """
    enum_cls = vars(lang_cls).get(name)
    if not isinstance(enum_cls, type) or not issubclass(enum_cls, enum.Enum):
        return ()
    return tuple(enum_cls)


@beartype
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
    "json-rendering": lambda cls: _language_owned_enum_members(
        lang_cls=cls,
        name="JsonRenderings",
    ),
    # ``RecordMapValueTypings`` is shared by the languages that define
    # the option rather than nested in each of their class bodies, so
    # the attribute to look for is the lowercase alias rather than the
    # name of the enum itself.
    "record-map-value-typing": lambda cls: _language_owned_enum_members(
        lang_cls=cls,
        name="record_map_value_typings",
    ),
    "bool-format": lambda cls: cls.BoolFormats,
    "annotation-evaluation": lambda cls: _language_owned_enum_members(
        lang_cls=cls,
        name="AnnotationEvaluations",
    ),
    "union-format": lambda cls: _language_owned_enum_members(
        lang_cls=cls,
        name="UnionFormats",
    ),
}


def _raw_string_option(options: Mapping[str, object], name: str) -> str:
    """Read a converted string option whose name is chosen dynamically."""
    value = options[name]
    if not isinstance(value, str):
        msg = f"Directive option '{name}' must be a string."
        raise TypeError(msg)
    return value


_IDENTIFIER_CASE_VALUES: tuple[str, ...] = tuple(
    sorted(m.name.lower() for m in IdentifierCase)
)
_COLLECTION_LAYOUT_VALUES: tuple[str, ...] = tuple(
    sorted(m.name.lower() for m in CollectionLayout)
)


@beartype
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


@beartype
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
        raise _DirectiveError(message=msg) from None


@beartype
def _enum_member[E: enum.Enum](cls: type[E], value: str) -> E:
    """Look up an enum member by its case-insensitive name.

    Raises a clean ``_DirectiveError`` (rather than the ``KeyError`` from
    a bare ``cls[value.upper()]``) when *value* is not a member name, so
    callers need not rely on an upstream ``directives.choice`` validator
    to constrain the string.
    """
    try:
        return cls[value.upper()]
    except KeyError:
        choices = sorted(member.name.lower() for member in cls)
        detail = (
            f" Choose from: {', '.join(choices)}." if len(choices) > 0 else ""
        )
        msg = f"'{value}' is not a valid value.{detail}"
        raise _DirectiveError(message=msg) from None


@beartype
def _substitute_placeholder(
    match: re.Match[str],
    *,
    replacements: Mapping[str, str],
) -> str:
    """Return the replacement text for a matched call-transform
    placeholder.
    """
    return replacements[match.group()]


@beartype
def _parse_modifiers(
    language_cls: LanguageCls,
    value: str,
) -> frozenset[enum.Enum]:
    """Parse a comma-separated list of modifier names for the language."""
    result: set[enum.Enum] = set()
    for raw in value.split(sep=","):
        name = raw.strip()
        if name == "":
            continue
        result.add(_enum_member(cls=language_cls.Modifiers, value=name))
    return frozenset(result)


@beartype
def _optional_modifiers(
    *, language_cls: LanguageCls, value: str | None
) -> frozenset[enum.Enum]:
    """Parse modifiers, or return an empty set when none were supplied."""
    if value is None:
        return frozenset[enum.Enum]()
    return _parse_modifiers(language_cls=language_cls, value=value)


@beartype
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
        if entry == "":
            continue
        if "=" not in entry:
            msg = (
                f"':record-shape-names:' entry {entry!r} is missing the "
                f"'=' between the comma-separated keys and the name."
            )
            raise _DirectiveError(message=msg)
        keys_part, name = entry.rsplit(sep="=", maxsplit=1)
        keys = frozenset(
            key.strip()
            for key in keys_part.split(sep=",")
            if key.strip() != ""
        )
        name = name.strip()
        if len(keys) == 0 or name == "":
            msg = (
                f"':record-shape-names:' entry {entry!r} must have at "
                f"least one key and a non-empty name."
            )
            raise _DirectiveError(message=msg)
        if keys in result:
            sorted_keys = ", ".join(sorted(keys))
            msg = (
                f"':record-shape-names:' has multiple entries for the "
                f"key set {{{sorted_keys}}}."
            )
            raise _DirectiveError(message=msg)
        result[keys] = name
    return result


@beartype
def _parse_record_null_substitutions(
    value: str,
) -> dict[str, _JSONValue]:
    """Parse the ``:record-null-substitutions:`` JSON object.

    Values replace ``null`` only when it appears in a record field of the
    given name. They are parsed as ordinary JSON values so their type
    inference remains language-neutral.
    """
    try:
        substitutions: object = json.loads(s=value)
    except json.JSONDecodeError as exc:
        msg = (
            "':record-null-substitutions:' must be a valid JSON object: "
            f"{exc.msg}."
        )
        raise _DirectiveError(message=msg) from exc
    if not _is_json_object(substitutions):
        msg = "':record-null-substitutions:' must be a JSON object."
        raise _DirectiveError(message=msg)
    return substitutions


@beartype
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


@beartype
def _heterogeneous_strategy_validator(x: str) -> str:
    """Validate ``:heterogeneous-strategy:``, also accepting ``auto``."""
    return directives.choice(
        argument=x,
        values=(
            _AUTO_STRATEGY,
            *_all_format_values()["heterogeneous-strategy"],
        ),
    )


_COMMON_OPTIONS: dict[str, _OptionValidator] = {
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
    "preamble-only": directives.flag,
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
    "multiline-raw-string-delimiter-base": directives.unchanged_required,
    "record-struct-name-prefix": directives.unchanged_required,
    "record-shape-names": directives.unchanged_required,
    "heterogeneous-value-name": directives.unchanged_required,
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


# Default element/key/value type options, mapped to the literalizer
# constructor parameter each one sets.  Lifted to module scope so the
# typed-options parse boundary and ``_apply_default_type_options`` share
# one source of truth.  Support is derived from constructor field
# presence, like every other option family here: a language declares the
# field exactly when its ``supports_default_*`` flag is ``True``.
_DEFAULT_TYPE_OPTIONS: dict[str, str] = {
    "default-set-element-type": "default_set_element_type",
    "default-sequence-element-type": "default_sequence_element_type",
    "default-dict-key-type": "default_dict_key_type",
    "default-dict-value-type": "default_dict_value_type",
    "default-ordered-map-value-type": "default_ordered_map_value_type",
}


_RAW_STRING_OPTION_NAMES = frozenset(
    {
        "language",
        "input-format",
        "indent-char",
        "module-name",
        "multiline-raw-string-delimiter-base",
        "record-struct-name-prefix",
        "record-shape-names",
        "heterogeneous-value-name",
        "ref-case",
        "ref-key",
        "collection-layout",
        "variable-name",
        "modifiers",
        *_FORMAT_OPTION_GETTERS,
        *_DEFAULT_TYPE_OPTIONS,
    }
)
_RAW_INTEGER_OPTION_NAMES = frozenset({"pre-indent-level", "indent"})
_RAW_FLAG_OPTION_NAMES = frozenset(
    {
        "include-preamble",
        "preamble-only",
        "skip-if-unrepresentable",
        "wrap-in-file",
        "existing-variable",
    }
)


def _is_raw_common_options(value: object, /) -> TypeGuard[_RawCommonOptions]:
    """Validate the shared converted fields before narrowing their
    type.
    """
    if not _is_string_object_dict(value) or not isinstance(
        value.get("language"), str
    ):
        return False
    for name, option in value.items():
        if name in _RAW_STRING_OPTION_NAMES and not isinstance(option, str):
            return False
        if name in _RAW_INTEGER_OPTION_NAMES and not isinstance(option, int):
            return False
        if name in _RAW_FLAG_OPTION_NAMES and option is not None:
            return False
    return True


def _validated_raw_common_options(value: object) -> _RawCommonOptions:
    """Check the merged mapping before treating it as converted
    options.
    """
    if not _is_raw_common_options(value):
        msg = "Invalid merged directive options."
        raise ExtensionError(message=msg)
    return value


# Literalizer exposes the same generated heterogeneous carrier concept
# under language-idiomatic constructor parameter names
# (``..._variant_name`` / ``..._union_name`` / ``..._enum_name``); the
# name a language accepts is discovered from its constructor fields, so
# adding a carrier-capable language upstream needs no change here.
_HETEROGENEOUS_VALUE_NAME_PARAMETERS: tuple[str, ...] = (
    "heterogeneous_value_variant_name",
    "heterogeneous_value_union_name",
    "heterogeneous_value_enum_name",
)


_EXTENSION_TO_INPUT_FORMAT: dict[str, InputFormat] = {
    ".json": InputFormat.JSON,
    ".json5": InputFormat.JSON5,
    ".yaml": InputFormat.YAML,
    ".yml": InputFormat.YAML,
    ".toml": InputFormat.TOML,
}


@beartype
def _format_input_path(*, path: tuple[str | int, ...]) -> str:
    """Render a literalizer input path as a compact locator string.

    Mapping keys join with ``.`` and zero-based sequence indexes render
    as ``[N]``, so the offending value in ``{"tasks": [{"name": ...}]}``
    is located as ``tasks[0].name``.
    """
    rendered = ""
    for element in path:
        if isinstance(element, int):
            rendered += f"[{element}]"
        elif rendered != "":
            rendered += f".{element}"
        else:
            rendered = element
    return rendered


@beartype
@contextmanager
def _literalize_errors_as_directive_errors() -> Generator[None]:
    """Convert user-facing literalizer exceptions into
    ``_DirectiveError``.

    Every public literalizer exception derives from ``LiteralizerError``
    and signals input the directive author wrote -- a bad option
    combination, a language that cannot represent the data.  Surfacing
    them as a clean ``_DirectiveError`` (rather than a traceback) lets
    the build report the offending directive's document and line and
    carry on with the rest of the build.

    A ``ParseError`` carrying a parser position reports it alongside the
    message, so a malformed data file is located by its own line and
    column rather than only by the directive that read it.

    ``ParameterCountMismatchError`` propagates unchanged: the
    ``literalizer-call`` directive catches it itself to add the
    ``:parameter-names:`` count to the message.
    """
    try:
        yield
    except ParameterCountMismatchError:
        raise
    except ParseError as exc:
        message = str(object=exc)
        # ``line`` and ``column`` are the underlying parser's one-based
        # position, set as a pair when the parser supplies one (a
        # position-less parse failure -- e.g. a duplicate JSON key -- has
        # neither).  The directive's document and line stay the reported
        # location; the parser position is appended so an author of a
        # large data file is not left bisecting it by hand.
        if exc.line is not None:
            message = (
                f"{message} (at line {exc.line}, column {exc.column} "
                "of the data file)"
            )
        raise _DirectiveError(message=message) from exc
    except LiteralizerError as exc:
        message = str(object=exc)
        # ``path`` locates the offending value within the input data
        # (``None`` or empty when the error concerns the whole input).
        if exc.path is not None and len(exc.path) > 0:
            locator = _format_input_path(path=exc.path)
            message = f"{message} (at input path '{locator}')"
        raise _DirectiveError(message=message) from exc


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
    preamble_only: bool
    format_options: Mapping[str, str]
    heterogeneous_strategy: str | None
    default_type_options: Mapping[str, str]
    module_name: str | None
    multiline_raw_string_delimiter_base: str | None
    record_struct_name_prefix: str | None
    record_shape_names: str | None
    heterogeneous_value_name: str | None
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
    record_null_substitutions: Mapping[str, _JSONValue] | None


@beartype
@dataclass(frozen=True, kw_only=True)
class _LiteralizerCallOptions(_CommonOptions):
    """Typed options for the ``literalizer-call`` directive."""

    target_name: str
    constructor_call: bool
    parameter_names: str
    per_element: bool
    call_transform: str | None
    zip_file: str | None
    zip_input_format: str | None
    comment_file: str | None
    consumable_refs: str | None
    omit_code: bool


class _CommonOptionArgs(TypedDict, closed=True):
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
    preamble_only: bool
    format_options: Mapping[str, str]
    heterogeneous_strategy: str | None
    default_type_options: Mapping[str, str]
    module_name: str | None
    multiline_raw_string_delimiter_base: str | None
    record_struct_name_prefix: str | None
    record_shape_names: str | None
    heterogeneous_value_name: str | None
    skip_if_unrepresentable: bool
    wrap_in_file: bool
    ref_case: str | None
    ref_key: str
    collection_layout: str
    variable_name: str | None
    existing_variable: bool
    modifiers: str | None


@beartype
def _common_option_args(
    options: _RawCommonOptions,
) -> _CommonOptionArgs:
    """Extract the shared options from a directive's raw ``options``.

    The ``@beartype``-wrapped :class:`_CommonOptions` constructor also
    validates the resulting values at runtime.
    """
    return _CommonOptionArgs(
        language=options["language"],
        input_format=options.get("input-format"),
        pre_indent_level=options.get("pre-indent-level", 0),
        indent=options.get("indent"),
        indent_char=options.get("indent-char"),
        include_preamble="include-preamble" in options,
        preamble_only="preamble-only" in options,
        format_options={
            name: _raw_string_option(options=options, name=name)
            for name in _FORMAT_OPTION_GETTERS
            if name != "heterogeneous-strategy" and name in options
        },
        heterogeneous_strategy=options.get("heterogeneous-strategy"),
        default_type_options={
            name: _raw_string_option(options=options, name=name)
            for name in _DEFAULT_TYPE_OPTIONS
            if name in options
        },
        module_name=options.get("module-name"),
        multiline_raw_string_delimiter_base=options.get(
            "multiline-raw-string-delimiter-base"
        ),
        record_struct_name_prefix=options.get("record-struct-name-prefix"),
        record_shape_names=options.get("record-shape-names"),
        heterogeneous_value_name=options.get("heterogeneous-value-name"),
        skip_if_unrepresentable="skip-if-unrepresentable" in options,
        wrap_in_file="wrap-in-file" in options,
        ref_case=options.get("ref-case"),
        ref_key=options.get("ref-key", "$ref"),
        collection_layout=options.get("collection-layout", "compact"),
        variable_name=options.get("variable-name"),
        existing_variable="existing-variable" in options,
        modifiers=options.get("modifiers"),
    )
