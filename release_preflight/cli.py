from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import scan
from .render import html_report, text_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline, read-only release checks for open-source maintainers.")
    parser.add_argument("path", nargs="?", default=".", type=Path, help="project directory (default: current directory)")
    parser.add_argument("--release", help="expected release version, e.g. 1.2.3 or v1.2.3")
    parser.add_argument("--format", choices=("text", "json", "html"), default="text")
    parser.add_argument("--lang", choices=("en", "zh"), default="en", help="text/HTML language; JSON always includes both")
    parser.add_argument("--output", type=Path, help="new report file OUTSIDE the project; existing files are never overwritten")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    parser.add_argument("--skip-git", action="store_true", help="explicitly skip Git checks (e.g. a source archive)")
    parser.add_argument("--exclude", action="append", default=[], metavar="DIRECTORY", help="skip a directory basename everywhere (repeatable)")
    parser.add_argument("--asset", action="append", type=Path, default=[], metavar="FILE", help="hash an explicit release asset; relative paths are relative to project")
    parser.add_argument("--version", action="version", version=f"release-preflight {__version__}")
    args = parser.parse_args(argv)
    try:
        root = args.path.resolve(strict=True)
        if args.output:
            output = args.output.resolve()
            if output.is_relative_to(root):
                raise ValueError("--output must be outside the scanned project to preserve read-only scanning")
            if output.exists() or args.output.is_symlink():
                raise ValueError("output already exists; choose a new filename")
            if not output.parent.is_dir():
                raise ValueError("output parent directory does not exist")
        report = scan(root, release=args.release, skip_git=args.skip_git,
                      assets=tuple(args.asset), excludes=tuple(args.exclude))
        if args.format == "json":
            content = json.dumps(report.to_dict(args.strict), ensure_ascii=False, indent=2) + "\n"
        elif args.format == "html":
            content = html_report(report, args.lang, args.strict)
        else:
            content = text_report(report, args.lang, args.strict)
        if args.output:
            # Exclusive creation protects existing content even if it appeared during scanning.
            with output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        else:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stdout.write(content)
        return report.exit_code(args.strict)
    except (OSError, ValueError) as error:
        print(f"release-preflight: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
