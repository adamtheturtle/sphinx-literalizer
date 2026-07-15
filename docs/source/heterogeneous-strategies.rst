.. _heterogeneous-strategies:

Heterogeneous strategies
========================

A *heterogeneous* collection is a list or mapping whose scalar values do not all share a single language-level type -- for example a JSON array ``[1, "hello"]``, which mixes an integer and a string.
Dynamically typed source data routinely contains such collections, but many target languages have no single literal that can hold them.

The ``:heterogeneous-strategy:`` option (on both the ``literalizer`` and ``literalizer-call`` directives -- see :doc:`index`) selects how |project| renders these collections.
This page explains what each strategy emits, when each is appropriate, and which languages expose which strategies.

The default: ``auto``
---------------------

``:heterogeneous-strategy:`` defaults to ``auto``.
``auto`` renders the input with its natural representation first -- so homogeneous and genuinely map-shaped data keep their native form, byte-identical to naming no strategy at all -- and only falls back to a representational strategy when the natural rendering fails because the data is heterogeneous.
Genuinely unrepresentable input still raises after the fallbacks are exhausted, so the "fail loud" safety is preserved exactly where it matters.

``auto`` makes a representation choice implicitly: ``record`` vs ``tuple`` vs ``tagged_enum`` changes the shape of the generated API.
An author who wants a specific representation for pedagogical or clarity reasons should set ``:heterogeneous-strategy:`` explicitly rather than rely on the default.
To keep a mixed-scalar collection a hard build failure instead, set ``:heterogeneous-strategy: error`` explicitly:

.. code-block:: rst

   .. literalizer:: data.json
      :language: rust
      :heterogeneous-strategy: error

with ``data.json`` containing ``[1, "hello"]`` raises an ``ExtensionError`` describing the heterogeneous scalar types.
Without that explicit ``error``, the same input falls back through the configured precedence under ``auto``.

Choosing a strategy
-------------------

``auto`` (the default)
   Let |project| choose.
   The input is rendered with its natural representation first, so homogeneous and genuinely map-shaped data keep their native form, and a strategy is only applied if that natural rendering fails because the data is heterogeneous.
   See `Letting the directive choose: auto`_ below.

``error``
   Keep strict typing.
   Appropriate when mixed-scalar collections in the source data are a mistake you want surfaced rather than rendered.
   This was the default before |project| defaulted ``:heterogeneous-strategy:`` to ``auto``; it must now be set explicitly.

``tagged_enum`` / ``object_variant`` / ``union_type`` / ``interface`` / ``variant``
   Wrap each value in a generated sum type so a *list* (or list-shaped mapping) of mixed scalars round-trips.
   Appropriate when the collection is genuinely a sequence of "one of several scalar types".
   These differ only in the host language's idiom for a tagged union; the modeling is the same.

``record``
   Render a *mapping* whose values mix scalars and containers as a generated ``struct`` declaration plus a matching struct literal.
   Appropriate when the mapping is record-shaped (non-empty, string keys) -- each key becomes a typed field, so values may legitimately differ per field.

``tuple``
   Render a fixed-length list of mixed scalars as the language's native tuple.
   Appropriate when position, not iteration, carries meaning and no extra preamble declaration is wanted.

Strategies are not mutually exclusive across data shapes: the same language may pick ``record`` for a mapping and one of the sum-type strategies for a list.
Each language exposes only the subset listed in `Per-language support`_ below.

Letting the directive choose: ``auto``
--------------------------------------

A realistic project rarely has one strategy that fits every input.
A record-shaped dict needs ``record``; a genuinely map-shaped dict must stay a map; a list of mixed scalars needs a sum type or ``tuple``.
``:heterogeneous-strategy: auto`` removes that per-input decision.

``auto`` renders the input with its **natural representation first**.
If that succeeds -- as it does for homogeneous data and for genuinely map-shaped mappings -- the native output is used unchanged, so ``auto`` never promotes a plain map to a generated record.
Only if the natural rendering fails because the data is heterogeneous does ``auto`` retry, trying each strategy the target language supports in a configured precedence and using the first that represents the data.

The precedence is the ``literalizer_heterogeneous_strategy_precedence`` configuration value (see :doc:`index`), restricted per directive to the strategies the target language exposes.
It defaults to ``record``, ``tuple``, ``tagged_enum``, ``object_variant``, ``variant``, ``union_type``, ``interface``; ``error`` is never a fallback because it is the failure ``auto`` is recovering from.

For example, with :file:`_examples/auto_record.json`:

.. literalinclude:: _examples/auto_record.json
   :language: json

the natural Rust map rendering fails (a ``HashMap`` cannot hold mixed value types), so ``auto`` falls back to ``record``:

.. rest-example::

   .. literalizer:: _examples/auto_record.json
      :language: rust
      :heterogeneous-strategy: auto

The same directive with a homogeneous or map-shaped input emits the native ``HashMap`` instead, with no fallback applied.

Skipping unrepresentable inputs
-------------------------------

Some inputs cannot be represented in some languages even with ``auto`` -- for instance a shape no strategy the language exposes can model.
By default this fails the build, which is correct when every language must render every input.

When a single canonical input is rendered across several languages (typically a Jinja loop over a language list), failing the whole build forces the data-shape knowledge -- "skip Rust for this one" -- into the template or prose.
The ``:skip-if-unrepresentable:`` flag (on both directives) keeps that knowledge in the directive: when the input cannot be represented in the target language, including after ``auto`` exhausts its precedence, the directive emits no node instead of raising.

.. code-block:: rst

   .. literalizer:: data.json
      :language: rust
      :heterogeneous-strategy: auto
      :skip-if-unrepresentable:

Without ``:skip-if-unrepresentable:`` the same unrepresentable input raises an ``ExtensionError`` and fails the build, as before.

Worked examples
---------------

Each example uses ``:include-preamble:`` so the generated declaration is shown alongside the literal.
Without that flag only the literal (the second block) is emitted, and without ``:include-delimiters:`` the literal carries no surrounding collection delimiters.

Most examples render :file:`_examples/mixed_scalars.json`:

.. literalinclude:: _examples/mixed_scalars.json
   :language: json

The ``record`` and ``tuple`` examples use their own input files, shown inline.

``tagged_enum`` (Rust)
~~~~~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. literalizer:: _examples/mixed_scalars.json
      :language: rust
      :heterogeneous-strategy: tagged_enum
      :include-preamble:

``record`` (Go)
~~~~~~~~~~~~~~~

With :file:`_examples/record.json`:

.. literalinclude:: _examples/record.json
   :language: json

.. rest-example::

   .. literalizer:: _examples/record.json
      :language: go
      :heterogeneous-strategy: record
      :include-preamble:

Nested map fallback (Rust)
~~~~~~~~~~~~~~~~~~~~~~~~~~

``record`` keeps a uniform outer record even when maps nested under the same
field have incompatible sibling shapes.  The nested level falls back to the
language's native map representation and value carrier; no ``:json-type:`` or
additional directive option is required.  This is useful for test-case data
such as :file:`_examples/record_nested_maps.json`:

.. literalinclude:: _examples/record_nested_maps.json
   :language: json

The same ``record`` path is available for C#, C++, Go, Java, Kotlin, Rust, and
Scala.  For example, Rust remains standard-library-only:

.. rest-example::

   .. literalizer:: _examples/record_nested_maps.json
      :language: rust
      :heterogeneous-strategy: record
      :include-delimiters:
      :include-preamble:

``tuple`` (Rust)
~~~~~~~~~~~~~~~~

With :file:`_examples/tuple.json`:

.. literalinclude:: _examples/tuple.json
   :language: json

renders (no preamble -- the tuple is a native literal):

.. rest-example::

   .. literalizer:: _examples/tuple.json
      :language: rust
      :heterogeneous-strategy: tuple

``object_variant`` (Nim)
~~~~~~~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. literalizer:: _examples/mixed_scalars.json
      :language: nim
      :heterogeneous-strategy: object_variant
      :include-preamble:

``union_type`` (Dhall)
~~~~~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. literalizer:: _examples/mixed_scalars.json
      :language: dhall
      :heterogeneous-strategy: union_type
      :include-preamble:

``interface`` (V)
~~~~~~~~~~~~~~~~~

.. rest-example::

   .. literalizer:: _examples/mixed_scalars.json
      :language: v
      :heterogeneous-strategy: interface
      :include-preamble:

``variant`` (Mojo)
~~~~~~~~~~~~~~~~~~

.. rest-example::

   .. literalizer:: _examples/mixed_scalars.json
      :language: mojo
      :heterogeneous-strategy: variant
      :include-preamble:

Per-language support
--------------------

``error`` is available for every language; ``auto`` is the default.
The table below lists the additional strategies each language exposes.
Languages not listed support only ``error`` (set explicitly) and ``auto`` (which, with no representational strategy to fall back to, behaves like ``error`` for heterogeneous input).

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Strategy
     - Languages
     - Emits
   * - ``tagged_enum``
     - Rust
     - A generated tagged ``enum`` plus wrapped values.
   * - ``record``
     - C#, C++, Go, Java, Kotlin, Rust, Scala
     - A generated ``struct`` / record declaration plus a matching literal, for record-shaped mappings.
   * - ``tuple``
     - C++, Rust
     - The language's native fixed-length tuple.
   * - ``object_variant``
     - Nim
     - A generated Nim object variant plus tagged values.
   * - ``union_type``
     - Dhall
     - A generated Dhall union type plus tagged values.
   * - ``interface``
     - V
     - A generated V ``interface`` plus wrapped values.
   * - ``variant``
     - Mojo
     - A ``Variant`` alias plus wrapped values.

Selecting a strategy a language does not support raises an ``ExtensionError`` rather than silently falling back, so a typo such as ``:heterogeneous-strategy: tagged_enum`` on a Go directive fails loudly.

This matrix tracks the upstream `literalizer`_ release pinned by |project|; new languages and strategies are announced in the :doc:`changelog`.

.. _literalizer: https://github.com/adamtheturtle/literalizer
