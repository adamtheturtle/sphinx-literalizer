"""Shared native invocation document and rendered-program witnesses."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp

_CONSTRUCTOR = {"constructor": "NativeCounter"}
NATIVE_RECIPE = {
    "function": "checkResult",
    "parameter-types": ["bool", "NSArray"],
    "return-type": "void",
    "arguments": [
        {
            "receiver": {"reference": "counter", "type": "NativeCounter"},
            "selector": "accept:timestamp:",
            "parameter-types": ["NSString", "float"],
            "return-type": "bool",
            "arguments": [{"input": 0}, {"input": 1}],
        },
        {"zipped": True},
    ],
}


def build_native_app(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path, recipe: object
) -> SphinxTestApp:
    """Create a nested document whose recipe/data dependencies are
    local.
    """
    source = tmp_path / "source"
    folder = source / "guide"
    folder.mkdir(parents=True)
    (source / "conf.py").touch()
    files: dict[str, object] = {
        "constructor.json": _CONSTRUCTOR,
        "no-args.json": [[]],
        "recipe.json": recipe,
        "calls.json": [["user_1", 100.0], ["user_2", 101.0]],
        "expected.json": [[True, "first"], [False, "second"]],
    }
    for name, value in files.items():
        _ = (folder / name).write_text(
            data=json.dumps(obj=value), encoding="utf-8"
        )
    _ = (source / "index.rst").write_text(
        data="Native\n======\n\n.. toctree::\n\n   guide/native\n",
        encoding="utf-8",
    )
    _ = (folder / "native.rst").write_text(
        data=dedent(
            text="""\
        Native
        ======

        .. literalizer-group:: objective-c

           .. code-block:: objective-c

              @interface NativeCounter : NSObject {
                  NSInteger _count;
              }
              - (BOOL)accept:(NSString *)userId timestamp:(double)timestamp;
              - (NSInteger)count;
              @end
              @implementation NativeCounter
              - (BOOL)accept:(NSString *)userId timestamp:(double)timestamp {
                  _count++;
                  return [userId isEqualToString:@"user_1"]
                      && timestamp == 100.0;
              }
              - (NSInteger)count { return _count; }
              @end
              static void checkResult(BOOL actual, NSArray *expected) {
                  NSCAssert(actual == [expected[0] boolValue],
                            @"wrong native result");
              }
              int main(void) {
                  @autoreleasepool {

           .. literalizer-invocation:: no-args.json
              :language: objective-c
              :invocation-file: constructor.json
              :variable-name: counter
              :per-element:
              :include-preamble:
              :pre-indent-level: 2

           .. literalizer-invocation:: calls.json
              :language: objective-c
              :invocation-file: recipe.json
              :zip-file: expected.json
              :per-element:
              :include-preamble:
              :pre-indent-level: 2

           .. code-block:: objective-c

                      NSCAssert([counter count] == 2,
                                @"receiver identity changed");
                  }
                  return 0;
              }
        """
        ),
        encoding="utf-8",
    )
    app = make_app(
        srcdir=source, confoverrides={"extensions": ["sphinx_literalizer"]}
    )
    app.build()
    return app


def native_program(app: SphinxTestApp) -> str:
    """Extract exactly the code emitted by Sphinx, including preambles."""
    blocks = list(
        app.env.get_doctree(docname="guide/native").findall(
            condition=nodes.literal_block
        )
    )
    assert all(  # noqa: S101
        block.rawsource == block.astext() for block in blocks
    )
    return "\n\n".join(block.astext() for block in blocks)
