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
   ``elixir``, ``erlang``, ``fsharp``, ``go``, ``groovy``, ``haskell``,
   ``hcl``, ``java``, ``javascript``, ``julia``, ``kotlin``, ``lua``,
   ``matlab``, ``mojo``, ``nim``, ``ocaml``, ``occam``, ``perl``, ``php``,
   ``powershell``, ``python``, ``r``, ``racket``, ``ruby``, ``rust``,
   ``scala``, ``swift``, ``toml``, ``typescript``, ``visual-basic``,
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

``:wrap:`` (optional flag)
   Wrap the output in language-appropriate delimiters
   (``[`` … ``]`` for arrays, ``{`` … ``}`` for dicts).

``:date-format:`` (optional)
   How to render YAML dates and datetimes.  Defaults to ``iso``
   (quoted ISO 8601 strings).  Supported values:

   ``iso``
      Quoted ISO 8601 string (e.g. ``"2024-01-15"``).
   ``python``
      Python constructor (e.g. ``datetime.date(2024, 1, 15)``).
   ``epoch``
      Seconds since Unix epoch for datetimes; ISO for dates.
   ``java-instant``
      ``LocalDate.of(...)`` for dates, ``Instant.parse(...)`` for
      datetimes.
   ``java-zoned``
      ``LocalDate.of(...)`` for dates, ``ZonedDateTime.of(...)`` for
      datetimes.
   ``ruby``
      ``Date.new(...)`` / ``Time.new(...)``.
   ``javascript``
      ``new Date(...)``.
   ``csharp``
      ``new DateOnly(...)`` / ``new DateTime(...)``.
   ``go``
      ``time.Date(...)``.
   ``kotlin``
      ``LocalDate.of(...)`` / ``LocalDateTime.of(...)``.
   ``cpp``
      ``std::chrono`` types.
   ``dart``
      ``DateTime.parse(...)`` for dates and datetimes.
   ``julia``
      ``Date(...)`` / ``DateTime(...)`` constructors.
   ``r``
      ``as.Date(...)`` / ``as.POSIXct(...)`` calls.

``:sequence-format:`` (optional)
   How to render sequences (arrays/lists).  Not all values are valid for
   every language.  Supported values:

   ``tuple``
      Tuple delimiters.  Available for Crystal, Elixir, Erlang, Julia,
      and Python (default for Python).
   ``list``
      List delimiters.  Available for Elixir (default), Erlang (default),
      and Python.
   ``array``
      Array delimiters.  Available for Crystal (default) and Julia
      (default).

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
   name.  Use with ``:wrap:`` to include the collection delimiters.

``:existing-variable:`` (optional flag)
   When combined with ``:variable-name:``, produce an assignment to an
   existing variable (e.g. ``x = ...``) instead of a new variable
   declaration (e.g. ``final x = ...`` in Dart).  Has no effect without
   ``:variable-name:``.

Example
~~~~~~~

Given a file ``data.json`` containing:

.. code-block:: json

   [true, false, 42, "hello"]

The directive:

.. code-block:: rst

   .. literalizer:: data.json
      :language: python
      :wrap:

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
