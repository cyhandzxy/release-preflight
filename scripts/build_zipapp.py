"""Build a dependency-free .pyz without copying private or development files."""
import argparse
import shutil
import tempfile
import zipapp
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("output", type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
output = args.output.resolve()
if output.exists():
    parser.error("output already exists")
output.parent.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix="release-preflight-build-") as temp:
    staging = Path(temp)
    shutil.copytree(root / "release_preflight", staging / "release_preflight", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copyfile(root / "LICENSE", staging / "LICENSE")
    zipapp.create_archive(staging, output, main="release_preflight.cli:main", compressed=True)
print(f"Built {output.name}")
