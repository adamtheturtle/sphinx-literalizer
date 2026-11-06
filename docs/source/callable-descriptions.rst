Callable descriptions in Jinja text
-----------------------------------

Enable ``sphinx_jinja2`` alongside ``sphinx_literalizer`` to use the ``literalizer_callable`` filter inside prose or text code blocks.
Keep question-specific descriptions in a JSON file, for example ``callables.json`` next to the guide:

.. code-block:: json

    {
        "accept": {
            "default": {
                "name": "accept",
                "parameter-names": ["value"]
            },
            "languages": {
                "objective-c": {"selector": "accept:"}
            }
        }
    }

Then insert the same description for each language:

.. code-block:: rst

    .. jinja:: languages

       .. code-block:: text

          Implement {{ "callables.json" | literalizer_callable("accept", language) }}.

The filter renders ``accept(value)`` for Python and ``accept:`` for Objective-C without sample argument values or implementations.
File paths are relative to the document containing the Jinja directive, and Sphinx tracks the JSON file as a dependency so metadata edits trigger incremental rebuilds.
No callable names or descriptions belong in ``conf.py``.

Language keys match the directive language keys.
The default name and parameter names can be canonical identifiers.
Pass existing naming functions through ``name_renamer`` and ``parameter_renamer``; explicit language overrides take precedence, and selectors and ``return-annotation`` remain exact display spellings.
For example, expose a generic mapping of naming functions in your Jinja context and select policies from language configuration:

.. code-block:: rst

    {{ "callables.json" | literalizer_callable("accept", language, name_renamer=renamers[method_style], parameter_renamer=renamers[variable_style]) }}

Both callbacks are optional and accept and return a string.
Omitting one preserves the corresponding default spelling.
This reuses the project's naming functions without repeating mechanical casing overrides in each JSON file.
``space-before-paren`` and ``space-after-paren`` are optional boolean presentation settings; selectors are validated against parameter count.
Descriptions and language overrides follow Literalizer's ``describe_callable`` schema.

The extension preserves existing Jinja filters and rejects a conflicting ``literalizer_callable`` filter.
Loading ``sphinx-jinja2`` is optional, and extension order does not matter.
As with other callable Jinja filters, Sphinx may warn that the configuration cannot be cached; suppress ``config.cache`` if that warning is expected in your build.
