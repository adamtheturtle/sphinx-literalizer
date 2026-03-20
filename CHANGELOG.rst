Changelog
=========

Next
----

- Bumped ``literalizer`` to ``2026.3.20``.
- Added support for Mojo and YAML languages.
- Added ``:sequence-format:`` directive option for choosing between
  tuple, list, and array output formats (supported by Crystal, Elixir,
  Erlang, Julia, and Python).
- Added ``:set-format:`` directive option for choosing between set and
  frozenset output (Python only).
- Added ``:bytes-format:`` directive option for choosing between hex and
  Python bytes output (Python only).

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
