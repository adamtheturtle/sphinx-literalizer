.. _heterogeneous-strategies:

Heterogeneous strategies
========================

A *heterogeneous* collection is a list or mapping whose scalar values do not all share a single language-level type -- for example a JSON array ``[1, "hello"]``, which mixes an integer and a string.
Dynamically typed source data routinely contains such collections, but many target languages have no single literal that can hold them.

The ``:heterogeneous-strategy:`` option (on both the ``literalizer`` and ``literalizer-call`` directives -- see :doc:`index`) selects how |project| renders these collections.
This page explains what each strategy emits, when each is appropriate, and which languages expose which strategies.

The default: ``error``
----------------------

Every language defaults to ``error``: a collection that mixes scalar types raises rather than emitting a literal that would not compile.
This is deliberate -- silently coercing ``1`` and ``"hello"`` to a common type would change the data.
The remaining strategies are opt-in, language-specific ways to represent the mixed collection faithfully instead of failing.

The directive:

.. code-block:: rst

   .. literalizer:: data.json
      :language: rust

with ``data.json`` containing ``[1, "hello"]`` raises an ``ExtensionError`` describing the heterogeneous scalar types.

Choosing a strategy
-------------------

``auto``
   Let |project| choose.
   The input is rendered with its natural representation first, so homogeneous and genuinely map-shaped data keep their native form, and a strategy is only applied if that natural rendering fails because the data is heterogeneous.
   See `Letting the directive choose: auto`_ below.

``error``
   Keep strict typing.
   Appropriate when mixed-scalar collections in the source data are a mistake you want surfaced rather than rendered.

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

For example, with ``data.json`` containing ``[{"id": 1, "desc": "x", "blocks": [1, 2]}]``:

.. code-block:: rst

   .. literalizer:: data.json
      :language: rust
      :heterogeneous-strategy: auto

the natural Rust map rendering fails (a ``HashMap`` cannot hold mixed value types), so ``auto`` falls back to ``record`` and renders:

.. code-block:: rust

   Record0 { id: 1, desc: "x", blocks: vec![1, 2] },

The same directive with a homogeneous or map-shaped ``data.json`` emits the native ``HashMap`` instead, with no fallback applied.

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
Without that flag only the literal (the second block) is emitted.

``tagged_enum`` (Rust)
~~~~~~~~~~~~~~~~~~~~~~

With ``data.json`` containing ``[1, "hello"]``:

.. code-block:: rst

   .. literalizer:: data.json
      :language: rust
      :heterogeneous-strategy: tagged_enum
      :include-preamble:

renders:

.. code-block:: rust

   enum Value {
       I32(i32),
       Str(&'static str),
   }

   vec![
       Value::I32(1),
       Value::Str("hello"),
   ]

``record`` (Go)
~~~~~~~~~~~~~~~

With ``data.json`` containing ``{"name": "a", "count": 1, "items": [1, 2]}``:

.. code-block:: rst

   .. literalizer:: data.json
      :language: go
      :heterogeneous-strategy: record
      :include-preamble:

renders:

.. code-block:: go

   package main
   type Record0 struct {
       Name string
       Count int
       Items []int
   }

   Record0{
       Name: "a",
       Count: 1,
       Items: []int{
           1,
           2,
       },
   }

``tuple`` (Rust)
~~~~~~~~~~~~~~~~

With ``data.json`` containing ``[1, "hello", true]``:

.. code-block:: rst

   .. literalizer:: data.json
      :language: rust
      :heterogeneous-strategy: tuple

renders (no preamble -- the tuple is a native literal):

.. code-block:: rust

   (
       1,
       "hello",
       true,
   )

``object_variant`` (Nim)
~~~~~~~~~~~~~~~~~~~~~~~~

With ``data.json`` containing ``[1, "hello"]``:

.. code-block:: rst

   .. literalizer:: data.json
      :language: nim
      :heterogeneous-strategy: object_variant
      :include-preamble:

renders:

.. code-block:: nim

   type
     ValueKind = enum
       vkInt, vkStr
     Value = object
       case kind: ValueKind
       of vkInt: intVal: int
       of vkStr: strVal: string

   @[
       Value(kind: vkInt, intVal: 1),
       Value(kind: vkStr, strVal: "hello")
   ]

``union_type`` (Dhall)
~~~~~~~~~~~~~~~~~~~~~~

With ``data.json`` containing ``[1, "hello"]``:

.. code-block:: rst

   .. literalizer:: data.json
      :language: dhall
      :heterogeneous-strategy: union_type
      :include-preamble:

renders:

.. code-block:: text

   let Value = < Int : Integer | Str : Text > in

   [
     Value.Int +1,
     Value.Str "hello",
   ]

``interface`` (V)
~~~~~~~~~~~~~~~~~

With ``data.json`` containing ``[1, "hello"]``:

.. code-block:: rst

   .. literalizer:: data.json
      :language: v
      :heterogeneous-strategy: interface
      :include-preamble:

renders:

.. code-block:: text

   interface IVal {}

   [
       IVal(1),
       IVal('hello'),
   ]

``variant`` (Mojo)
~~~~~~~~~~~~~~~~~~

With ``data.json`` containing ``[1, "hello"]``:

.. code-block:: rst

   .. literalizer:: data.json
      :language: mojo
      :heterogeneous-strategy: variant
      :include-preamble:

renders:

.. code-block:: text

   from std.utils.variant import Variant
   comptime Value = Variant[Int, String]

   [
       Value(1),
       Value(String("hello")),
   ]

Per-language support
--------------------

``error`` is available for every language and is always the default.
The table below lists the additional strategies each language exposes.
Languages not listed support only ``error``.

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
     - Go, Java, Kotlin, Rust, Scala
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
