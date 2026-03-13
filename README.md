# sphinx-literalizer

A Sphinx extension for [literalizer](https://github.com/adamtheturtle/literalizer).

Literalizer converts JSON data structures to native language literal syntax (Python, TypeScript, Go, etc.). This extension integrates that capability into Sphinx documentation builds.

## Installation

```bash
pip install sphinx-literalizer
```

## Usage

Add to your Sphinx `conf.py`:

```python
extensions = [
    # ...
    "sphinx_literalizer",
]
```

## Development

```bash
pip install -e ".[dev]"
```

## License

MIT
