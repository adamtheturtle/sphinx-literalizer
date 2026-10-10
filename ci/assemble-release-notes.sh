#!/usr/bin/env bash
set -euo pipefail

release_version=${1:?Provide the release version}
changelog="docs/source/changelog/$release_version.md"

uv run --group=release towncrier build --yes --version "$release_version"
uv run --group=dev snapper --native --max-width 0 --in-place "$changelog"

# Use the same formatted file for documentation and the GitHub release body.
cp "$changelog" release-notes.md
