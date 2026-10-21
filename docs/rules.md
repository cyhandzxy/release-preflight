# Rules and limits

## Release metadata

The scanner reads only root `package.json` and the PEP 621 `[project]` table in
root `pyproject.toml`. An explicit `--release` takes precedence; otherwise the
first readable static version is used. All discovered versions are compared
after removing an optional leading `v`. Version syntax and ordering are not
validated as SemVer or PEP 440. Workspaces, lockfiles, Poetry metadata and dynamic
version providers are not resolved. Supply `--release` for other ecosystems.

The first existing `CHANGELOG.md`, `CHANGES.md`, or `HISTORY.md` must contain an
ATX heading for that exact version, e.g. `## [1.2.3] - 2026-10-21`.
Mentioning the number in prose or a code fence does not satisfy the check.
The tool does not assess the completeness or truthfulness of release notes.

## Documentation

README and license documents must exist and contain non-whitespace text. The
scanner does not validate license grants. CONTRIBUTING and SECURITY documents
are recommended. Files must be UTF-8 (a BOM is accepted), regular files, and no
larger than 2 MiB. Linked files and Windows reparse points are not read.

Common Markdown inline links, image links, and reference-link definitions are
checked. Fenced code, inline code and HTML comments are masked. Angle-bracket
destinations, percent-encoded paths and a single level of parentheses in bare
destinations are supported. A path beginning `/` is relative to the project root.
Missing local targets fail; links leaving the root warn and are not followed.

This is a deliberately limited parser, not full CommonMark. Anchor existence,
remote URLs, undefined reference names, nested link labels, deeply nested
parentheses, HTML/MDX links and generated routing rules are not checked. A
`link-scope` row always records this limitation. A link pass is a destination
existence check for supported syntax, not a guarantee that all links work.

## Scan boundaries

The scan stops after 10,000 files and reports failure rather than silently
passing incomplete coverage. Common generated directories such as `.git`,
`node_modules`, `.venv`, `dist`, `build`, cache folders and `*.egg-info` are
excluded. Use repeatable `--exclude DIRECTORY` to exclude further directory
basenames everywhere. Git ignore rules are not otherwise interpreted.

## Git and artifacts

The selected directory must be the exact Git worktree root for Git checks.
Missing Git/repository/history produces a warning. A dirty working tree fails.
Use `--skip-git` only when intentionally checking an archive or file snapshot;
the report records the skip. No commit, tag, push, hook, or fetch is performed.
Git hooks are not needed; fsmonitor is explicitly disabled for inspection.
Remote synchronization, tags, branch policy, shallow-history completeness and
submodule cleanliness guarantees are outside scope.

`--asset FILE` reads a regular file in chunks and records SHA-256 and byte size.
Relative paths are resolved from the project root. Explicit absolute files
outside the project are allowed. Size/mtime/inode changes detected during the
read cause failure. Signatures and trusted prior hashes are not verified.

## Reports

JSON schema version 1 includes stable rule IDs, bilingual messages, status,
relative source location, artifact fingerprints, summary and effective exit
code. HTML is self-contained, escapes project text and has no external assets.
Reports are exclusively created outside the source root; existing files are
never overwritten. Text output suppresses ASCII terminal-control characters.
Reading a file can update its filesystem access timestamp; the tool does not
promise an unchanged access-time record.
