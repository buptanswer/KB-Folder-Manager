"""
Quick GUI launch test - Opens GUI and closes after 3 seconds.
This tests that the GUI can actually start without errors.
"""
import sys
import time
import threading

def auto_close_gui():
    """Close GUI after 3 seconds."""
    time.sleep(3)
    print("\n[TEST] Auto-closing GUI after 3 seconds...")
    sys.exit(0)

if __name__ == '__main__':
    print("[TEST] Starting GUI...")
    print("[TEST] GUI will auto-close in 3 seconds...")
    
    # Start auto-close thread
    closer = threading.Thread(target=auto_close_gui, daemon=True)
    closer.start()
    
    # Launch GUI
    from kb_folder_manager.gui import launch_gui
    try:
        launch_gui()
        print("[TEST] GUI closed successfully!")
    except Exception as e:
        print(f"[ERROR] GUI failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
