# Next

- Bump `literalizer` to `2026.7.21.1`.
- `:record-shape-names:` now exposes literalizer's externally declared C++ record rendering.
  With `:language-version: cpp14` and `:heterogeneous-strategy: record`, a shape mapping such as `title,done=Task` renders `std::vector<Task>{...}` without emitting a duplicate `struct Task` declaration.
