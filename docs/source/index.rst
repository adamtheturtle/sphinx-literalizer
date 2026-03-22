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

``:prefix:`` (optional)
   Number of whitespace characters to prepend to each output line.
   Defaults to ``0``.

``:prefix-char:`` (optional)
   Type of whitespace for the prefix: ``spaces`` (default) or ``tabs``.

``:indent:`` (optional)
   Number of whitespace characters used for indentation inside wrapped
   delimiters.  Uses the same character type as ``:prefix-char:``.
   Defaults to ``4``.

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
