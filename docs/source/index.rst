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


Reference
---------

.. toctree::
   :maxdepth: 3

   api-reference
   release-process
   changelog
   contributing

.. _literalizer: https://github.com/adamtheturtle/literalizer
