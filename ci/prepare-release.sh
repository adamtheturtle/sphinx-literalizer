#!/usr/bin/env bash
set -euo pipefail

release_version=${1:?Provide the release version}
changelog="docs/source/changelog/$release_version.md"

uv run --group=release towncrier build --yes --version "$release_version"
uv run --group=dev snapper --native --max-width 0 --in-place "$changelog"

# Include the new file in --all-files checks before any commit or publication.
git add -- docs/source/changelog newsfragments
for stage in pre-commit pre-push manual; do
    uv run --group=dev prek run --all-files --hook-stage "$stage"
done
uv run --group=dev pytest -s -vvv --cov --cov-config=pyproject.toml .

# Publish exactly the formatted and validated documentation file.
cp "$changelog" release-notes.md
