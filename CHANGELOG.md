# Changelog

## [Unreleased]

- Treat absolute assets beneath an explicitly selected root alias consistently
  with relative assets, including macOS temporary-directory aliases.
- Preserve rejection of linked artifact files inside the project.
- Add scanner and CLI regression coverage for aliased roots.

## [0.1.0] - 2026-10-21

Initial alpha implementation.

- Compare root npm / PEP 621 static versions with an expected release.
- Match exact release headings in Markdown changelogs.
- Check common local Markdown link and image destinations with source locations.
- Inspect project documents and read-only Git status.
- Compute SHA-256 fingerprints for explicitly selected artifacts.
- Export English / Simplified Chinese text, JSON, and portable HTML reports.
- Protect source files and existing outputs; skip network access and project execution.
- Include standard-library tests, a zipapp builder, and a cross-platform CI workflow.
