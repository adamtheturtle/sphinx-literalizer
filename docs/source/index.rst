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
   Supported values: ``python``, ``typescript``, ``javascript``, ``go``,
   ``cpp``, ``csharp``, ``ruby``, ``java``, ``kotlin``.

``:prefix:`` (optional)
   Number of whitespace characters to prepend to each output line.
   Defaults to ``0``.

``:prefix-char:`` (optional)
   Type of whitespace for the prefix: ``spaces`` (default) or ``tabs``.

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
