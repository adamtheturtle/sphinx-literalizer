Changelog
=========

Next
----

- Bumped ``literalizer`` to ``2026.5.13``.
- Removed the ``:line-ending:`` directive option.  Upstream
  ``literalizer`` removed the corresponding ``LineEndings`` enum;
  statement terminators now follow each language's idiomatic default.
- Languages whose ``wrap_in_file`` introduces a named scope (e.g.
  Java, C, C++, D, Erlang, Fortran, F#, Objective-C, Occam,
  SystemVerilog) now require ``:variable-name:`` when ``:wrap-in-file:``
  is set.  Upstream ``literalizer`` raises
  ``WrapInFileWithoutVariableNotSupportedError`` for languages that
  cannot represent a bare value at file-statement scope.
- The ``:variable-type-hints:`` option exposes upstream's new ``safe``
  value, and the previous ``auto`` value is now spelled ``never`` (the
  rendered output is unchanged for languages that did not previously
  distinguish the two).
- The ``:call-style:`` option exposes the new ``curried`` value for
  F#, Haskell, OCaml, and SML.  Elm ``literalizer-call`` output now
  emits curried-application calls in place of the prior tuple form.
- The new upstream typed exceptions raised by directive option
  combinations a language cannot represent
  (``WrapInFileWithoutVariableNotSupportedError``,
  ``WrapCombinedInFileNotSupportedError``,
  ``VariableNameNotSupportedError``, ``UnsupportedCallShapeError``,
  ``UnsupportedIdentifierCaseError``,
  ``DottedCallTargetNotSupportedError``,
  ``DottedCallStubNotSupportedError``,
  ``FreeFunctionCallNotSupportedError``, and
  ``CallArgNotSupportedError``) are now caught and re-raised as
  ``ExtensionError`` so the offending directive is reported as a
  build error rather than a traceback.

2026.05.01.2
------------


- Bumped ``literalizer`` to ``2026.5.1.1``.
- Added ``:collection-layout:`` to both directives, exposing
  literalizer's nested collection layout control.
- Go output now follows literalizer's idiomatic no-semicolon default
  line ending unless ``:line-ending: semicolon`` is selected.

2026.05.01.1
------------


- Added ``:omit-code:`` to ``literalizer-call`` so callers can combine it
  with ``:include-preamble:`` to render imports or other preamble lines
  without also rendering generated calls.

2026.05.01
----------


- Bumped ``literalizer`` to ``2026.5.1``.
- Added ``:ref-key:`` to both directives, exposing literalizer's
  configurable reference marker key.
- Added ``:language-version:`` to both directives, exposing each target
  language's ``VersionFormats`` enum.
- ``Roc`` is now selected with ``:language: roc`` while still using
  ``text`` syntax highlighting.

2026.04.30.3
------------


- Bumped ``literalizer`` to ``2026.4.30.3``.
- New languages Tcl, Nix, SML, V, Wren, and Forth are now available via
  the ``:language:`` option, provided by literalizer's new backends.
- The ``:module-name:`` value is now automatically converted to the
  case expected by the target language (e.g. ``my_module`` becomes
  ``MyModule`` for Java, which requires PascalCase class names), using
  the ``module_name_case`` attribute introduced in literalizer
  ``2026.4.30.3``.

2026.04.30.2
------------


- Bumped ``literalizer`` to ``2026.4.30.2``.
- Added ``:consumable-refs:`` option to the ``literalizer-call`` directive.
  Accepts a comma-separated list of variable names that may be consumed
  (moved) when they appear as ``$ref`` markers in exactly one call argument
  across all rendered calls. For languages such as C++ and Mojo, this causes
  the matching ``std::move``/``^`` transfer to be emitted.

2026.04.30.1
------------


- Added ``:both-variable-forms:`` to the ``literalizer`` directive.
  When combined with ``:variable-name:`` and ``:wrap-in-file:``, it uses
  literalizer's ``BothVariableForms`` to emit both a declaration and an
  assignment in a single output block.

2026.04.30
----------


2026.04.30
----------

- Bumped ``literalizer`` to ``2026.4.30``.

2026.04.29
----------


- Bumped ``literalizer`` to ``2026.4.29``.
- Added ``:wrap-in-file:`` to the ``literalizer`` directive, exposing
  literalizer's ``wrap_in_file`` parameter so generated output can be
  emitted as a self-contained compilable file.
- Added ``:module-name:`` to both directives.  When the selected language
  has a named-scope wrapper (``C``, ``Cpp``, ``D``, ``Erlang``,
  ``Fortran``, ``FSharp``, ``Java``, ``ObjectiveC``, ``Occam``,
  ``SystemVerilog``, ``Ada``, ``Crystal``, ``Scala``, ``Haskell``), the
  value is passed to the language constructor's ``module_name``
  argument.  Languages that do not accept ``module_name`` raise a clear
  ``ExtensionError``.
- ``:ref-case:`` is now also accepted by the ``literalizer`` directive
  (previously only ``literalizer-call``), letting top-level or nested
  ``{"$ref": "name"}`` mappings render as case-converted bare
  identifiers in plain literal output.
- Roc is now available as a ``:language: roc`` target via
  literalizer's new Roc backend.

2026.04.26
----------


- Bumped ``literalizer`` to ``2026.4.24.1``.
- ``literalizer-call`` now accepts ``:ref-case:`` (``snake``, ``camel``,
  ``pascal``, ``upper_snake``, or ``kebab``) to convert
  ``{"$ref": "name"}`` identifiers to the chosen case before rendering.

2026.04.24
----------


2026.04.24
----------


- Bumped ``literalizer`` to ``2026.4.24``.
- ``literalizer-call`` with ``:per-element:`` for Rust now widens
  ``:heterogeneous-strategy: tagged_enum`` scalar wrapping across
  sibling calls at matching argument slots, so a homogeneous sibling
  no longer emits an unwrapped scalar that mismatches the parameter
  type implied by a heterogeneous sibling.

2026.04.23.1
------------


- Bumped ``literalizer`` to ``2026.4.23``.
- ``:heterogeneous-strategy: object_variant`` is now available for Nim,
  auto-generating a Nim object variant in the preamble for dicts,
  lists, or sibling-list pairs that hold scalars of more than one Nim
  type.
- ``:heterogeneous-strategy: union_type`` is now available for Dhall,
  auto-generating a Dhall union type in the preamble for mixed-scalar
  containers.
- ``literalizer-call`` now renders Clojure, Objective-C, and Perl
  calls: Clojure as ``(process :flag true :count 42)``, Objective-C
  as ``process(@YES, @(42));`` with boxed scalars, and Perl as
  ``process(1, 42);``.
- ``literalizer-call`` now recognizes ``{"$ref": "name"}`` markers at
  argument positions in the data file, emitting ``name`` as a bare
  identifier (``process(user=user_obj, count=42)``) rather than
  formatting the marker dict as a literal.  Refs and literal values
  can be mixed in the same call across JSON, JSON5, YAML, and TOML.

2026.04.23
----------


- Added a ``:call-style:`` option to select a non-default call style for
  the ``literalizer-call`` directive (e.g. ``:call-style: positional``
  for TypeScript to render ``myFunc({...})`` instead of
  ``myFunc({ obj: {...} })``).

2026.04.22
----------


2026.04.21.5
------------

- Bumped ``literalizer`` to ``2026.4.21.5``.
- ``:declaration-style: lazy_static`` is now available for Rust,
  wrapping the value in ``std::sync::LazyLock`` so module-level
  ``HashMap``, ``BTreeMap``, ``Vec``, and similar collections can be
  declared with a runtime-initialized literal.
- ``literalizer-call`` now renders Racket and Common Lisp calls as
  S-expressions with prefixed keyword arguments (``(process #:flag #t
  #:count 42)`` and ``(process :flag t :count 42)`` respectively).
- ``literalizer-call`` without ``:per-element:`` now respects the
  language's call style, so Swift gets calls with keyword labels
  (``process(data: [1, 2, 3])``) instead of an unlabeled positional
  argument.

2026.04.21.2
------------


2026.04.21.4
------------

- Bumped ``literalizer`` to ``2026.4.21.4``.
- ``literalizer-call`` now reports a parameter/value count mismatch as
  an ``ExtensionError`` naming the ``:parameter-names:`` option, rather
  than surfacing literalizer's ``ParameterCountMismatchError`` as a
  traceback.
- Picked up the upstream fix for ``pre_indent_level`` interaction with
  ``:variable-name:``: multi-line values are now uniformly indented
  under the declaration rather than inserting the ``pre_indent_level``
  whitespace between ``=`` and the value.

2026.04.21.1
------------


2026.04.21.3
------------

- Bumped ``literalizer`` to ``2026.4.21.3``.
- Added ``:heterogeneous-strategy:`` directive option, exposing
  language-level heterogeneous-scalar strategies such as Rust's
  ``tagged_enum``.

2026.04.21
----------



- Bumped ``literalizer`` to ``2026.4.21.1``.
- Added ``:modifiers:`` directive option for declaring variables with
  language-specific keywords (e.g. ``public,static,final`` for Java).
- Removed the now-unused ``error_on_coercion`` argument from the
  ``literalize`` call, matching the upstream API change.

2026.04.18
----------



- Bumped ``literalizer`` to ``2026.4.18``.

2026.04.15
----------



- Bumped ``literalizer`` to ``2026.4.15``.
- Adopted the new ``variable_form`` parameter (``NewVariable`` / ``ExistingVariable``) replacing ``variable_name`` / ``new_variable``.
- Added ``:numeric-style:`` directive option.

2026.04.14
----------


- Bumped ``literalizer`` to ``2026.4.14``.
- Added support for Nix output language.
- Renamed ``:call-function:`` directive option to ``:target-function:``.
- Renamed ``:call-params:`` directive option to ``:parameter-names:``.

2026.04.06
----------


- Bumped ``literalizer`` to ``2026.4.6``.
- Added ``:input-format:`` directive option for explicit input format selection.
- Added support for TOML (``.toml``) and JSON5 (``.json5``) input files with auto-detection by extension.
- Added support for new output languages: Dhall, Odin, PureScript, Raku, Scheme, and SystemVerilog.
- Fixed handling of languages with no Pygments lexer (``pygments_name=None``).
- Added ``:dict-entry-style:`` directive option.
- Added ``:float-format:`` directive option.
- Added ``:numeric-literal-suffix:`` directive option.
- Added ``:default-ordered-map-value-type:`` directive option.

2026.03.26.2
------------


- Bumped ``literalizer`` to ``2026.3.26.2``.

2026.03.26.1
------------


- Bumped ``literalizer`` to ``2026.3.26.1``.
- Replaced ``:variable-type-hints: inline`` with ``:variable-type-hints: always``
  and ``:variable-type-hints: auto``, matching the upstream API change.
- Added ``:empty-dict-key:`` directive option.

2026.03.26
----------


- Bumped ``literalizer`` to ``2026.3.26``.
- Replaced ``:prefix:`` and ``:prefix-char:`` directive options with
  ``:pre-indent-level:`` and ``:indent-char:``, matching the upstream
  API change from ``line_prefix`` to ``pre_indent_level``.
- Added ``:line-ending:`` directive option.

2026.03.25
----------


- Bumped ``literalizer`` to ``2026.3.25``.
- Passed ``:indent:`` to the language constructor instead of
  ``literalize_yaml``, matching the upstream API change.

2026.03.23
----------


- Bumped ``literalizer`` to ``2026.3.23``.
- ``literalize_yaml`` now returns ``LiteralizeResult``; use ``.code``
  for the rendered text.
- Added ``:declaration-style:`` directive option.
- Added ``:dict-format:`` directive option.
- Added ``:integer-format:`` directive option.
- Added ``:numeric-separator:`` directive option.
- Added ``:string-format:`` directive option.
- Added ``:trailing-comma:`` directive option.

2026.03.22.1
------------


- Bumped ``literalizer`` to ``2026.3.22.1``.
- Renamed ``:wrap:`` directive option to ``:include-delimiters:``.
- Added ``:variable-type-hints:`` directive option.
- Derived language directive keys from ``pygments_name`` instead of a
  hand-maintained mapping.  Renamed ``visual-basic`` to ``vb.net``.
- Used ``pygments_name`` from language classes for syntax highlighting.
- Used ``LanguageCls`` instead of ``HasFormatEnums``.
- Added ``ALL_LANGUAGES`` consistency check.

2026.03.22
----------


2026.03.20.1
------------


- Bumped ``literalizer`` to ``2026.3.20.2``.
- Added support for Objective-C language.
- Added ``array`` sequence format option for Rust.
- Added ``sequence_format`` as a required field for all languages.
  New sequence format values: ``cell_array``, ``initializer_list``,
  ``sequence``, ``slice``, ``table``, ``vector``.

2026.03.20
----------


- Bumped ``literalizer`` to ``2026.3.20.1``.
- Added support for Fortran and Norg languages.
- Added ``vec`` and ``tuple`` sequence format options for Rust.

2026.03.19
----------


- Bumped ``literalizer`` to ``2026.3.19``.
- Added ``:indent:`` directive option for controlling indentation inside
  wrapped delimiters independently of the line prefix.

2026.03.18
----------


- Bumped ``literalizer`` to ``2026.3.18``.
- Added support for Ada, Bash, C, Crystal, D, Elixir, Erlang, F#, Groovy,
  Haskell, Lua, MATLAB, Nim, OCaml, Occam, Perl, PowerShell, Rust, and Zig
  languages.
- Added ``rust`` date format
  (``NaiveDate::from_ymd_opt(...)`` / ``NaiveDateTime::new(...)``).
- Added ``typescript`` date format alias (same as ``javascript``).
- Removed ``php`` date format (PHP uses ISO dates by default; the option
  had no effect).

2026.03.17.1
------------


2026.03.17.2
------------

- Bumped ``literalizer`` to ``2026.3.17.2``.
- Added support for Clojure, Scala, and R languages.
- Added ``r`` date format (``as.Date(...)`` / ``as.POSIXct(...)``).

2026.03.17
----------


2026.03.16.2
------------


2026.03.16.1
------------


- Bumped ``literalizer`` to ``2026.3.16.1``.

2026.03.16
----------


- Bumped ``literalizer`` to ``2026.3.16``.

2026.03.15.4
------------


2026.03.15.3
------------

- Bumped ``literalizer`` to ``2026.3.15.2``.

2026.03.15.2
------------


2026.03.15.1
------------


2026.03.15
----------


2026.03.14.1
------------


2026.03.14
----------


* Initial release.
