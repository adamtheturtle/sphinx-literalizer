|Build Status| |PyPI|

sphinx-literalizer
==================

``sphinx-literalizer`` is a Sphinx extension for `literalizer`_, which converts
JSON, YAML, TOML, and JSON5 data structures to native language literal syntax
(Python, TypeScript, Go, etc.).

.. contents::
   :local:

Installation
------------

Requires Python |minimum-python-version|\+.

.. code-block:: sh

   pip install sphinx-literalizer


Usage
-----

Add to your Sphinx ``conf.py``:

.. code-block:: python

   extensions = [
       # ...
       "sphinx_literalizer",
   ]

Then use the ``literalizer`` directive in your ``.rst`` files:

.. code-block:: rst

   .. literalizer:: path/to/data.json
      :language: python
      :wrap:

This reads the data file and renders its contents as a native Python literal
in a code block. Input format is auto-detected from the file extension
(``.json``, ``.yaml``/``.yml``, ``.toml``, ``.json5``), or can be set
explicitly with ``:input-format:``.

Full documentation
------------------

See the `full documentation <https://adamtheturtle.github.io/sphinx-literalizer/>`__
for more information including how to contribute.

.. _literalizer: https://github.com/adamtheturtle/literalizer

.. |Build Status| image:: https://github.com/adamtheturtle/sphinx-literalizer/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sphinx-literalizer/actions
.. |PyPI| image:: https://badge.fury.io/py/sphinx-literalizer.svg
   :target: https://badge.fury.io/py/sphinx-literalizer
.. |minimum-python-version| replace:: 3.12
