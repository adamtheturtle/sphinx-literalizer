"""A composed program rendered with individual Objective-C options."""

import json
from collections.abc import Callable
from pathlib import Path
from textwrap import dedent

from docutils import nodes
from sphinx.testing.util import SphinxTestApp


def make_options_app(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> SphinxTestApp:
    """Prepare literal, helper, and native fragments for a real build."""
    source = tmp_path / "source"
    source.mkdir()
    (source / "conf.py").touch()
    files: dict[str, object] = {
        "data.json": {"name": "Ada", "values": [1, 2]},
        "calls.json": [["Ada", 100.0]],
        "recipe.json": {
            "receiver": {"reference": "counter", "type": "Counter"},
            "selector": "shouldSendNotification:notificationTimestamp:",
            "parameter-types": ["NSString", "float"],
            "return-type": "bool",
            "arguments": [{"input": 0}, {"input": 1}],
        },
    }
    for name, value in files.items():
        _ = (source / name).write_text(
            data=json.dumps(obj=value), encoding="utf-8"
        )
    _ = (source / "index.rst").write_text(
        data=dedent(
            text="""\
        Options
        =======

        .. combined-code-block:: objective-c

           .. literalizer-group:: objective-c

              .. code-block:: objective-c

                 @interface Counter : NSObject
                 - (BOOL)shouldSendNotification:(NSString *)name
                          notificationTimestamp:(double)timestamp;
                 @end
                 @implementation Counter
                 - (BOOL)shouldSendNotification:(NSString *)name
                          notificationTimestamp:(double)timestamp {
                   return [name isEqualToString:@"Ada"] && timestamp == 100.0;
                 }
                 @end
                 int main(void) {
                   @autoreleasepool {
                     Counter *counter = [Counter new];

              .. literalizer:: data.json
                 :language: objective-c
                 :variable-name: payload
                 :pre-indent-level: 2
                 :include-preamble:

              .. literalizer-invocation:: calls.json
                 :language: objective-c
                 :invocation-file: recipe.json
                 :variable-name: actual
                 :per-element:
                 :pre-indent-level: 2
                 :include-preamble:

              .. code-block:: objective-c

                     NSCAssert(actual, @"result");
                     id name = payload[@"name"];
                     NSCAssert([name isEqualToString:@"Ada"], @"data");
                   }
                   return 0;
                 }

        .. literalizer-call:: calls.json
           :language: objective-c
           :target-function: process
           :parameter-names: user,time
           :per-element:
           :wrap-in-file:
           :module-name: main
        """
        ),
        encoding="utf-8",
    )
    return make_app(
        srcdir=source,
        confoverrides={
            "extensions": ["sphinx_literalizer", "sphinx_combine"],
            "literalizer_language_defaults": {
                "objective-c": {
                    "indent": "2",
                    "dict-entry-style": "spaced",
                    "collection-layout": "multiline",
                    "native-collection-layout": "compact",
                    "native-argument-layout": "auto",
                    "native-align-selectors": "true",
                    "native-continuation-indent": "1",
                    "native-column-limit": "80",
                    "indent-file-body": "true",
                    "expand-call-stubs": "true",
                },
            },
        },
    )


def options_programs(app: SphinxTestApp) -> list[str]:
    """Read the actual combined and independently wrapped blocks."""
    blocks = list(
        app.env.get_doctree(docname="index").findall(
            condition=nodes.literal_block
        )
    )
    assert all(block.rawsource == block.astext() for block in blocks)  # noqa: S101
    return [block.astext() for block in blocks]
