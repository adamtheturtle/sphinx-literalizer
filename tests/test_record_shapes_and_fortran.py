"""Record-shape and Fortran integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_cpp14_nested_tuple_strategy_uses_standard_tuple_types(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Nested C++14 tuples do not fall back to variant wrappers."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1, "Mainframe1"]]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: tuple
           :include-delimiters:
           :include-preamble:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    output = literal_block.astext()
    assert "std::vector<std::tuple<int, std::string>>" in output
    assert "std::make_tuple(" in output
    assert "LiteralizerVariant" not in output
    app.cleanup()


def test_record_struct_name_prefix_unsupported_language_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:record-struct-name-prefix: with a language that has no record
    strategy is a directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: typescript
           :record-struct-name-prefix: Row
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
            "Language 'typescript' does not support ':record-struct-name-"
            "prefix:'."
        ),
    )


def test_record_shape_names_java(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Java's :record-shape-names: maps a key set to a custom record
    name instead of the auto-generated one.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}, {"x": 3, "y": 4}]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=Point
           :include-delimiters:
           :include-preamble:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "record Point(int x, int y) {}\n"
        "\n"
        "new Point[]{\n"
        "    new Point(1, 2),\n"
        "    new Point(3, 4)\n"
        "}"
    )
    app.cleanup()


def test_record_shape_names_cpp14_external_record(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """C++14 maps a named record shape to a caller-declared struct."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[
                {"title": "Write docs", "done": False},
                {"title": "Review PR", "done": True},
            ],
        ),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\\
        Test
        ====

        .. literalizer:: data.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: record
           :record-shape-names: title,done=Task
           :include-delimiters:
           :include-preamble:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    output = literal_block.astext()
    assert output == (
        "#include <initializer_list>\n"
        "#include <string>\n"
        "#include <vector>\n"
        "\n"
        "std::vector<Task>{\n"
        '    Task{"Write docs", false},\n'
        '    Task{"Review PR", true},\n'
        "}"
    )
    assert "struct Task" not in output
    assert "LiteralizerVariant" not in output
    app.cleanup()


def test_record_shape_names_cpp14_error_external_map_alias(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """C++14 ERROR uses a named map shape as the vector element type."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "expenses.json").write_text(
        data=json.dumps(
            obj=[
                {
                    "expense_id": "001",
                    "trip_id": "001",
                    "amount_usd": "49.99",
                },
            ],
        ),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: expenses.json
           :language: cpp
           :language-version: cpp14
           :heterogeneous-strategy: error
           :record-shape-names: expense_id,trip_id,amount_usd=Expense
           :include-delimiters:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "std::vector<Expense>{\n"
        "    std::map<std::string, std::string>{"
        '{"expense_id", "001"}, {"trip_id", "001"}, '
        '{"amount_usd", "49.99"}},\n'
        "}"
    )
    app.cleanup()


def test_record_shape_names_invalid_name_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A :record-shape-names: name that is not a PascalCase identifier
    is surfaced as a clean directive error, not a traceback.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=point
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
            "record_shape_names entry for keys ['x', 'y'] maps to "
            "'point', which is not a PascalCase Java identifier."
        ),
    )


def test_record_shape_names_malformed_entry_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A :record-shape-names: entry without '=' is a directive error."""
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y
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
            "':record-shape-names:' entry 'x,y' is missing the '=' between the "
            "comma-separated keys and the name."
        ),
    )


def test_record_shape_names_trailing_separator_ignored(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A trailing ';' (or empty entry) in :record-shape-names: is
    skipped rather than treated as a malformed entry.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}, {"x": 3, "y": 4}]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=Point;
           :include-delimiters:
           :include-preamble:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == (
        "record Point(int x, int y) {}\n"
        "\n"
        "new Point[]{\n"
        "    new Point(1, 2),\n"
        "    new Point(3, 4)\n"
        "}"
    )
    app.cleanup()


def test_record_shape_names_empty_name_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A :record-shape-names: entry with keys but an empty name is a
    directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=
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
            "':record-shape-names:' entry 'x,y=' must have at least one key and a"
            " non-empty name."
        ),
    )


def test_record_shape_names_duplicate_key_set_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Two :record-shape-names: entries for the same key set (in any
    key order) are a directive error instead of silently
    keeping only the last name.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: java
           :heterogeneous-strategy: record
           :record-shape-names: x,y=Point; y,x=Other
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
        message="':record-shape-names:' has multiple entries for the key set {x, y}.",
    )


def test_record_shape_names_unsupported_language_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:record-shape-names: with a language that does not support it
    (e.g. Python) is a directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[{"x": 1, "y": 2}]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: python
           :heterogeneous-strategy: record
           :record-shape-names: x,y=Point
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
        message="Language 'python' does not support ':record-shape-names:'.",
    )


def test_fortran_language_version_v2003(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Fortran accepts :language-version: v2003 again, defining int64
    via selected_int_kind and real64 via selected_real_kind instead of
    importing them from iso_fortran_env.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2])
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer:: data.json
           :language: fortran
           :language-version: v2003
           :include-delimiters:
           :include-preamble:
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0

    doctree = app.env.get_doctree(docname="index")
    (literal_block,) = doctree.findall(condition=nodes.literal_block)
    assert literal_block.astext() == dedent(
        text="""\
        module fval_m
          implicit none
          integer, parameter :: int64 = selected_int_kind(18)
          integer, parameter :: real64 = selected_real_kind(15, 307)
          integer, parameter :: tag_null = 0
          integer, parameter :: tag_bool = 1
          integer, parameter :: tag_int = 2
          integer, parameter :: tag_real = 3
          integer, parameter :: tag_str = 4
          integer, parameter :: tag_list = 5
          integer, parameter :: tag_map = 6
          integer, parameter :: tag_set = 7
          integer, parameter :: tag_entry = 8
          type :: fval_t
            integer :: tag = tag_null
            logical :: bv = .false.
            integer(kind=int64) :: iv = 0_int64
            real(kind=real64) :: rv = 0.0_real64
            character(len=:), pointer :: sv => null()
            type(fval_t), pointer :: items(:) => null()
          end type fval_t
        contains
          function fnull() result(v)
            type(fval_t) :: v
            v%tag = tag_null
          end function fnull
          function fbool(b) result(v)
            logical, intent(in) :: b
            type(fval_t) :: v
            v%tag = tag_bool
            v%bv = b
          end function fbool
          function fint(n) result(v)
            integer(kind=int64), intent(in) :: n
            type(fval_t) :: v
            v%tag = tag_int
            v%iv = n
          end function fint
          function freal(x) result(v)
            real(kind=real64), intent(in) :: x
            type(fval_t) :: v
            v%tag = tag_real
            v%rv = x
          end function freal
          function fstr(s) result(v)
            character(len=*), intent(in) :: s
            type(fval_t) :: v
            v%tag = tag_str
            allocate(character(len=len(s)) :: v%sv)
            v%sv = s
          end function fstr
          function flist(a) result(v)
            type(fval_t), intent(in) :: a(:)
            type(fval_t) :: v
            v%tag = tag_list
            allocate(v%items(size(a)))
            v%items = a
          end function flist
          function fmap(a) result(v)
            type(fval_t), intent(in) :: a(:)
            type(fval_t) :: v
            v%tag = tag_map
            allocate(v%items(size(a)))
            v%items = a
          end function fmap
          function fset(a) result(v)
            type(fval_t), intent(in) :: a(:)
            type(fval_t) :: v
            v%tag = tag_set
            allocate(v%items(size(a)))
            v%items = a
          end function fset
          function fentry(k, u) result(v)
            character(len=*), intent(in) :: k
            type(fval_t), intent(in) :: u
            type(fval_t) :: v
            v%tag = tag_entry
            allocate(character(len=len(k)) :: v%sv)
            v%sv = k
            allocate(v%items(1))
            v%items(1) = u
          end function fentry
        end module fval_m

        flist([fval_t ::
            fint(1_int64),
            fint(2_int64)
        ])"""
    )
    app.cleanup()
