Callable descriptions in Jinja text
-----------------------------------

Enable ``sphinx_jinja2`` alongside ``sphinx_literalizer`` to use the ``literalizer_callable`` filter inside prose or text code blocks.
Pass the callable name, language, and parameter names directly:

.. code-block:: rst

    .. jinja:: languages

       .. code-block:: text

          Implement {{ "accept" | literalizer_callable(language, ["value"]) }}.

This renders ``accept(value)`` without sample argument values or a function body.
Question-specific names and parameters stay beside the prose that uses them.
The filter does not load metadata files or require question data in ``conf.py``.

Optional keyword arguments are ``selector``, ``return_annotation``, ``space_before_paren``, ``space_after_paren``, ``name_renamer``, ``parameter_renamer``, and ``overrides``.
The spacing options are booleans; naming callbacks accept and return a string.
Omitting a callback preserves the corresponding spelling.
Use existing naming functions from your Jinja context:

.. code-block:: rst

    {{ "accept_value" | literalizer_callable(language, ["item_name"], name_renamer=renamers[method_style], parameter_renamer=renamers[variable_style]) }}

Explicit language overrides take precedence over naming callbacks.
Keys in ``overrides`` match Pygments language IDs, and each override follows Literalizer's ``describe_callable`` schema, using hyphenated field names:

.. code-block:: rst

    {{ "accept" | literalizer_callable(language, ["value"], overrides={"objective-c": {"selector": "accept:", "return-annotation": "BOOL"}}) }}

This renders ``accept(value)`` for Python and ``accept: -> BOOL`` for Objective-C.
Selectors and return annotations keep their exact display spelling; selectors are validated against parameter count.

The extension preserves existing Jinja filters and rejects a conflicting ``literalizer_callable`` filter.
Loading ``sphinx-jinja2`` is optional, and extension order does not matter.
As with other callable Jinja filters, Sphinx may warn that the configuration cannot be cached; suppress ``config.cache`` if that warning is expected in your build.
