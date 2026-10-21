"""Generate an honest failing example report from a temporary synthetic project."""
import argparse
import tempfile
from pathlib import Path

from release_preflight.core import scan
from release_preflight.render import html_report

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
if args.output.exists():
    parser.error("choose a new output filename")
with tempfile.TemporaryDirectory(prefix="preflight-demo-") as temporary:
    root = Path(temporary) / "demo-project"
    root.mkdir()
    (root / "README.md").write_text("# Demo project\n\n[Guide](docs/missing.md)\n", encoding="utf-8")
    (root / "LICENSE").write_text("Example fixture license (not a real project).", encoding="utf-8")
    (root / "CONTRIBUTING.md").write_text("# Contributing\nPlease run the tests.", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nversion="0.2.0"\n', encoding="utf-8")
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0\nInitial version.\n", encoding="utf-8")
    result = scan(root, release="0.2.0", skip_git=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(html_report(result, "zh"))
print("Wrote a synthetic demo report with intentional findings.")
