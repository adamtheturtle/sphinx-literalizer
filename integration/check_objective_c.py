"""Compile and run the exact rendered block in the macOS CI job.

This external compiler witness runs separately from the cross-platform
Python coverage suite, which exercises the shared document builder.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

from sphinx.testing.util import SphinxTestApp

from tests.native_invocation_support import (
    NATIVE_RECIPE,
    build_native_app,
    native_program,
)


def test_native_rendered_program_runs(
    *, make_app: Callable[..., SphinxTestApp], tmp_path: Path
) -> None:
    """The exact rendered program calls real methods with real scalars."""
    app = build_native_app(
        make_app=make_app, tmp_path=tmp_path, recipe=NATIVE_RECIPE
    )
    assert app.warning.getvalue() == ""  # noqa: S101
    source = tmp_path / "native.m"
    binary = tmp_path / "native"
    _ = source.write_text(data=native_program(app=app), encoding="utf-8")
    _ = subprocess.run(  # noqa: S603
        args=[  # noqa: S607
            "xcrun",
            "clang",
            "-fobjc-arc",
            "-Werror",
            "-framework",
            "Foundation",
            str(object=source),
            "-o",
            str(object=binary),
        ],
        check=True,
        capture_output=True,
        timeout=120,
    )
    _ = subprocess.run(  # noqa: S603
        args=[str(object=binary)], check=True, capture_output=True, timeout=10
    )
    app.cleanup()
