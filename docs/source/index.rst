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
