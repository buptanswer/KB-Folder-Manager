"""
GUI Integration Test with Real Data
====================================

This script creates test data and provides instructions for testing
the GUI with actual file operations.
"""
import tempfile
import shutil
from pathlib import Path

def create_test_data():
    """Create test data structure for GUI testing."""
    test_root = Path(tempfile.gettempdir()) / "KB_GUI_TEST_DATA"
    
    # Clean up if exists
    if test_root.exists():
        shutil.rmtree(test_root)
    
    # Create test structure
    test_kb = test_root / "TestKnowledgeBase"
    test_kb.mkdir(parents=True)
    
    # Create various file types
    (test_kb / "document.pdf").write_text("This is a PDF document", encoding='utf-8')
    (test_kb / "notes.md").write_text("# My Notes\n\nSome important notes here.", encoding='utf-8')
    (test_kb / "readme.txt").write_text("Read me first!", encoding='utf-8')
    (test_kb / "image.jpg").write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 200)
    (test_kb / "data.bin").write_bytes(b'\x00\x01\x02\x03\x04\x05')
    
    # Create nested structure
    nested = test_kb / "Projects"
    nested.mkdir()
    (nested / "report.docx").write_text("Project report content", encoding='utf-8')
    (nested / "presentation.pptx").write_text("Slides content", encoding='utf-8')
    (nested / "video.mp4").write_bytes(b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 100)
    (nested / "code.py").write_text("print('Hello World')", encoding='utf-8')
    
    # Create another nested level
    deep = nested / "Archive"
    deep.mkdir()
    (deep / "old_notes.txt").write_text("Old archived notes", encoding='utf-8')
    (deep / "backup.zip").write_bytes(b'PK\x03\x04' + b'\x00' * 100)
    
    # Empty folder
    (test_kb / "EmptyFolder").mkdir()
    
    # Output directories
    split_output = test_root / "Split_Output"
    merge_output = test_root / "Merge_Output"
    validate_logs = test_root / "Validate_Logs"
    index_output = test_root / "index_output.json"
    
    return {
        'test_root': test_root,
        'test_kb': test_kb,
        'split_output': split_output,
        'merge_output': merge_output,
        'validate_logs': validate_logs,
        'index_output': index_output,
    }

def print_instructions(paths):
    """Print testing instructions."""
    print("\n" + "="*70)
    print("GUI INTEGRATION TEST - Setup Complete")
    print("="*70)
    print("\nTest data created at:")
    print(f"  {paths['test_root']}")
    print("\nNow launch the GUI:")
    print("  python kb_folder_manager_gui.py")
    print("\n" + "="*70)
    print("TEST 1: SPLIT OPERATION")
    print("="*70)
    print("1. Click the 'Split' tab")
    print("2. Source (Complete Folder):")
    print(f"   {paths['test_kb']}")
    print("3. Output Root:")
    print(f"   {paths['split_output']}")
    print("4. Check 'Auto-confirm' (optional)")
    print("5. Click 'Execute Split Operation'")
    print("6. Watch progress bar and log output")
    print("7. Verify success message")
    print("\nExpected Results:")
    print(f"  - Doc folder: {paths['split_output'] / 'doc' / 'TestKnowledgeBase'}")
    print(f"  - Res folder: {paths['split_output'] / 'res' / 'TestKnowledgeBase'}")
    print("  - Index files created")
    print("  - Placeholders created for moved files")
    
    print("\n" + "="*70)
    print("TEST 2: VALIDATE OPERATION")
    print("="*70)
    print("1. Click the 'Validate' tab")
    print("2. Select 'Class1' mode")
    print("3. Target Folder:")
    print(f"   {paths['test_kb']}")
    print("4. Role: complete")
    print("5. Log Directory:")
    print(f"   {paths['validate_logs']}")
    print("6. Click 'Execute Validation'")
    print("7. Check log output for validation results")
    
    print("\n" + "="*70)
    print("TEST 3: INDEX OPERATION")
    print("="*70)
    print("1. Click the 'Index' tab")
    print("2. Target Folder:")
    print(f"   {paths['test_kb']}")
    print("3. Output Index File:")
    print(f"   {paths['index_output']}")
    print("4. Log Directory:")
    print(f"   {paths['validate_logs']}")
    print("5. Click 'Generate Index'")
    print("6. Verify index file is created")
    
    print("\n" + "="*70)
    print("TEST 4: MERGE OPERATION (After Split)")
    print("="*70)
    print("1. First complete TEST 1 (Split)")
    print("2. Click the 'Merge' tab")
    print("3. Doc Folder:")
    print(f"   {paths['split_output'] / 'doc' / 'TestKnowledgeBase'}")
    print("4. Res Folder:")
    print(f"   {paths['split_output'] / 'res' / 'TestKnowledgeBase'}")
    print("5. Output Root:")
    print(f"   {paths['merge_output']}")
    print("6. Check 'Auto-confirm' (optional)")
    print("7. Click 'Execute Merge Operation'")
    print("8. Verify merged folder created")
    
    print("\n" + "="*70)
    print("TEST 5: SETTINGS TAB")
    print("="*70)
    print("1. Click the 'Settings' tab")
    print("2. Verify configuration is displayed")
    print("3. Try 'Reload Configuration' button")
    print("4. Try 'Open Config File' button")
    
    print("\n" + "="*70)
    print("CLEANUP")
    print("="*70)
    print("After testing, you can delete the test data:")
    print(f"  {paths['test_root']}")
    print("\nOr run this script again to reset test data.")
    print("="*70)

def main():
    """Main entry point."""
    print("Creating test data for GUI testing...")
    paths = create_test_data()
    
    file_count = sum(1 for _ in paths['test_kb'].rglob('*') if _.is_file())
    print(f"\n✓ Test data created successfully!")
    print(f"  - {file_count} test files")
    print(f"  - 3 nested directories")
    print(f"  - Multiple file types (.pdf, .md, .txt, .jpg, .bin, .docx, .pptx, .mp4, .py, .zip)")
    
    print_instructions(paths)

if __name__ == '__main__':
    main()
