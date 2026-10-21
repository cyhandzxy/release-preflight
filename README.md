# Release Preflight

**Catch release housekeeping mistakes before they reach your users.**

[简体中文](README.zh-CN.md) · [Rules and limits](docs/rules.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

Release Preflight is a small, offline CLI for open-source maintainers. It checks
declared versions, release notes, local documentation links, project documents,
Git cleanliness, and explicit release artifact hashes. It produces terminal,
JSON, and self-contained HTML reports in English or Chinese.

**Status: v0.1.0 alpha.** This is a new project; broader adoption and long-term
maintenance have not yet been established. It has no runtime dependencies and
does not require an AI account, API key, or network access.

## Quick start

Requires Python 3.11 or newer. From a downloaded source checkout:

```sh
python -B -m release_preflight . --release 0.1.0 --lang zh
python -B -m release_preflight /path/to/project --format html --output ../report.html
```

On Windows, replace `/path/to/project` with a quoted path such as `"D:\My Project"`.
The first command scans this project. Git warnings are expected in an extracted
source ZIP; use `--skip-git` when you intentionally want to skip Git checks.

Reports must be written **outside the scanned project** to a **new filename**.
The tool never overwrites an existing output file. HTML files are portable and
have status filters; open them manually in a browser. The tool does not launch one.

### Portable single file

Build a Python zip application using only the standard library:

```sh
python scripts/build_zipapp.py ../release-preflight.pyz
python -B ../release-preflight.pyz /path/to/project --lang zh
```

The `.pyz` still requires Python 3.11+. It is not a native executable.

### Optional local installation

```sh
python -m pip install .
release-preflight /path/to/project --strict
```

Installation may download the build backend. Scanning itself stays offline.
This name has not been published to PyPI; install from source rather than a
similarly named registry package.

## What it checks

| Check | What a failure or warning means |
| --- | --- |
| Version consistency | Root `package.json` / PEP 621 `pyproject.toml` disagree with the expected release |
| Changelog | `CHANGELOG.md`, `CHANGES.md`, or `HISTORY.md` has no exact release heading |
| Local Markdown links | A supported local file/image destination is absent or unsafe to inspect |
| Project documents | README or license is missing/empty; contribution/security documents are recommended |
| Git status | Working tree has uncommitted/untracked changes, or cannot be checked |
| Artifact SHA-256 | An explicitly supplied file cannot be read consistently |

Version strings are compared literally after removing an optional `v` prefix.
Dynamic build metadata is never executed. The license check detects presence,
not legal validity. Hashes are fingerprints, not signatures. See the
[documented coverage and exclusions](docs/rules.md).

## Examples

```sh
# JSON suitable for CI; warnings become a nonzero exit in strict mode
python -B -m release_preflight . --release 0.1.0 --strict --format json

# Report with release artifact hashes (relative asset paths use the project root)
python -B -m release_preflight . --asset dist/tool.zip --format html --output ../release.html

# Large repositories: omit a directory basename everywhere it occurs
python -B -m release_preflight . --exclude generated --exclude snapshots
```

Exit codes: `0` selected checks passed; `1` failed checks (or warnings with
`--strict`); `2` invalid input/output or invocation error; `130` interrupted.
Skipped checks are visible in every report and never count as verified.

## Development and CI

```sh
python -B -m unittest discover -s tests -v
python -B -m release_preflight . --release 0.1.0 --skip-git --strict
```

The included GitHub Actions workflow tests Python 3.11 and 3.14 on Windows,
Linux, and macOS once the repository is published. A workflow file is not
evidence that those hosted jobs have run. No tokens or secrets are needed.

## Why this exists

Small projects often release without a dedicated release engineer. A stale
version, missing release note, or broken relative documentation link can turn
a small update into avoidable support work. Release Preflight groups these
checks into one report without running the project's build scripts or uploading
its contents. Bilingual reports help maintainers and collaborators discuss the
same findings.

Maintained by **cyhandzxy**. The intended repository is
[cyhandzxy/release-preflight](https://github.com/cyhandzxy/release-preflight).
See the [roadmap](docs/roadmap.md) and [MIT license](LICENSE).
