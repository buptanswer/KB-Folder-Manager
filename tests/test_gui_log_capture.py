from __future__ import annotations

import sys
import unittest
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb_folder_manager.gui import LogCapture


class _DummyTextWidget:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def after(self, _delay: int, callback):
        callback()

    def insert(self, _where: str, text: str) -> None:
        self.lines.append(text.rstrip('\n'))

    def see(self, _where: str) -> None:
        return

    def update_idletasks(self) -> None:
        return

    def index(self, _expr: str) -> str:
        return f"{len(self.lines) + 1}.0"

    def delete(self, _start: str, _end: str) -> None:
        self.lines.clear()


class TestGuiLogCapture(unittest.TestCase):
    def test_status_callback_print_does_not_recurse(self) -> None:
        widget = _DummyTextWidget()
        status_updates: list[str] = []

        def _status_cb(message: str) -> None:
            status_updates.append(message)
            # Simulate diagnostics callback writing to stdout.
            print(f"[STATUS] {message}")

        capture = LogCapture(widget, progress_callback=None, status_callback=_status_cb)

        old_stdout = sys.stdout
        try:
            sys.stdout = capture
            print("[INFO] building index")
            print("[INFO] indexing progress: files=1/10")
            print("[INFO] indexing progress: files=10/10")
        finally:
            sys.stdout = old_stdout

        capture.flush()
        self.assertGreaterEqual(len(status_updates), 2)
        self.assertTrue(any('building index' in line.lower() for line in widget.lines))


if __name__ == '__main__':
    unittest.main()
