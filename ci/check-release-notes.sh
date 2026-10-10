#!/usr/bin/env bash
set -euo pipefail

# Rehearse a release without consuming fragments in the original checkout.
repo_root=$(git rev-parse --show-toplevel)
validation_directory=$(mktemp -d)
trap 'rm -rf "$validation_directory"' EXIT
git clone --quiet --no-hardlinks "$repo_root" "$validation_directory/repo"
cd "$validation_directory/repo"

# Cover issue-link formatting even when there are no pending fragments.
printf '\n%s\n' 'Validate JSON and Sphinx configuration boundaries explicitly instead of relying on casts and ignored type errors.' >> newsfragments/491.change.md
git add -- newsfragments/491.change.md
bash ci/assemble-release-notes.sh 9999.01.01

# Include the generated file in the repository's lint checks.
git add -- docs/source/changelog newsfragments
for stage in pre-commit pre-push manual; do
    uv run --group=dev prek run --all-files --hook-stage "$stage"
done
cmp docs/source/changelog/9999.01.01.md release-notes.md
