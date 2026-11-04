"""Scoped reference metadata through real Sphinx builds and Rust."""

import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

import pytest
from docutils import nodes
from sphinx.testing.util import SphinxTestApp


def _build(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    content: str,
) -> SphinxTestApp:
    """Build independent source files in a real document."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "numbers.json").write_text(data="[1, 2]")
    _ = (source / "keyword.json").write_text(data='"tech"')
    _ = (source / "depth.json").write_text(data="2")
    _ = (source / "calls.json").write_text(
        data='[[{"$ref":"numbers"},{"$ref":"keyword"},{"$ref":"depth"}],'
        '[{"$ref":"numbers"},{"$ref":"keyword"},{"$ref":"depth"}]]',
    )
    _ = (source / "single.json").write_text(data='[[{"$ref":"keyword"}]]')
    _ = (source / "index.rst").write_text(
        data="Test\n====\n\n" + dedent(text=content),
    )
    app = make_app(
        srcdir=source,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    return app


def _code(*, app: SphinxTestApp) -> str:
    """Join the actual rendered blocks, without rewriting them."""
    return "\n\n".join(
        block.astext()
        for block in app.env.get_doctree(docname="index").findall(
            condition=nodes.literal_block,
        )
    )


@pytest.mark.parametrize(argnames="sequence", argvalues=["vec", "array"])
@pytest.mark.parametrize(argnames="consumable", argvalues=[False, True])
def test_reference_program_compiles_and_preserves_values(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    sequence: str,
    consumable: bool,
) -> None:
    """Preserve scalar and container values across repeated calls."""
    rust_type = "Vec<i32>" if sequence == "vec" else "[i32; 2]"
    consume_option = ":consumable-refs: numbers" if consumable else ""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content=f"""\
        .. literalizer-group:: rust
           :share-references:

           .. code-block:: rust

              fn consume(numbers: {rust_type}, keyword: &str, depth: i32) {{
                  assert_eq!(numbers.as_slice(), &[1, 2]);
                  assert_eq!(keyword, "tech");
                  assert_eq!(depth, 2);
              }}
              fn main() {{

           .. literalizer:: numbers.json
              :language: rust
              :variable-name: numbers
              :sequence-format: {sequence}

           .. literalizer:: keyword.json
              :language: rust
              :variable-name: keyword
              :sequence-format: {sequence}

           .. literalizer:: depth.json
              :language: rust
              :variable-name: depth
              :sequence-format: {sequence}

           .. literalizer-call:: calls.json
              :language: rust
              :target-function: consume
              :parameter-names: numbers,keyword,depth
              :ref-key: $ref
              :per-element:
              :sequence-format: {sequence}
              {consume_option}

           .. code-block:: rust

              assert_eq!(numbers.as_slice(), &[1, 2]);
              assert_eq!(keyword, "tech");
              assert_eq!(depth, 2);
              }}
        """,
    )
    assert app.warning.getvalue() == ""
    compiler = shutil.which(cmd="rustc")
    assert compiler is not None, (
        "Rust is required for the native integration tests."
    )
    source = tmp_path / "references.rs"
    binary = tmp_path / "references.exe"
    code = _code(app=app)
    _ = source.write_text(data=code)
    _ = subprocess.run(  # noqa: S603
        args=[
            compiler,
            "--edition=2021",
            "--deny=warnings",
            str(object=source),
            "-o",
            str(object=binary),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    _ = subprocess.run(  # noqa: S603
        args=[str(object=binary)],
        check=True,
        capture_output=True,
        timeout=10,
    )
    assert "keyword.clone()" not in code
    assert "depth.clone()" not in code
    assert ("numbers.clone()" in code) == (sequence == "vec")


def test_reference_scope_is_explicit_and_incremental(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Keep context local and refresh it when source data changes."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. literalizer-group:: rust
           :share-references:

           .. literalizer:: keyword.json
              :language: rust
              :variable-name: keyword

           .. literalizer-call:: single.json
              :language: rust
              :target-function: search
              :parameter-names: keyword
              :ref-key: $ref
              :per-element:

        .. literalizer-call:: single.json
           :language: rust
           :target-function: external
           :parameter-names: keyword
           :ref-key: $ref
           :per-element:
        """,
    )
    assert app.warning.getvalue() == ""
    code = _code(app=app)
    assert "search(keyword);" in code
    assert "external(keyword.clone());" in code
    data_file = tmp_path / "source/keyword.json"
    assert data_file in app.env.dependencies["index"]
    _ = data_file.write_text(data='["tech"]')
    # Sphinx compares dependency modification times to the preceding read timestamp.
    # Sphinx records microseconds; filesystem nanoseconds keep the
    # conversion exact and within the Windows timestamp range.
    timestamp = app.env.all_docs["index"] * 1_000 + 2_000_000_000
    os.utime(path=data_file, ns=(timestamp, timestamp))
    app.build()
    assert app.warning.getvalue() == ""
    assert "search(keyword.clone());" in _code(app=app)


def test_reference_names_and_case_conversion(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Match raw names to cased declarations without parsing code."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. literalizer-group:: python
           :share-references:

           .. literalizer:: keyword.json
              :language: python
              :variable-name: Keyword
              :reference-name: keyword

           .. literalizer-call:: single.json
              :language: python
              :target-function: search
              :parameter-names: keyword
              :ref-key: $ref
              :ref-case: pascal
              :call-style: positional
              :per-element:
        """,
    )
    assert app.warning.getvalue() == ""
    assert "search(Keyword)" in _code(app=app)


def test_unknown_external_reference_warning_is_not_suppressed(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The native gate rejects a warning even when Sphinx succeeds."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. code-block:: rust

           fn search(keyword: &str) { assert_eq!(keyword, "tech"); }
           fn main() {

        .. literalizer:: keyword.json
           :language: rust
           :variable-name: keyword

        .. literalizer-call:: single.json
           :language: rust
           :target-function: search
           :parameter-names: keyword
           :ref-key: $ref
           :per-element:

        .. code-block:: rust

           }
        """,
    )
    assert app.warning.getvalue() == ""
    compiler = shutil.which(cmd="rustc")
    assert compiler is not None
    source = tmp_path / "unknown.rs"
    _ = source.write_text(data=_code(app=app))
    result = subprocess.run(  # noqa: S603
        args=[
            compiler,
            "--edition=2021",
            "--deny=warnings",
            str(object=source),
            "-o",
            str(object=tmp_path / "unknown.exe"),
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode != 0
    assert "noop-method-call" in result.stderr


def test_automatic_representation_follows_the_actual_declaration(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A reference-only call retains a selected tuple representation."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. literalizer-group:: rust
           :share-references:

           .. code-block:: rust

              fn consume(value: (&str, i32)) {
                  assert_eq!(value.0, "tech");
                  assert_eq!(value.1, 2);
              }
              fn main() {

           .. literalizer:: keyword.json
              :language: rust
              :variable-name: keyword
              :include-preamble:

           .. literalizer-call:: single.json
              :language: rust
              :target-function: consume
              :parameter-names: keyword
              :ref-key: $ref
              :per-element:

           .. code-block:: rust

              assert_eq!(keyword.0, "tech");
              assert_eq!(keyword.1, 2);
              }
        """,
    )
    _ = (tmp_path / "source/keyword.json").write_text(data='["tech", 2]')
    app.build(force_all=True)
    assert app.warning.getvalue() == ""
    compiler = shutil.which(cmd="rustc")
    assert compiler is not None
    source = tmp_path / "tuple.rs"
    binary = tmp_path / "tuple.exe"
    _ = source.write_text(data=_code(app=app))
    _ = subprocess.run(  # noqa: S603
        args=[
            compiler,
            "--edition=2021",
            "--deny=warnings",
            str(object=source),
            "-o",
            str(object=binary),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    _ = subprocess.run(  # noqa: S603
        args=[str(object=binary)],
        check=True,
        capture_output=True,
        timeout=10,
    )


def test_forward_reference_retains_unknown_behavior(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An opted-in scope does not invent a later declaration's value."""
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. literalizer-group:: rust
           :share-references:

           .. literalizer-call:: single.json
              :language: rust
              :target-function: external
              :parameter-names: keyword
              :ref-key: $ref
              :per-element:

           .. literalizer:: keyword.json
              :language: rust
              :variable-name: keyword
        """,
    )
    assert app.warning.getvalue() == ""
    assert "external(keyword.clone());" in _code(app=app)


def test_ambiguous_automatic_representations_are_rejected(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Different declaration strategies require an explicit common
    form.
    """
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content="""\
        .. literalizer-group:: rust
           :share-references:

           .. literalizer:: numbers.json
              :language: rust
              :variable-name: numbers

           .. literalizer:: keyword.json
              :language: rust
              :variable-name: keyword
              :heterogeneous-strategy: tagged_enum

           .. literalizer-call:: single.json
              :language: rust
              :target-function: consume
              :parameter-names: keyword
              :ref-key: $ref
              :per-element:
        """,
    )
    assert (
        "require one explicit common heterogeneous strategy"
        in app.warning.getvalue()
    )


@pytest.mark.parametrize(
    argnames=("declaration", "call_options", "message"),
    argvalues=[
        (":reference-name: shared", "", "resolves to 'shared'"),
        (
            ":sequence-format: array",
            "",
            "different language representation options",
        ),
        (":existing-variable:", "", "require new variable declarations"),
        (
            ':record-null-substitutions: {"field": 0}',
            "",
            "require new variable declarations",
        ),
        ("", ":language: python", "different language representation options"),
    ],
)
def test_incompatible_reference_context_reports_directive_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    declaration: str,
    call_options: str,
    message: str,
) -> None:
    """Report incompatible declarations at the source directive."""
    call_language = ":language: rust" if call_options == "" else call_options
    app = _build(
        make_app=make_app,
        tmp_path=tmp_path,
        content=f"""\
        .. literalizer-group:: rust
           :share-references:

           .. literalizer:: keyword.json
              :language: rust
              :variable-name: keyword
              {declaration}

           .. literalizer-call:: single.json
              {call_language}
              :target-function: search
              :parameter-names: keyword
              :ref-key: $ref
              :per-element:
        """,
    )
    warning = app.warning.getvalue()
    assert "index.rst:" in warning
    assert message in warning


@pytest.mark.parametrize(
    argnames=("content", "message"),
    argvalues=[
        (
            """\
        .. literalizer:: keyword.json
           :language: rust
           :variable-name: keyword
           :reference-name: keyword
        """,
            "requires a group with :share-references:",
        ),
        (
            """\
        .. literalizer-group:: rust
           :share-references:

           .. literalizer:: keyword.json
              :language: rust
              :reference-name: keyword
        """,
            "requires an emitted variable declaration",
        ),
        (
            """\
        .. literalizer-group:: rust
           :share-references:

           .. literalizer:: keyword.json
              :language: rust
              :variable-name: keyword

           .. literalizer:: keyword.json
              :language: rust
              :variable-name: keyword
        """,
            "Duplicate shared reference declaration",
        ),
        (
            """\
        .. literalizer-group:: rust
           :share-references:

           .. literalizer-group:: rust

              .. code-block:: rust

                 let n = 1;
        """,
            "literalizer-group cannot be nested",
        ),
    ],
)
def test_invalid_shared_reference_declarations(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    """Reject ambiguous or unsupported shared declarations."""
    app = _build(make_app=make_app, tmp_path=tmp_path, content=content)
    assert message in app.warning.getvalue()
