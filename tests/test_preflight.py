import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from release_preflight.cli import main
from release_preflight.core import Check, Report, scan
from release_preflight.render import html_report, text_report


class FixtureCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="preflight-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "project"
        self.root.mkdir()
        for name, content in {
            "README.md": "# Example\n\n[Guide](docs/guide.md)\n",
            "LICENSE": "Example license text for a test fixture.",
            "CONTRIBUTING.md": "# Contributing\nRun the tests.",
            "SECURITY.md": "# Security\nUse private reports.",
            "CHANGELOG.md": "# Changes\n\n## [1.2.3] - 2026-10-21\nFirst release.\n",
            "pyproject.toml": '[project]\nname = "example"\nversion = "1.2.3"\n',
            "docs/guide.md": "# Guide\n\n[Home](../README.md)\n",
        }.items():
            self.write(name, content)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_scan(self, **kwargs):
        kwargs.setdefault("skip_git", True)
        return scan(self.root, **kwargs)

    def has(self, report, rule, status):
        return any(c.rule == rule and c.status == status for c in report.checks)


class ProjectCase(FixtureCase):
    def test_healthy_project(self):
        result = self.run_scan()
        self.assertEqual(result.exit_code(strict=True), 0)
        self.assertEqual(result.release, "1.2.3")

    def test_missing_license_fails(self):
        (self.root / "LICENSE").unlink()
        self.assertTrue(self.has(self.run_scan(), "document-license", "fail"))

    def test_empty_readme_fails(self):
        self.write("README.md", " \n")
        self.assertTrue(self.has(self.run_scan(), "document-readme", "fail"))

    def test_warnings_change_strict_exit(self):
        (self.root / "CONTRIBUTING.md").unlink()
        result = self.run_scan()
        self.assertEqual(result.exit_code(), 0)
        self.assertEqual(result.exit_code(strict=True), 1)

    def test_node_and_python_version_conflict(self):
        self.write("package.json", '{"version":"2.0.0"}')
        self.assertTrue(self.has(self.run_scan(), "version-match", "fail"))

    def test_explicit_version_and_v_prefix(self):
        self.assertEqual(self.run_scan(release="v1.2.3").exit_code(), 0)
        self.assertTrue(self.has(self.run_scan(release="1.2.4"), "version-match", "fail"))

    def test_malformed_and_non_object_manifests_fail(self):
        for text in ("{bad", "[]", '{"version": 23}'):
            with self.subTest(text=text):
                self.write("package.json", text)
                self.assertTrue(self.has(self.run_scan(), "manifest-format", "fail"))

    def test_dynamic_version_is_not_executed(self):
        self.write("pyproject.toml", '[project]\nname="example"\ndynamic=["version"]\n')
        self.assertTrue(self.has(self.run_scan(release="1.2.3"), "manifest-version", "warn"))

    def test_changelog_requires_exact_heading(self):
        for text in ("Mention 1.2.3 here", "## 1.2.30", "```md\n## 1.2.3\n```", "## [1.2.3]suffix"):
            with self.subTest(text=text):
                self.write("CHANGELOG.md", text)
                self.assertTrue(self.has(self.run_scan(), "changelog", "fail"))

    def test_prerelease_changelog(self):
        self.write("pyproject.toml", '[project]\nversion="1.2.3-rc.1+build.4"\n')
        self.write("CHANGELOG.md", "## [1.2.3-rc.1+build.4] - 2026-10-21\nNotes")
        self.assertEqual(self.run_scan().exit_code(), 0)

    def test_broken_link_line_number(self):
        self.write("README.md", "# Title\n\n[Broken](missing.md)\n")
        broken = [c for c in self.run_scan().checks if c.rule == "local-link"]
        self.assertEqual(len(broken), 1)
        self.assertEqual((broken[0].path, broken[0].line, broken[0].status), ("README.md", 3, "fail"))

    def test_code_and_comments_are_ignored(self):
        self.write("README.md", '# Title\n```md\n[Missing](missing.md)\n```\n`[Missing](missing.md)`\n<!-- [Missing](missing.md) -->\n')
        self.assertEqual(self.run_scan().exit_code(), 0)

    def test_encoded_unicode_root_links_and_parentheses(self):
        self.write("docs/使用 指南 (v1).md", "# Guide")
        self.write("README.md", '[Guide](docs/%E4%BD%BF%E7%94%A8%20%E6%8C%87%E5%8D%97%20(v1).md)\n[License](/LICENSE)\n[Title](<docs/使用 指南 (v1).md> "Guide")\n')
        self.assertEqual(self.run_scan().exit_code(), 0)

    def test_image_and_reference_links(self):
        self.write("README.md", "![Image](missing.png)\n[Guide][guide]\n\n[guide]: absent.md\n")
        self.assertEqual(sum(c.rule == "local-link" and c.status == "fail" for c in self.run_scan().checks), 2)

    def test_remote_and_anchor_links_are_not_requested(self):
        self.write("README.md", "[URL](https://invalid.example/nowhere)\n[Anchor](#missing)\n[Email](mailto:test@example.invalid)\n")
        with patch("socket.socket", side_effect=AssertionError("network attempted")):
            self.assertEqual(self.run_scan().exit_code(), 0)

    def test_outside_link_is_warning_without_read(self):
        outside = self.base / "private.md"
        outside.write_text("private", encoding="utf-8")
        self.write("README.md", "[Outside](../private.md)")
        self.assertTrue(self.has(self.run_scan(), "local-link", "warn"))

    def test_generated_and_custom_directories_are_excluded(self):
        self.write("node_modules/pkg/README.md", "[Bad](missing.md)")
        self.write("custom/README.md", "[Bad](missing.md)")
        self.assertEqual(self.run_scan(excludes=("custom",)).exit_code(), 0)
        self.assertEqual(self.run_scan().exit_code(), 1)

    def test_invalid_exclude_is_rejected(self):
        with self.assertRaises(ValueError):
            self.run_scan(excludes=("../outside",))

    def test_invalid_encoding_and_oversized_text_fail(self):
        (self.root / "README.md").write_bytes(b"\xff\xfe\x00")
        self.assertTrue(self.has(self.run_scan(), "readable-text", "fail"))
        self.write("README.md", "A" * (2 * 1024 * 1024 + 1))
        self.assertTrue(self.has(self.run_scan(), "readable-text", "fail"))

    def test_file_limit_cannot_silently_pass(self):
        with patch("release_preflight.core.MAX_FILES", 2):
            self.assertTrue(self.has(self.run_scan(), "scan-limit", "fail"))

    def test_linked_markdown_not_read(self):
        target = self.base / "private.md"
        target.write_text("private", encoding="utf-8")
        link = self.root / "secret.md"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable on this host")
        self.assertTrue(self.has(self.run_scan(), "readable-text", "fail"))

    def test_sha256_matches_published_test_vector(self):
        asset = self.write("artifact.bin", "abc")
        result = self.run_scan(assets=(asset,))
        self.assertEqual(result.assets[0]["sha256"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
        self.assertEqual(result.assets[0]["bytes"], 3)
        self.assertEqual(result.assets[0]["name"], "artifact.bin")

    def test_missing_asset_fails(self):
        self.assertTrue(self.has(self.run_scan(assets=(Path("absent.zip"),)), "asset-sha256", "fail"))

    def project_alias(self):
        alias = self.base / "project-alias"
        try:
            alias.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("directory symlink creation unavailable on this host")
        return alias

    def test_absolute_asset_under_selected_root_alias(self):
        self.write("artifact.bin", "abc")
        alias = self.project_alias()
        result = scan(alias, skip_git=True, assets=(alias / "artifact.bin",))
        self.assertTrue(self.has(result, "asset-sha256", "pass"))
        self.assertEqual(result.assets[0]["sha256"], "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_cli_absolute_asset_under_selected_root_alias(self):
        self.write("artifact.bin", "abc")
        alias = self.project_alias()
        output = self.base / "alias-report.json"
        code = main([str(alias), "--skip-git", "--asset", str(alias / "artifact.bin"),
                     "--format", "json", "--output", str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(output.read_text(encoding="utf-8"))["assets"]), 1)

    def test_symlink_asset_inside_project_is_still_rejected(self):
        target = self.write("artifact.bin", "abc")
        link = self.root / "linked-artifact.bin"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation unavailable on this host")
        result = self.run_scan(assets=(link,))
        self.assertTrue(self.has(result, "asset-sha256", "fail"))
        self.assertEqual(result.assets, [])

    def test_scan_does_not_change_source_bytes(self):
        def snapshot():
            return {p.relative_to(self.root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob("*") if p.is_file()}
        before = snapshot()
        self.run_scan(assets=(Path("LICENSE"),))
        self.assertEqual(before, snapshot())

    def test_json_cli_and_exit_code(self):
        output = self.base / "report.json"
        code = main([str(self.root), "--skip-git", "--format", "json", "--output", str(output)])
        self.assertEqual(code, 0)
        data = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(data["schema_version"], 1)
        self.assertNotIn(str(self.root), output.read_text(encoding="utf-8"))
        self.assertEqual(data["exit_code"], 0)

    def test_cli_never_overwrites_existing_file(self):
        output = self.base / "important.txt"
        output.write_text("KEEP", encoding="utf-8")
        with contextlib.redirect_stderr(io.StringIO()):
            code = main([str(self.root), "--output", str(output)])
        self.assertEqual(code, 2)
        self.assertEqual(output.read_text(encoding="utf-8"), "KEEP")

    def test_cli_refuses_output_inside_source(self):
        with contextlib.redirect_stderr(io.StringIO()):
            code = main([str(self.root), "--output", str(self.root / "report.html")])
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "report.html").exists())

    def test_cli_invalid_path_has_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([str(self.base / "absent")]), 2)

    def test_html_escapes_repository_content(self):
        report = Report('<script>alert("x")</script>')
        report.checks.append(Check("test", "fail", '<img src=x onerror=alert(1)>', '<img src=x onerror=alert(1)>'))
        html = html_report(report, "zh")
        self.assertNotIn('<img src=x', html)
        self.assertNotIn('<script>alert', html)
        self.assertIn('&lt;img', html)
        self.assertIn('default-src', html)

    def test_text_strips_terminal_controls(self):
        report = Report("project\x1b[31m")
        self.assertNotIn("\x1b", text_report(report))


@unittest.skipUnless(shutil.which("git"), "Git not installed")
class GitCase(FixtureCase):
    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True, text=True)

    def init_repo(self):
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Test fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("add", ".")
        self.git("commit", "-m", "Fixture")

    def test_real_git_clean_then_modified(self):
        self.init_repo()
        self.assertTrue(self.has(self.run_scan(skip_git=False), "git-clean", "pass"))
        self.write("new-file.txt", "untracked")
        self.assertTrue(self.has(self.run_scan(skip_git=False), "git-clean", "fail"))

    def test_empty_repo_warns_for_missing_history(self):
        self.git("init", "-b", "main")
        self.assertTrue(self.has(self.run_scan(skip_git=False), "git-history", "warn"))

    def test_parent_repo_is_not_mistaken_for_project_repo(self):
        self.init_repo()
        result = scan(self.root / "docs")
        self.assertTrue(self.has(result, "git", "warn"))

    def test_git_environment_cannot_redirect_scan(self):
        self.init_repo()
        with patch.dict(os.environ, {"GIT_DIR": str(self.base / "wrong")}):
            self.assertTrue(self.has(self.run_scan(skip_git=False), "git-clean", "pass"))


if __name__ == "__main__":
    unittest.main()
