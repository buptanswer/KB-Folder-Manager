from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestCliSmoke(unittest.TestCase):
    def _run_cli(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "kb_folder_manager.py", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def test_help_exit_zero(self) -> None:
        root = Path(__file__).parent.parent
        cp = self._run_cli(["--help"], root)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("KB Folder Manager", cp.stdout)

    def test_validate_compare_blockers_exit_two(self) -> None:
        root = Path(__file__).parent.parent
        with tempfile.TemporaryDirectory(prefix="kbfm_cli_cmp_") as tmp:
            tmp_path = Path(tmp)
            old_dir = tmp_path / "old"
            new_dir = tmp_path / "new"
            log_dir = tmp_path / "logs"
            old_dir.mkdir(parents=True, exist_ok=True)
            new_dir.mkdir(parents=True, exist_ok=True)
            log_dir.mkdir(parents=True, exist_ok=True)

            (old_dir / "a.txt").write_text("old", encoding="utf-8")
            (new_dir / "a.txt").write_text("new", encoding="utf-8")

            cp = self._run_cli(
                [
                    "validate",
                    "--mode",
                    "compare",
                    "--old",
                    str(old_dir),
                    "--new",
                    str(new_dir),
                    "--log-dir",
                    str(log_dir),
                ],
                root,
            )
            self.assertEqual(cp.returncode, 2, cp.stdout + cp.stderr)
            self.assertIn("[FATAL]", cp.stdout)

    def test_index_success_exit_zero(self) -> None:
        root = Path(__file__).parent.parent
        with tempfile.TemporaryDirectory(prefix="kbfm_cli_idx_") as tmp:
            tmp_path = Path(tmp)
            target = tmp_path / "target"
            target.mkdir(parents=True, exist_ok=True)
            (target / "note.md").write_text("hello", encoding="utf-8")
            output = tmp_path / "index.json"
            log_dir = tmp_path / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)

            cp = self._run_cli(
                [
                    "index",
                    "--target",
                    str(target),
                    "--output",
                    str(output),
                    "--log-dir",
                    str(log_dir),
                ],
                root,
            )
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertTrue(output.exists(), "index output file was not created")


if __name__ == "__main__":
    unittest.main()

