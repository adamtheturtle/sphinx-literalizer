"""Literalizer-call file and style integration tests."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp

from tests.test_helpers import assert_directive_error


def test_literalizer_call_zip_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:zip-file: pairs a parallel data file with the generated calls,
    surfacing each element as ``$zipped`` rendered as a native literal.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    _ = (source_directory / "expected.json").write_text(
        data=json.dumps(obj=["first", "second"]),
    )
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :zip-file: expected.json
           :call-transform: assert $call == $zipped
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    _ = source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           assert my_func(flag=True, count=42, name="hello") == "first"
           assert my_func(flag=False, count=99, name="world") == "second"
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_literalizer_call_comment_file(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """:comment-file: emits one trailing comment per generated call,
    using the target language's comment syntax, with a blank line
    emitting no comment for that call.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    _ = (source_directory / "comments.txt").write_text(data="first case\n\n")
    source_file = source_directory / "index.rst"
    _ = source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :comment-file: comments.txt
    """
        )
    )

    app = make_app(
        srcdir=source_directory,
        confoverrides={"extensions": ["sphinx_literalizer"]},
    )
    app.build()
    assert app.statuscode == 0
    content_html = (app.outdir / "index.html").read_text()
    app.cleanup()

    _ = source_file.write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. code-block:: python

           my_func(flag=True, count=42, name="hello")  # first case
           my_func(flag=False, count=99, name="world")
    """
        )
    )
    expected_app = make_app(srcdir=source_directory)
    expected_app.build()
    assert expected_app.statuscode == 0
    expected_html = (expected_app.outdir / "index.html").read_text()
    expected_app.cleanup()

    assert content_html == expected_html


def test_literalizer_call_comment_file_length_mismatch(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A :comment-file: whose line count does not match the number of
    generated calls is surfaced as a clean directive error.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42, "hello"], [False, 99, "world"]]),
    )
    _ = (source_directory / "comments.txt").write_text(data="only one\n")
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: my_func
           :parameter-names: flag,count,name
           :per-element:
           :comment-file: comments.txt
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
            "comment_source has 1 entry(ies) but 2 call(s) were "
            "generated; the lengths must match"
        ),
    )


def test_literalizer_call_racket(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Racket S-expression calls
    with prefixed keyword arguments.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: racket
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    text = literal_block.astext()
    assert "(process #:flag #t #:count 42)" in text
    assert "(process #:flag #f #:count 99)" in text
    app.cleanup()


def test_literalizer_call_common_lisp(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Common Lisp calls with
    ``:keyword`` arguments.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: common-lisp
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    text = literal_block.astext()
    assert "(process :flag t :count 42)" in text
    assert "(process :flag nil :count 99)" in text
    app.cleanup()


def test_literalizer_call_clojure(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Clojure calls as
    S-expressions with ``:keyword`` arguments.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: clojure
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    text = literal_block.astext()
    assert "(process :flag true :count 42)" in text
    assert "(process :flag false :count 99)" in text
    app.cleanup()


def test_literalizer_call_objective_c(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Objective-C calls as
    positional C-style calls with boxed scalars.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: objective-c
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    text = literal_block.astext()
    assert text == "process(@YES, @42);\nprocess(@NO, @99);"
    app.cleanup()


def test_literalizer_call_perl(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The literalizer-call directive renders Perl calls as positional
    subroutine invocations.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[True, 42], [False, 99]]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: perl
           :target-function: process
           :parameter-names: flag,count
           :per-element:
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
    text = literal_block.astext()
    assert text == (
        "process(JSON::PP::true, 42);\nprocess(JSON::PP::false, 99);"
    )
    app.cleanup()


def test_literalizer_call_ref_case_camel(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``:ref-case: camel`` converts ``{"$ref": "name"}`` identifiers
    to camelCase in the rendered call.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[
                [{"$ref": "user_obj"}, 42],
                [{"$ref": "admin_user"}, 99],
            ],
        ),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: typescript
           :target-function: process
           :parameter-names: user,count
           :per-element:
           :ref-case: camel
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
    text = literal_block.astext()
    expected = (
        "process({ user: userObj, count: 42 });\n"
        "process({ user: adminUser, count: 99 });"
    )
    assert text == expected
    app.cleanup()


def test_literalizer_call_ref_marker(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """``{"$ref": "name"}`` markers at argument positions emit the name
    as a bare identifier rather than formatting it as a literal.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(
            obj=[
                [{"$ref": "user_obj"}, 42],
                [{"$ref": "admin"}, 99],
            ],
        ),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: process
           :parameter-names: user,count
           :per-element:
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
    text = literal_block.astext()
    assert "process(user=user_obj, count=42)" in text
    assert "process(user=admin, count=99)" in text
    app.cleanup()


def test_call_style_positional_typescript(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :call-style: positional option overrides TypeScript's default
    OBJECT style so the call drops the parameter-name object wrapper.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"flag": True, "count": 42}),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: typescript
           :target-function: myFunc
           :parameter-names: obj
           :call-style: positional
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
    text = literal_block.astext()
    assert 'myFunc({"flag": true, "count": 42});' in text
    assert "obj:" not in text
    app.cleanup()


def test_call_style_unsupported_value(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """The :call-style: option rejects values a language does not
    support.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj={"flag": True}),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: f
           :parameter-names: obj
           :call-style: object
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
        message="Language 'python' does not support call-style 'object'.",
    )


def test_literalizer_call_without_per_element_uses_call_style(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Without :per-element:, the call uses the language's call style
    (e.g. Swift's keyword labels) rather than a positional argument.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[1, 2, 3]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: swift
           :target-function: process
           :parameter-names: data
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
    text = literal_block.astext()
    assert "process(data: [1, 2, 3])" in text
    app.cleanup()


def test_parameter_count_mismatch_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """A row whose value count differs from :parameter-names: is a
    directive error instead of a raw traceback.
    """
    source_directory = tmp_path / "source"
    source_directory.mkdir()
    (source_directory / "conf.py").touch()
    _ = (source_directory / "data.json").write_text(
        data=json.dumps(obj=[[1, 2, 3]]),
    )
    _ = (source_directory / "index.rst").write_text(
        data=dedent(
            text="""\
        Test
        ====

        .. literalizer-call:: data.json
           :language: python
           :target-function: f
           :parameter-names: a,b
           :per-element:
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
            "':parameter-names:' has 2 entries but the data provides a different "
            "number of values: Expected 2 parameters but got 3 values"
        ),
    )
