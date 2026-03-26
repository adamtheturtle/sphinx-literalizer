Changelog
=========

Next
----

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
