"""Read-only checks. No project code, build commands, or network calls are run."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import __version__

MAX_TEXT_BYTES = 2 * 1024 * 1024
MAX_FILES = 10_000
EXCLUDED = frozenset({
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules", "vendor",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "dist", "build", "coverage", ".next", ".idea", ".vscode",
})


@dataclass(frozen=True)
class Check:
    rule: str
    status: str
    en: str
    zh: str
    path: str = ""
    line: int | None = None


@dataclass
class Report:
    project: str
    release: str = ""
    checks: list[Check] = field(default_factory=list)
    assets: list[dict] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        return {s: sum(c.status == s for c in self.checks) for s in ("pass", "warn", "fail", "skip")}

    def exit_code(self, strict: bool = False) -> int:
        return int(bool(self.counts["fail"] or (strict and self.counts["warn"])))

    def to_dict(self, strict: bool = False) -> dict:
        return {
            "schema_version": 1, "tool": "release-preflight", "tool_version": __version__,
            "project": self.project, "release": self.release, "strict": strict,
            "exit_code": self.exit_code(strict), "counts": self.counts,
            "checks": [asdict(c) for c in self.checks], "assets": self.assets,
        }


def _linked(path: Path) -> bool:
    info = path.lstat()
    return path.is_symlink() or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _text(root: Path, path: Path) -> str:
    # Reject symlinks/junctions at every component, including links within the root.
    relative = path.relative_to(root)
    current = root
    for component in relative.parts:
        current = current / component
        if _linked(current):
            raise ValueError("symbolic links / reparse points are not read")
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("text must be a regular file")
    with path.open("rb") as stream:
        content = stream.read(MAX_TEXT_BYTES + 1)
    if len(content) > MAX_TEXT_BYTES:
        raise ValueError("text file exceeds the 2 MiB limit")
    return content.decode("utf-8-sig")


def _prose(text: str) -> str:
    """Mask fenced and inline code while preserving source line numbers."""
    lines = []
    fence = ""
    width = 0
    for line in text.splitlines(keepends=True):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence:
            if match and match[1][0] == fence and len(match[1]) >= width and not match[2].strip():
                fence = ""
            lines.append("\n" if line.endswith("\n") else "")
        elif match:
            fence, width = match[1][0], len(match[1])
            lines.append("\n" if line.endswith("\n") else "")
        else:
            lines.append(line)
    value = "".join(lines)
    value = re.sub(r"<!--.*?-->", lambda m: "\n" * m[0].count("\n"), value, flags=re.S)
    return re.sub(r"(`+)(?!`)(.*?)(?<!`)\1(?!`)", lambda m: "\n" * m[0].count("\n"), value, flags=re.S)


def _links(text: str):
    """Yield destinations for common Markdown inline and reference links.

    Anchors, HTML/MDX links, and full CommonMark parsing are outside v0.1 scope.
    Bare destinations support balanced parentheses to one nested level.
    """
    prose = _prose(text)
    destination = r'(?:<([^>\n]+)>|((?:\\.|[^\s()\\]|\((?:\\.|[^()\\])*\))+))'
    inline = re.compile(r'(?<!!)\[[^\]\n]*\]\(\s*' + destination + r'(?:\s+["\'][^\n]*?["\'])?\s*\)|!\[[^\]\n]*\]\(\s*' + destination + r'(?:\s+["\'][^\n]*?["\'])?\s*\)')
    for match in inline.finditer(prose):
        value = next(v for v in match.groups() if v is not None)
        yield re.sub(r"\\([\\()\[\] ])", r"\1", value), prose.count("\n", 0, match.start()) + 1
    # Check declared reference destinations, including shortcut-reference definitions.
    for match in re.finditer(r"^ {0,3}\[[^\]\n]+\]:\s*" + destination, prose, flags=re.M):
        value = match[1] if match[1] is not None else match[2]
        yield re.sub(r"\\([\\()\[\] ])", r"\1", value), prose.count("\n", 0, match.start()) + 1


def _git(root: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    return subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-c", "core.untrackedCache=false",
         "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=15, env=env, check=False,
    )


def scan(root: Path, *, release: str | None = None, skip_git: bool = False,
         assets: tuple[Path, ...] = (), excludes: tuple[str, ...] = ()) -> Report:
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError("project path must be a directory")
    if any(not n or "/" in n or "\\" in n or n in {".", ".."} for n in excludes):
        raise ValueError("--exclude accepts a directory basename, not a path or glob")
    if release is not None and (not release.removeprefix("v").strip() or re.search(r"[\s\x00-\x1f]", release)):
        raise ValueError("release must be a nonempty version without whitespace")
    report = Report(root.name)

    def add(rule, status, en, zh, path="", line=None):
        report.checks.append(Check(rule, status, en, zh, path, line))

    def read(path: Path) -> str | None:
        try:
            return _text(root, path)
        except (OSError, UnicodeError, ValueError) as error:
            # Do not include exception text: OS exceptions may contain absolute/private paths.
            add("readable-text", "fail", f"Cannot read UTF-8 text ({type(error).__name__}); check permissions, size and links.",
                f"无法读取 UTF-8 文本（{type(error).__name__}）；请检查权限、文件大小和符号链接。", path.relative_to(root).as_posix())
            return None

    for label, names, required in (
        ("README", ("README.md", "README.rst", "README.txt", "README"), True),
        ("LICENSE", ("LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"), True),
        ("CONTRIBUTING", ("CONTRIBUTING.md", ".github/CONTRIBUTING.md"), False),
        ("SECURITY", ("SECURITY.md", ".github/SECURITY.md"), False),
    ):
        path = next((root / n for n in names if (root / n).exists() or (root / n).is_symlink()), None)
        if path is None:
            add("document-" + label.lower(), "fail" if required else "warn", f"Add a {label} document.", f"请添加 {label} 文档。")
        else:
            content = read(path)
            if content is not None:
                add("document-" + label.lower(), "pass" if content.strip() else "fail",
                    f"{label} is present and nonempty." if content.strip() else f"{label} is empty.",
                    f"{label} 已提供且非空。" if content.strip() else f"{label} 内容为空。", path.relative_to(root).as_posix())

    versions = []
    found_manifest = False
    for name in ("package.json", "pyproject.toml"):
        path = root / name
        if not path.exists() and not path.is_symlink():
            continue
        found_manifest = True
        content = read(path)
        if content is None:
            continue
        try:
            data = json.loads(content) if name.endswith("json") else tomllib.loads(content)
            if not isinstance(data, dict):
                raise ValueError("manifest must be an object")
            metadata = data if name.endswith("json") else data.get("project", {})
            if not isinstance(metadata, dict):
                raise ValueError("project must be an object")
            version = metadata.get("version")
            if version is None:
                add("manifest-version", "warn", "Static version unavailable; dynamic/legacy versions are not executed.",
                    "未找到静态版本；不会执行动态版本或旧式构建配置。", name)
            elif not isinstance(version, str) or not version.removeprefix("v") or re.search(r"[\s\x00-\x1f]", version):
                raise ValueError("invalid version value")
            else:
                versions.append((name, version.removeprefix("v")))
        except (ValueError, TypeError):
            add("manifest-format", "fail", "Malformed manifest or version field.", "清单格式或版本字段无效。", name)
    if not found_manifest:
        add("manifest-version", "warn", "No root package.json or PEP 621 pyproject.toml found; use --release for another ecosystem.",
            "未找到根目录 package.json 或 PEP 621 pyproject.toml；其他生态可用 --release 指定版本。")
    report.release = release.removeprefix("v") if release else (versions[0][1] if versions else "")
    for name, version in versions:
        match = version == report.release
        add("version-match", "pass" if match else "fail", f"Declared {version}; expected {report.release}.",
            f"声明版本 {version}；目标版本 {report.release}。", name)

    changelog = next((root / n for n in ("CHANGELOG.md", "CHANGES.md", "HISTORY.md") if (root / n).exists()), None)
    if changelog is None:
        add("changelog", "fail", "Add CHANGELOG.md with a heading for this release.", "请添加包含本次版本标题的 CHANGELOG.md。")
    elif not report.release:
        add("changelog", "warn", "Release version unknown; supply --release to check the changelog.", "目标版本未知；请用 --release 检查更新日志。", changelog.name)
    else:
        content = read(changelog)
        if content is not None:
            pattern = r"^#{1,6}\s+\[?v?" + re.escape(report.release) + r"\]?(?=\s|$)"
            exists = bool(re.search(pattern, _prose(content), flags=re.M))
            add("changelog", "pass" if exists else "fail",
                f"Release heading {report.release} " + ("found." if exists else "is missing."),
                f"版本 {report.release} 的更新日志标题" + ("已找到。" if exists else "缺失。"), changelog.name)

    excluded = EXCLUDED | set(excludes)
    documents: list[Path] = []
    total = 0
    limited = False

    def walk_error(_error):
        add("scan-access", "fail", "A directory could not be inspected; scan is incomplete.", "部分目录无法读取；扫描不完整。")

    for base, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        kept = []
        for name in sorted(dirs):
            path = Path(base) / name
            if name in excluded or name.endswith(".egg-info"):
                continue
            try:
                if _linked(path):
                    add("linked-directory", "warn", "Linked directory excluded from scan.", "符号链接或联接目录未扫描。", path.relative_to(root).as_posix())
                else:
                    kept.append(name)
            except OSError:
                walk_error(None)
        dirs[:] = kept
        for name in sorted(files):
            total += 1
            if total > MAX_FILES:
                limited = True
                break
            path = Path(base) / name
            if path.suffix.lower() == ".md":
                documents.append(path)
        if limited:
            break
    if limited:
        add("scan-limit", "fail", "10,000 file limit reached; use --exclude to narrow the scan.", "超过 10,000 个文件；请用 --exclude 缩小范围。")

    local_links = 0
    broken = 0
    for document in documents:
        content = read(document)
        if content is None:
            continue
        for destination, line in _links(content):
            try:
                url = urlsplit(destination)
                if url.scheme or url.netloc or not url.path:
                    continue
                decoded = unquote(url.path)
                if "\x00" in decoded or "\\" in decoded:
                    raise ValueError("invalid local link")
                target = (root / decoded.lstrip("/")) if decoded.startswith("/") else document.parent / decoded
                resolved = target.resolve()
                if not resolved.is_relative_to(root):
                    add("local-link", "warn", "Link leaves the project; destination was not inspected.", "链接指向项目外部；未检查目标。", document.relative_to(root).as_posix(), line)
                    continue
                local_links += 1
                # Check lexical components too: do not follow an in-tree junction or symlink.
                lexical = Path(os.path.abspath(target))
                current = root
                for component in lexical.relative_to(root).parts:
                    current = current / component
                    if current.exists() and _linked(current):
                        raise ValueError("linked destination")
                if not resolved.exists():
                    raise FileNotFoundError()
            except (OSError, ValueError):
                broken += 1
                add("local-link", "fail", "Local link is missing, invalid, or linked; inspect the source line.",
                    "本地链接不存在、无效或经过符号链接；请检查对应行。", document.relative_to(root).as_posix(), line)
    if not broken:
        add("local-links", "pass", f"Checked {local_links} local destinations across {len(documents)} Markdown files.",
            f"已检查 {len(documents)} 个 Markdown 文件中的 {local_links} 个本地链接目标。")
    add("link-scope", "skip", "Remote URLs, anchors, undefined references, HTML and MDX are not validated.",
        "未验证远程网址、页内锚点、未定义引用、HTML 和 MDX。")

    if skip_git:
        add("git", "skip", "Git checks disabled by --skip-git.", "已通过 --skip-git 跳过 Git 检查。")
    else:
        try:
            top = _git(root, ["rev-parse", "--show-toplevel"])
            if top.returncode:
                if (root / ".git").exists():
                    add("git", "fail", "Git metadata exists but repository inspection failed.", "发现 Git 元数据，但无法检查仓库。")
                else:
                    add("git", "warn", "No readable Git repository found.", "未找到可读取的 Git 仓库。")
            elif Path(top.stdout.strip()).resolve() != root:
                add("git", "warn", "Selected folder is inside another repository; scan its root for Git checks.", "所选目录位于其他仓库内；请扫描仓库根目录。")
            else:
                status = _git(root, ["status", "--porcelain=v1", "-z", "--untracked-files=normal"])
                if status.returncode:
                    add("git-clean", "fail", "Git status could not be read.", "无法读取 Git 状态。")
                else:
                    dirty = bool(status.stdout)
                    add("git-clean", "fail" if dirty else "pass", "Working tree has uncommitted/untracked changes." if dirty else "Working tree is clean.",
                        "工作区存在未提交或未跟踪的改动。" if dirty else "工作区干净。")
                head = _git(root, ["rev-parse", "--verify", "HEAD"])
                add("git-history", "pass" if head.returncode == 0 else "warn", "At least one commit exists." if head.returncode == 0 else "Repository has no readable commit.",
                    "仓库至少有一条提交。" if head.returncode == 0 else "仓库尚无可读取的提交。")
        except (OSError, subprocess.TimeoutExpired):
            add("git", "warn", "Git unavailable or timed out; working tree was not verified.", "Git 不可用或检查超时；未验证工作区状态。")

    for asset in assets:
        path = asset if asset.is_absolute() else root / asset
        try:
            # Explicit asset paths may be outside the project; never recurse into folders.
            if any(_linked(p) for p in (path, *path.parents)) or not path.is_file():
                raise ValueError("asset must be a regular file without linked ancestors")
            before = path.stat()
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
            after = path.stat()
            if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                raise ValueError("asset changed during hashing")
            report.assets.append({"name": path.name, "bytes": after.st_size, "sha256": digest.hexdigest()})
            add("asset-sha256", "pass", "SHA-256 recorded; this is an integrity fingerprint, not a signature.", "已记录 SHA-256 完整性指纹；它不是数字签名。", path.name)
        except (OSError, ValueError):
            add("asset-sha256", "fail", "Asset missing, linked, unreadable, or changed during hashing.", "发布文件缺失、经过链接、不可读或在计算期间发生变化。", path.name)
    return report
