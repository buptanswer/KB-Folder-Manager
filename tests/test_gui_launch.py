"""Quick GUI launch test - opens GUI and auto-closes after 3 seconds."""
from __future__ import annotations

import sys
from pathlib import Path

import ttkbootstrap as ttk

# Add project root to path for direct script execution
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb_folder_manager.gui import KBFolderManagerGUI


def main() -> int:
    print("[TEST] Starting GUI...")
    print("[TEST] GUI will auto-close in 3 seconds...")
    try:
        root = ttk.Window(themename="cosmo")
        KBFolderManagerGUI(root)

        def _close() -> None:
            print("\n[TEST] Auto-closing GUI after 3 seconds...")
            root.destroy()

        root.after(3000, _close)
        root.mainloop()
        print("[TEST] GUI closed successfully!")
        return 0
    except Exception as e:
        print(f"[ERROR] GUI failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
