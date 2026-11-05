"""Independent emitter settings through real Sphinx directives."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from docutils import nodes
from sphinx.errors import ExtensionError
from sphinx.testing.util import SphinxTestApp

from tests.objective_c_options_support import (
    make_options_app,
    options_programs,
)


def test_composed_options_without_external_commands(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raw combined output uses precise options with no external
    commands.
    """
    app = make_options_app(make_app=make_app, tmp_path=tmp_path)
    with monkeypatch.context() as context:
        context.setenv(name="PATH", value="")
        app.build()
    assert app.warning.getvalue() == ""
    program, helper = options_programs(app=app)
    assert program.count("#import <Foundation/Foundation.h>") == 1
    assert '      @"name" : @"Ada",' in program
    assert "notificationTimestamp:100.0]" in program
    assert 'BOOL actual = [counter shouldSendNotification:@"Ada"\n' in program
    assert (
        "static void process(id _a0, id _a1) {\n  (void)_a0;\n  (void)_a1;\n}"
        in helper
    )
    assert '  @autoreleasepool {\n    process(@"Ada", @100.0);' in helper
    app.cleanup()


def _option_app(  # noqa: PLR0913
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    directive: str,
    language: str,
    options: str,
    defaults: dict[str, str],
) -> SphinxTestApp:
    """Prepare a small source for overrides and located diagnostics."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    _ = (source / "data.json").write_text(data='[["first", "second"]]')
    _ = (source / "recipe.json").write_text(
        data=json.dumps(
            obj={
                "function": "consume",
                "parameter-types": ["NSString", "NSString"],
                "arguments": [{"input": 0}, {"input": 1}],
                "return-type": "void",
            }
        )
    )
    _ = (source / "index.rst").write_text(
        data=(
            f"Options\n=======\n\n.. {directive}:: data.json\n"
            f"   :language: {language}\n{options}"
        )
    )
    return make_app(
        srcdir=source,
        confoverrides={
            "extensions": ["sphinx_literalizer"],
            "literalizer_language_defaults": {language: defaults},
        },
    )


def test_explicit_options_override_defaults(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """False booleans and inline arguments override true/multiline
    defaults.
    """
    app = _option_app(
        make_app=make_app,
        tmp_path=tmp_path,
        directive="literalizer-call",
        language="objective-c",
        options=(
            "   :target-function: process\n   :parameter-names: a,b\n   :per-element:\n"
            "   :wrap-in-file:\n   :indent-file-body: false\n"
            "   :expand-call-stubs: false\n"
        ),
        defaults={"indent-file-body": "true", "expand-call-stubs": "true"},
    )
    app.build()
    assert app.warning.getvalue() == ""
    (block,) = app.env.get_doctree(docname="index").findall(
        condition=nodes.literal_block
    )
    assert "(void)_a0, (void)_a1; }" in block.astext()
    assert '\nprocess(@"first", @"second");' in block.astext()
    app.cleanup()


@pytest.mark.parametrize(argnames="initial_column", argvalues=[0, 20])
def test_native_initial_column_and_overrides(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    initial_column: int,
) -> None:
    """Caller placement participates in automatic argument wrapping."""
    app = _option_app(
        make_app=make_app,
        tmp_path=tmp_path,
        directive="literalizer-invocation",
        language="objective-c",
        options=(
            "   :invocation-file: recipe.json\n   :per-element:\n"
            "   :native-argument-layout: auto\n"
            "   :native-align-selectors: false\n"
            "   :native-continuation-indent: 2\n"
            f"   :initial-column: {initial_column}\n"
        ),
        defaults={
            "native-argument-layout": "multiline",
            "native-column-limit": "40",
        },
    )
    app.build()
    assert app.warning.getvalue() == ""
    (block,) = app.env.get_doctree(docname="index").findall(
        condition=nodes.literal_block
    )
    if initial_column != 0:
        assert (
            block.astext() == 'consume(@"first",\n' + " " * 28 + '@"second");'
        )
    else:
        assert block.astext() == 'consume(@"first", @"second");'
    app.cleanup()


@pytest.mark.parametrize(
    argnames=("language", "option", "message"),
    argvalues=[
        (
            "python",
            "expand-call-stubs: true",
            "does not support 'expand-call-stubs'",
        ),
        (
            "python",
            "native-argument-layout: multiline",
            "native-argument-layout",
        ),
        (
            "objective-c",
            "initial-column: 4",
            "requires a literalizer-invocation",
        ),
        ("objective-c", "native-column-limit: 0", "must be positive"),
        ("objective-c", "native-continuation-indent: -1", "negative value"),
        (
            "objective-c",
            "native-align-selectors: maybe",
            "invalid option value",
        ),
    ],
)
def test_unsupported_or_invalid_options_are_located(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    language: str,
    option: str,
    message: str,
) -> None:
    """Invalid options point at their document and input file."""
    app = _option_app(
        make_app=make_app,
        tmp_path=tmp_path,
        directive="literalizer",
        language=language,
        options=f"   :{option}\n",
        defaults={},
    )
    app.build()
    warning = app.warning.getvalue()
    assert "index.rst:" in warning
    assert "data.json" in warning
    assert message in warning
    app.cleanup()


def test_invalid_scalar_default_is_configuration_error(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
) -> None:
    """Configuration errors identify the invalid default option."""
    app = _option_app(
        make_app=make_app,
        tmp_path=tmp_path,
        directive="literalizer",
        language="objective-c",
        options="",
        defaults={"native-column-limit": "0"},
    )
    with pytest.raises(
        expected_exception=ExtensionError,
        match="Invalid language default 'native-column-limit'",
    ):
        app.build()
    app.cleanup()
