|project|
=========

|project| is a Sphinx extension for `literalizer`_, which converts JSON data
structures to native language literal syntax (Python, TypeScript, Go, etc.).

Installation
------------

Requires Python |minimum-python-version|\+.

.. code-block:: shell

   pip install sphinx-literalizer


Usage
-----

Add to your Sphinx :file:`conf.py`:

.. code-block:: python

   extensions = [
       # ...
       "sphinx_literalizer",
   ]

Then use the ``literalizer`` directive in your ``.rst`` files:

.. code-block:: rst

   .. literalizer:: path/to/data.json
      :language: python

This reads the JSON file and renders its contents as a native Python literal
in a code block.

Directive options
~~~~~~~~~~~~~~~~~

``:language:`` (required)
   Target language name (Pygments language name).
   Supported values: ``ada``, ``bash``, ``c``, ``clojure``, ``cobol``,
   ``common-lisp``, ``cpp``, ``crystal``, ``csharp``, ``d``, ``dart``,
   ``elixir``, ``erlang``, ``fortran``, ``fsharp``, ``go``, ``groovy``,
   ``haskell``, ``hcl``, ``java``, ``javascript``, ``julia``, ``kotlin``,
   ``lua``, ``matlab``, ``mojo``, ``nim``, ``norg``, ``objective-c``,
   ``ocaml``, ``occam``, ``perl``, ``php``,
   ``powershell``, ``python``, ``r``, ``racket``, ``ruby``, ``rust``,
   ``scala``, ``swift``, ``toml``, ``typescript``, ``vb.net``,
   ``yaml``, ``zig``.

``:pre-indent-level:`` (optional)
   Number of indent levels to prepend to each output line.
   Defaults to ``0``.

``:indent:`` (optional)
   Number of whitespace characters used for one level of indentation.
   Defaults to ``4``.

``:indent-char:`` (optional)
   Type of whitespace for indentation: ``spaces`` (default) or ``tabs``.

``:include-delimiters:`` (optional flag)
   Include collection delimiters in the output
   (``[`` … ``]`` for arrays, ``{`` … ``}`` for dicts).

``:date-format:`` (optional)
   How to render YAML dates.  Not all values are valid for every
   language.  Supported values:

   ``cpp``
      ``std::chrono::year_month_day`` type.
   ``csharp``
      ``new DateOnly(...)`` constructor.
   ``dart``
      ``DateTime.parse(...)`` constructor.
   ``go``
      ``time.Date(...)`` call.
   ``iso``
      Quoted ISO 8601 string (e.g. ``"2024-01-15"``).  This is the
      default for most languages.
   ``java``
      ``LocalDate.of(...)`` constructor.
   ``js``
      ``new Date(...)`` constructor (JavaScript/TypeScript).
   ``julia``
      ``Date(...)`` constructor.
   ``kotlin``
      ``LocalDate.of(...)`` constructor.
   ``objc``
      Objective-C date representation.
   ``php``
      PHP date representation.
   ``python``
      ``datetime.date(...)`` constructor.
   ``r``
      ``as.Date(...)`` call.
   ``ruby``
      ``Date.new(...)`` constructor.
   ``rust``
      ``NaiveDate::from_ymd_opt(...)`` call.
   ``toml``
      TOML date literal.
   ``yaml``
      YAML date literal.

``:datetime-format:`` (optional)
   How to render YAML datetimes.  Not all values are valid for every
   language.  Supported values:

   ``cpp``
      ``std::chrono`` datetime type.
   ``csharp``
      ``new DateTime(...)`` constructor.
   ``dart``
      ``DateTime.parse(...)`` constructor.
   ``epoch``
      Seconds since Unix epoch (e.g. ``1705314600.0``).
   ``go``
      ``time.Date(...)`` call.
   ``instant``
      ``Instant.parse(...)`` (Java).
   ``iso``
      Quoted ISO 8601 string.  This is the default for most languages.
   ``js``
      ``new Date(...)`` constructor (JavaScript/TypeScript).
   ``julia``
      ``DateTime(...)`` constructor.
   ``kotlin``
      ``LocalDateTime.of(...)`` constructor.
   ``objc``
      Objective-C datetime representation.
   ``php``
      PHP datetime representation.
   ``python``
      ``datetime.datetime(...)`` constructor.
   ``r``
      ``as.POSIXct(...)`` call.
   ``ruby``
      ``Time.new(...)`` constructor.
   ``rust``
      ``NaiveDateTime::new(...)`` call.
   ``toml``
      TOML datetime literal.
   ``yaml``
      YAML datetime literal.
   ``zoned``
      ``ZonedDateTime.of(...)`` (Java).

``:sequence-format:`` (optional)
   How to render sequences (arrays/lists).  Not all values are valid for
   every language.  Supported values:

   ``array``
      Array delimiters.  Available for Crystal (default), Julia (default),
      Rust, and many other languages.
   ``cell_array``
      Cell array delimiters.  Available for MATLAB (default).
   ``initializer_list``
      Initializer list.  Available for C++ (default).
   ``list``
      List delimiters.  Available for Elixir (default), Erlang (default),
      Python, and many other languages.
   ``sequence``
      Sequence delimiters.  Available for COBOL (default) and YAML
      (default).
   ``slice``
      Slice delimiters.  Available for Go (default).
   ``table``
      Table delimiters.  Available for Lua (default).
   ``tuple``
      Tuple delimiters.  Available for Crystal, Elixir, Erlang, Julia,
      Python (default for Python), and Rust.
   ``vec``
      Vec macro (``vec![...]``).  Available for Rust (default).
   ``vector``
      Vector delimiters.  Available for Clojure (default).

``:set-format:`` (optional)
   How to render sets (Python only).  Supported values:

   ``set``
      ``{`` … ``}`` set literal (default).
   ``frozenset``
      ``frozenset({`` … ``})`` constructor.

``:bytes-format:`` (optional)
   How to render binary data (Python only).  Supported values:

   ``hex``
      Hex-escaped bytes literal, e.g. ``b"\x48\x65"`` (default).
   ``python``
      Python bytes literal, e.g. ``b"Hello"``.

``:variable-name:`` (optional)
   Wrap the output in a variable declaration or assignment using the given
   name.  Use with ``:include-delimiters:`` to include the collection
   delimiters.

``:existing-variable:`` (optional flag)
   When combined with ``:variable-name:``, produce an assignment to an
   existing variable (e.g. ``x = ...``) instead of a new variable
   declaration (e.g. ``final x = ...`` in Dart).  Has no effect without
   ``:variable-name:``.

``:variable-type-hints:`` (optional)
   Whether to add inline type hints to variable declarations.
   Supported values:

   ``none``
      Bare assignment, e.g. ``my_var = {...}`` (default).
   ``inline``
      With type annotation, e.g. ``my_var: dict[str, Any] = {...}``.
      Currently available for Python only.

``:comment-format:`` (optional)
   How to render comments.  Not all values are valid for every language.
   Supported values:

   ``apostrophe``
      ``'`` comments.  Available for Visual Basic.
   ``block``
      Block comments (``/* ... */`` or equivalent).  Available for C,
      C#, C++, Common Lisp, D, Dart, F#, Go, Groovy, Haskell, HCL,
      Java, JavaScript, Julia, Kotlin, Lua, MATLAB, Nim, Objective-C,
      PHP, PowerShell, Racket, Rust, Scala, Swift, TypeScript.
   ``double_dash``
      ``--`` comments.  Available for Ada, Haskell, Lua, Occam.
   ``double_slash``
      ``//`` comments.  Available for C, C#, C++, D, Dart, F#, Go,
      Groovy, Java, JavaScript, Kotlin, Objective-C, PHP, Rust, Scala,
      Swift, TypeScript, Zig.
   ``exclamation``
      ``!`` comments.  Available for Fortran.
   ``hash``
      ``#`` comments.  Available for Bash, Crystal, Elixir, HCL, Julia,
      Mojo, Nim, Perl, PowerShell, Python, R, Ruby, TOML, YAML.
   ``paren_star``
      ``(* ... *)`` comments.  Available for OCaml.
   ``percent``
      ``%`` comments.  Available for Erlang, MATLAB, Norg.
   ``semicolon``
      ``;`` comments.  Available for Clojure, Common Lisp, Racket.
   ``star_angle``
      ``*>`` comments.  Available for COBOL.

``:declaration-style:`` (optional)
   How to declare variables.  Not all values are valid for every
   language.  Supported values:

   ``assign``
      Plain assignment (``x = ...``).  Available for Crystal, Elixir,
      Erlang, Haskell, HCL, Julia, MATLAB, Mojo, PHP, PowerShell,
      Python, R, Ruby, TOML, YAML.
   ``auto``
      ``auto`` keyword.  Available for C++, D.
   ``block``
      Block-level declaration.  Available for Norg.
   ``const``
      ``const`` keyword.  Available for JavaScript, TypeScript, Zig.
   ``declare``
      Language-specific declaration keyword.  Available for Ada, Bash.
   ``def``
      ``def`` keyword.  Available for Clojure, Groovy.
   ``define``
      ``define`` form.  Available for Racket.
   ``defparameter``
      ``defparameter`` form.  Available for Common Lisp.
   ``dim``
      ``Dim`` keyword.  Available for Visual Basic.
   ``final``
      ``final`` keyword.  Available for Dart.
   ``let``
      ``let`` keyword.  Available for F#, JavaScript, OCaml, Rust,
      Swift.
   ``local``
      ``local`` keyword.  Available for Lua.
   ``my``
      ``my`` keyword.  Available for Perl.
   ``short``
      Short variable declaration (``:=``).  Available for Go.
   ``typed``
      Typed declaration.  Available for C, COBOL, Fortran, Objective-C.
   ``val``
      ``val`` keyword.  Available for Kotlin, Occam, Scala.
   ``var``
      ``var`` keyword.  Available for C#, Java, Nim.

``:dict-format:`` (optional)
   How to render dictionaries / maps.  Not all values are valid for
   every language.  Supported values:

   ``default``
      Language-default dict syntax.  Available for most languages.
   ``dict``
      ``Dict(...)`` constructor.  Available for Julia.
   ``dictionary``
      ``Dictionary`` constructor.  Available for C#.
   ``hash_map``
      ``HashMap`` constructor.  Available for Rust.
   ``map``
      ``Map`` constructor.  Available for C++, JavaScript, Kotlin,
      Scala.
   ``map_of_entries``
      ``Map.ofEntries(...)`` constructor.  Available for Java.
   ``object``
      Object literal syntax.  Available for JavaScript, TypeScript.
   ``struct``
      ``struct`` syntax.  Available for MATLAB.

``:integer-format:`` (optional)
   How to render integer values.  Not all values are valid for every
   language.  Supported values:

   ``decimal``
      Decimal integer literal (default for all languages).
   ``hex``
      Hexadecimal integer literal.  Available for JavaScript.

``:numeric-separator:`` (optional)
   Whether to use numeric separators in integer literals.  Supported
   values:

   ``none``
      No separators (default for all languages).
   ``underscore``
      Underscore separators (e.g. ``1_000_000``).  Available for
      JavaScript.

``:string-format:`` (optional)
   How to render string values.  Supported values:

   ``double``
      Double-quoted strings (default for all languages).
   ``single``
      Single-quoted strings.  Available for JavaScript.

``:trailing-comma:`` (optional)
   Whether to include a trailing comma after the last element in
   collections.  Supported values:

   ``yes``
      Include trailing comma.  Available for C, C++, Crystal, D, Dart,
      Elixir, Go, Groovy, HCL, JavaScript, Julia, Kotlin, Lua, Mojo,
      Objective-C, Perl, PHP, Python, Ruby, Rust, Scala, Swift,
      TypeScript, Zig.
   ``no``
      Omit trailing comma.  Available for Ada, Bash, C#, Clojure,
      COBOL, Common Lisp, Erlang, F#, Fortran, Haskell, Java,
      JavaScript, MATLAB, Nim, Norg, OCaml, Occam, PowerShell, R,
      Racket, TOML, Visual Basic, YAML.

``:line-ending:`` (optional)
   Whether to include semicolons at the end of statements.
   Supported values:

   ``semicolon``
      Include semicolons.  This is the default for all languages.
   ``none``
      Omit semicolons.  Available for JavaScript, TypeScript.

Example
~~~~~~~

Given a file ``data.json`` containing:

.. code-block:: json

   [true, false, 42, "hello"]

The directive:

.. code-block:: rst

   .. literalizer:: data.json
      :language: python
      :include-delimiters:

renders as a code block containing:

.. skip doccmd[pyright]: next

.. code-block:: python

   [
       True,
       False,
       42,
       "hello",
   ]


Reference
---------

.. toctree::
   :maxdepth: 3

   api-reference
   release-process
   changelog
   contributing

.. _literalizer: https://github.com/adamtheturtle/literalizer
