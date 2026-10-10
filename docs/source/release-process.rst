Release Process
===============

Outcomes
~~~~~~~~

* A new ``git`` tag available to install.
* A new package on PyPI.

Perform a Release
~~~~~~~~~~~~~~~~~

On each pull request, CI assembles release notes with a numbered news fragment and runs all lint stages on the resulting tree.
The required CI check also covers the test matrix.
The release workflow uses the same assembly and formatting script before committing, tagging, and publishing.
The GitHub release description uses the same Markdown file as the documentation.

#. `Install GitHub CLI`_.

#. Perform a release:

   .. code-block:: console
      :substitutions:

      $ gh workflow run release.yml --repo "|github-owner|/|github-repository|"

.. _Install GitHub CLI: https://cli.github.com/
