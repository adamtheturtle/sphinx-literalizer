"""Error-reporting integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from sphinx.testing.util import SphinxTestApp
from sphinx.util.console import strip_colors

from tests.test_helpers import assert_directive_error


def test_error_reports_input_path(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """An error tied to one input value reports that value's path.

    literalizer attaches the offending value's input path to its
    errors; the directive error appends it as a compact locator so an
    author can find the value in a large data file.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(
            obj={"tasks": [{"name": "a", "items": [1, "two"]}]},
        ),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: rust
           :heterogeneous-strategy: error
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Collection contains heterogeneous scalar types that cannot "
            "be represented in the target language (found types: int, "
            "str) (at input path 'tasks[0].items')"
        ),
    )
    app.cleanup()


def test_parse_error_reports_position(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A malformed data file reports the parser's line and column.

    literalizer attaches the underlying parser's one-based position to
    its parse errors; the directive error appends it so the author of a
    large data file can jump to the offending line rather than bisecting
    the input by hand.  The directive's own document and line remain the
    reported location.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data='{\n  "a": [1, 2,\n}',
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message=(
            "Invalid JSON: Expecting value at line 3 column 1 "
            "(at line 3, column 1 of the data file)"
        ),
    )
    app.cleanup()


def test_parse_error_without_position(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A parse error without a parser position reports only its message.

    A duplicate JSON key is rejected by literalizer itself rather than
    the underlying parser, so the error carries no line or column and no
    position suffix is appended.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(data='{"a": 1, "a": 2}')
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=4,
        message="Invalid JSON: duplicate key 'a'",
    )
    app.cleanup()


def test_error_reports_directive_line(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A failing directive is reported at its own line in the document.

    The document has a passing directive first so the reported line
    cannot be right by accident: it identifies the failing block rather
    than the first ``literalizer`` block in the file.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python

        Prose between the blocks.

        .. literalizer:: data.json
           :language: python
           :sequence-format: vec
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    assert_directive_error(
        app=app,
        source_directory=source_directory,
        line=9,
        message="Language 'python' does not support sequence-format 'vec'.",
    )
    app.cleanup()


def test_errors_do_not_stop_the_build(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """One build reports every failing directive rather than the first.

    Each error is a document error, so the build carries on and an
    author fixing a large tree sees all of the bad blocks in one run.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :sequence-format: vec

        .. literalizer:: data.json
           :language: rust
           :set-format: frozenset
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    document = source_directory / "index.rst"
    reported = strip_colors(app.warning.getvalue()).splitlines()
    assert reported == [
        (
            f"{document}:4: ERROR: Language 'python' does not support "
            "sequence-format 'vec'. (in 'data.json') [docutils]"
        ),
        (
            f"{document}:8: ERROR: Language 'rust' does not support "
            "set-format 'frozenset'. (in 'data.json') [docutils]"
        ),
    ]
    app.cleanup()


def test_error_names_the_data_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Every directive error ends with the data file the directive read.

    A directive generated inside another directive's content -- a
    ``sphinx-jinja2`` block, say -- is reported against the enclosing
    directive's line, so identical failures over different data files
    would otherwise be indistinguishable.  The path is echoed as the
    directive writes it, which is what an author has to open.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "first.json").write_text(data=json.dumps(obj=[1]))
    nested_directory = source_directory / "nested"
    nested_directory.mkdir()
    _ = (nested_directory / "second.json").write_text(data=json.dumps(obj=[2]))
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: first.json
           :language: python
           :sequence-format: vec

        .. literalizer:: nested/second.json
           :language: python
           :sequence-format: vec
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    document = source_directory / "index.rst"
    reported = strip_colors(app.warning.getvalue()).splitlines()
    assert reported == [
        (
            f"{document}:4: ERROR: Language 'python' does not support "
            "sequence-format 'vec'. (in 'first.json') [docutils]"
        ),
        (
            f"{document}:8: ERROR: Language 'python' does not support "
            "sequence-format 'vec'. (in 'nested/second.json') [docutils]"
        ),
    ]
    app.cleanup()


def test_errors_fail_the_build_with_warnings_as_errors(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A failing directive still fails the build under ``-W``."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(data=json.dumps(obj=[1]))
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :sequence-format: vec
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
        warningiserror=True,
    )
    app.build()
    assert app.statuscode == 1

    document = source_directory / "index.rst"
    reported = strip_colors(app.warning.getvalue()).splitlines()
    assert reported == [
        (
            f"{document}:4: ERROR: Language 'python' does not support "
            "sequence-format 'vec'. (in 'data.json') [docutils]"
        )
    ]
    app.cleanup()
