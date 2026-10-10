Release Process
===============

Outcomes
~~~~~~~~

* A new ``git`` tag available to install.
* A new package on PyPI.

Perform a Release
~~~~~~~~~~~~~~~~~

CI rehearses release preparation with a numbered news fragment, including when no release notes are pending.
The release workflow assembles and formats the release notes, then runs all lint stages and tests before committing, tagging, or publishing.
The GitHub release description uses the same validated Markdown file as the documentation.

#. `Install GitHub CLI`_.

#. Perform a release:

   .. code-block:: console
      :substitutions:

      $ gh workflow run release.yml --repo "|github-owner|/|github-repository|"

.. _Install GitHub CLI: https://cli.github.com/
