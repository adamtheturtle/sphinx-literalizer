Bump ``literalizer`` to ``2026.5.28``, and expose the new ``:json-type:`` and ``:bool-format:`` directive options.
``:json-type:`` routes values through a JSON-value type -- e.g. ``serde_json::Value``, ``nlohmann::json``, ``com.fasterxml.jackson.databind.JsonNode``, ``Yojson.Safe.t`` -- on the languages that support it, so heterogeneous data renders without a heterogeneous-strategy fallback.
``:bool-format:`` selects Perl boolean variants (``integer``, ``json_pp_ref``, ``json_pp_singleton``).
The new ``UnrepresentableEmptyDictError`` and ``UnrepresentableIntegerError`` raised by ``literalizer`` are surfaced as ``ExtensionError`` and honoured by ``:skip-if-unrepresentable:``.
