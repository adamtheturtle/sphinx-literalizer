"""Compile and run the exact rendered block in the macOS CI job.

This external compiler witness runs separately from the cross-platform
Python coverage suite, which exercises the shared document builder.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
from sphinx.testing.util import SphinxTestApp

from tests.native_invocation_support import (
    NATIVE_RECIPE,
    build_native_app,
    native_program,
)
from tests.objective_c_options_support import (
    make_options_app,
    options_programs,
)


@pytest.mark.parametrize(argnames="precise_options", argvalues=[False, True])
def test_native_rendered_program_runs(
    *,
    make_app: Callable[..., SphinxTestApp],
    tmp_path: Path,
    precise_options: bool,
) -> None:
    """The exact rendered program calls real methods with real scalars."""
    if precise_options:
        app = make_options_app(make_app=make_app, tmp_path=tmp_path)
        app.build()
        programs = options_programs(app=app)
    else:
        app = build_native_app(
            make_app=make_app, tmp_path=tmp_path, recipe=NATIVE_RECIPE
        )
        programs = [native_program(app=app)]
    assert app.warning.getvalue() == ""  # noqa: S101
    source = tmp_path / "native.m"
    binary = tmp_path / "native"
    for program in programs:
        if precise_options:
            formatted = subprocess.run(
                args=[  # noqa: S607
                    "clang-format",
                    "--assume-filename=guide.m",
                    (
                        "--style={BasedOnStyle: LLVM, IndentWidth: 2, "
                        "ColumnLimit: 80, BinPackArguments: false, "
                        "BinPackLongBracedList: false, "
                        "AlignTrailingComments: Never, ReflowComments: false}"
                    ),
                ],
                input=program,
                text=True,
                capture_output=True,
                check=True,
                timeout=10,
            )
            assert formatted.stdout.rstrip() == program.rstrip()  # noqa: S101
        _ = source.write_text(data=program, encoding="utf-8")
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
            args=[str(object=binary)],
            check=True,
            capture_output=True,
            timeout=10,
        )
    app.cleanup()
