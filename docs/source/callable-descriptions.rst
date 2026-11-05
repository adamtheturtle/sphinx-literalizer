Callable descriptions in Jinja text
-----------------------------------

Enable ``sphinx_jinja2`` alongside ``sphinx_literalizer`` to use the ``literalizer_callable`` filter inside prose or text code blocks.
Configure named descriptions in ``conf.py``:

.. code-block:: python

    """Configure shared callable descriptions."""

    literalizer_callable_descriptions = {
        "counter.accept": {
            "default": {
                "name": "accept",
                "parameter-names": ["value"],
            },
            "languages": {
                "objective-c": {"selector": "accept:"},
            },
        },
    }

Then insert the same description for each language:

.. code-block:: rst

    .. jinja:: languages

       .. code-block:: text

          Implement {{ "counter.accept" | literalizer_callable(language) }}.

The filter renders ``accept(value)`` for Python and ``accept:`` for Objective-C without sample argument values or implementations.
Language keys match the directive language keys.
The generic name, parameter names, and optional ``return-annotation`` are explicit display spellings.
``space-before-paren`` and ``space-after-paren`` are optional boolean presentation settings; selectors are validated against parameter count.
Descriptions and language overrides follow Literalizer's ``describe_callable`` schema.

The extension preserves existing Jinja filters and rejects a conflicting ``literalizer_callable`` filter.
Loading sphinx-jinja2 is optional, and extension order does not matter.
As with other callable Jinja filters, Sphinx may warn that the configuration cannot be cached; suppress ``config.cache`` if that warning is expected in your build.
