# Contributing

Thanks for helping small-project maintainers ship reliable releases.

Use Python 3.11+ and run `python -B -m unittest discover -s tests -v` from the
repository root. No test dependencies are required. Git integration tests need
Git. Symlink tests may be skipped on hosts without permission to create links.

For a bug, provide the tool/Python/OS versions, exact command, expected result,
and a small synthetic example. Remove private paths, tokens and unpublished
project content before sharing a report. Do not upload the entire repository
just to demonstrate a broken link.

For a contribution, keep changes focused and add a test for behavior that could
regress. Use bilingual messages for new findings and keep stable JSON rule IDs.
Update the [changelog](CHANGELOG.md) and [rule coverage](docs/rules.md) when scope
changes. Prefer standard-library code and do not execute scanned project code.

The maintainer reviews pull requests before merging. CI success is required for
release candidates. Contributors retain copyright and license contributions
under the project's [MIT license](LICENSE).
