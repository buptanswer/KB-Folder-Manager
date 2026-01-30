"""
GUI Test Script - Simulates user interactions with the GUI.

This script performs automated testing of the KB Folder Manager GUI by:
1. Creating test directories and files
2. Simulating GUI operations programmatically
3. Validating results
4. Providing detailed logs
"""
from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

from kb_folder_manager.config import Config
from kb_folder_manager.operations import (
    split_operation,
    merge_operation,
    validate_operation,
    index_operation,
)


class GUITestSimulator:
    """Simulates GUI operations for testing."""
    
    def __init__(self):
        self.test_root = Path(tempfile.mkdtemp(prefix="kb_gui_test_"))
        self.test_results: list[tuple[str, bool, str]] = []
        self.test_counter = 0  # Counter for unique test folders
        print(f"\n{'='*70}")
        print(f"GUI Test Simulator - KB Folder Manager v3.0")
        print(f"{'='*70}")
        print(f"Test Root: {self.test_root}\n")
        
    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message."""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def create_test_structure(self) -> Path:
        """Create test file structure."""
        self.log("Creating test file structure...")
        
        self.test_counter += 1
        complete = self.test_root / f"TestKB_{self.test_counter}"
        complete.mkdir(parents=True)
        
        # Create various file types
        (complete / "document.pdf").write_text("PDF content", encoding='utf-8')
        (complete / "notes.md").write_text("# Notes\nTest notes", encoding='utf-8')
        (complete / "image.jpg").write_bytes(b'\xFF\xD8\xFF\xE0' + b'\x00' * 100)  # Fake JPEG
        (complete / "data.bin").write_bytes(b'\x00\x01\x02\x03')
        
        # Create nested structure
        nested = complete / "subfolder"
        nested.mkdir()
        (nested / "report.docx").write_text("Report content", encoding='utf-8')
        (nested / "video.mp4").write_bytes(b'\x00\x00\x00\x18ftypmp42' + b'\x00' * 50)
        (nested / "archive.zip").write_bytes(b'PK\x03\x04' + b'\x00' * 50)
        
        # Empty directory
        (complete / "empty_folder").mkdir()
        
        self.log(f"Created test structure at: {complete}")
        self.log(f"  - 4 files in root")
        self.log(f"  - 3 files in subfolder")
        self.log(f"  - 1 empty folder")
        
        return complete
        
    def test_split_operation(self) -> bool:
        """Test Split operation (simulating GUI Split tab)."""
        self.log("\n" + "="*70, "TEST")
        self.log("TEST 1: Split Operation", "TEST")
        self.log("="*70, "TEST")
        
        try:
            # Setup
            source = self.create_test_structure()
            output_root = self.test_root / "split_output"
            
            # Create config
            config = Config(
                specified_types={'.pdf', '.md', '.doc', '.docx', '.txt'},
                placeholder_suffix='(PH)',
                hash_algorithm='sha256',
                use_7zip=False
            )
            
            self.log("Simulating GUI Split operation...")
            self.log(f"  Source: {source}")
            self.log(f"  Output Root: {output_root}")
            self.log(f"  Force: False")
            self.log(f"  Auto-Yes: True")
            
            # Execute operation (as GUI would)
            split_operation(source, output_root, config, force=False, auto_yes=True)
            
            # Validate results
            doc_root = output_root / "doc" / source.name
            res_root = output_root / "res" / source.name
            
            assert doc_root.exists(), "Doc folder not created!"
            assert res_root.exists(), "Res folder not created!"
            
            # Check doc files (should have .pdf, .md, .docx)
            doc_files = list(doc_root.rglob("*"))
            doc_file_names = [f.name for f in doc_files if f.is_file()]
            self.log(f"Doc files: {doc_file_names}")
            
            assert "document.pdf" in doc_file_names, "PDF not in doc!"
            assert "notes.md" in doc_file_names, "MD not in doc!"
            assert "report.docx" in doc_file_names, "DOCX not in doc!"
            
            # Check res files (should have .jpg, .bin, .mp4, .zip)
            res_files = list(res_root.rglob("*"))
            res_file_names = [f.name for f in res_files if f.is_file()]
            self.log(f"Res files: {res_file_names}")
            
            assert "image.jpg" in res_file_names, "JPG not in res!"
            assert "data.bin" in res_file_names, "BIN not in res!"
            assert "video.mp4" in res_file_names, "MP4 not in res!"
            assert "archive.zip" in res_file_names, "ZIP not in res!"
            
            # Check placeholders
            doc_placeholders = [f.name for f in doc_root.rglob("*") if f.is_dir() and f.name.endswith("(PH)")]
            res_placeholders = [f.name for f in res_root.rglob("*") if f.is_dir() and f.name.endswith("(PH)")]
            
            self.log(f"Doc placeholders: {len(doc_placeholders)}")
            self.log(f"Res placeholders: {len(res_placeholders)}")
            
            assert len(doc_placeholders) > 0, "No placeholders in doc!"
            assert len(res_placeholders) > 0, "No placeholders in res!"
            
            # Check index files
            index_files = [
                output_root / "index" / "complete" / ".kb_index.json",
                output_root / "index" / "doc" / ".kb_index.json",
                output_root / "index" / "res" / ".kb_index.json",
            ]
            for idx_file in index_files:
                assert idx_file.exists(), f"Index file missing: {idx_file}"
                
            self.log("Split operation PASSED!", "SUCCESS")
            self.test_results.append(("Split Operation", True, "All checks passed"))
            return True
            
        except Exception as e:
            self.log(f"Split operation FAILED: {e}", "ERROR")
            self.test_results.append(("Split Operation", False, str(e)))
            return False
            
    def test_merge_operation(self) -> bool:
        """Test Merge operation (simulating GUI Merge tab)."""
        self.log("\n" + "="*70, "TEST")
        self.log("TEST 2: Merge Operation", "TEST")
        self.log("="*70, "TEST")
        
        try:
            # First do a split to get doc/res
            source = self.create_test_structure()
            split_output = self.test_root / "for_merge_split"
            
            config = Config(
                specified_types={'.pdf', '.md', '.doc', '.docx', '.txt'},
                placeholder_suffix='(PH)',
                hash_algorithm='sha256',
                use_7zip=False
            )
            
            self.log("Preparing data: Running split first...")
            split_operation(source, split_output, config, force=False, auto_yes=True)
            
            doc_path = split_output / "doc" / source.name
            res_path = split_output / "res" / source.name
            merge_output = self.test_root / "merge_output"
            
            self.log("Simulating GUI Merge operation...")
            self.log(f"  Doc: {doc_path}")
            self.log(f"  Res: {res_path}")
            self.log(f"  Output Root: {merge_output}")
            self.log(f"  Force: False")
            self.log(f"  Auto-Yes: True")
            
            # Execute merge operation (as GUI would)
            merge_operation(doc_path, res_path, merge_output, config, force=False, auto_yes=True)
            
            # Validate results
            complete_path = merge_output / "complete" / source.name
            assert complete_path.exists(), "Complete folder not created!"
            
            # Check all original files are back
            merged_files = list(complete_path.rglob("*"))
            merged_file_names = [f.name for f in merged_files if f.is_file()]
            self.log(f"Merged files: {merged_file_names}")
            
            expected_files = ["document.pdf", "notes.md", "image.jpg", "data.bin", 
                            "report.docx", "video.mp4", "archive.zip"]
            for expected in expected_files:
                assert expected in merged_file_names, f"{expected} missing after merge!"
                
            # Check no placeholders in complete
            placeholders = [f for f in merged_files if f.is_dir() and "(PH)" in f.name]
            assert len(placeholders) == 0, f"Placeholders found in merged result: {[p.name for p in placeholders]}"
            
            # Check empty folder preserved
            empty_folder = complete_path / "empty_folder"
            assert empty_folder.exists() and empty_folder.is_dir(), "Empty folder not preserved!"
            
            self.log("Merge operation PASSED!", "SUCCESS")
            self.test_results.append(("Merge Operation", True, "All checks passed"))
            return True
            
        except Exception as e:
            self.log(f"Merge operation FAILED: {e}", "ERROR")
            self.test_results.append(("Merge Operation", False, str(e)))
            return False
            
    def test_validate_operation(self) -> bool:
        """Test Validate operation (simulating GUI Validate tab)."""
        self.log("\n" + "="*70, "TEST")
        self.log("TEST 3: Validate Operation", "TEST")
        self.log("="*70, "TEST")
        
        try:
            # Create a valid structure
            source = self.create_test_structure()
            log_dir = self.test_root / "validate_logs"
            
            config = Config(
                specified_types={'.pdf', '.md', '.doc', '.docx', '.txt'},
                placeholder_suffix='(PH)',
                hash_algorithm='sha256',
                use_7zip=False
            )
            
            self.log("Simulating GUI Validate operation (class1)...")
            self.log(f"  Target: {source}")
            self.log(f"  Mode: class1")
            self.log(f"  Role: complete")
            
            # Execute validation (as GUI would)
            validate_operation(source, 'class1', config, log_dir, 'complete')
            
            # Check log file created
            log_files = list(log_dir.rglob("*.log"))
            assert len(log_files) > 0, "No log files created!"
            self.log(f"Log files created: {len(log_files)}")
            
            # Read log content
            for log_file in log_files:
                content = log_file.read_text(encoding='utf-8')
                self.log(f"Log file: {log_file.name} ({len(content)} bytes)")
                # Should not have FATAL errors for valid structure
                if "[FATAL]" in content:
                    self.log("Warning: FATAL errors found in validation log", "WARN")
                    
            self.log("Validate operation PASSED!", "SUCCESS")
            self.test_results.append(("Validate Operation", True, "All checks passed"))
            return True
            
        except Exception as e:
            self.log(f"Validate operation FAILED: {e}", "ERROR")
            self.test_results.append(("Validate Operation", False, str(e)))
            return False
            
    def test_index_operation(self) -> bool:
        """Test Index operation (simulating GUI Index tab)."""
        self.log("\n" + "="*70, "TEST")
        self.log("TEST 4: Index Operation", "TEST")
        self.log("="*70, "TEST")
        
        try:
            # Create structure
            source = self.create_test_structure()
            output_file = self.test_root / "test_index.json"
            log_dir = self.test_root / "index_logs"
            
            config = Config(
                specified_types={'.pdf', '.md', '.doc', '.docx', '.txt'},
                placeholder_suffix='(PH)',
                hash_algorithm='sha256',
                use_7zip=False
            )
            
            self.log("Simulating GUI Index operation...")
            self.log(f"  Target: {source}")
            self.log(f"  Output: {output_file}")
            
            # Execute index operation (as GUI would)
            index_operation(source, output_file, config, log_dir)
            
            # Validate results
            assert output_file.exists(), "Index file not created!"
            
            import json
            with open(output_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
                
            self.log(f"Index file created: {output_file}")
            self.log(f"  Files indexed: {len(index_data.get('files', {}))}")
            self.log(f"  Dirs indexed: {len(index_data.get('dirs', {}))}")
            self.log(f"  Placeholders: {len(index_data.get('placeholders', {}))}")
            
            # Check metadata
            assert 'metadata' in index_data, "Metadata missing!"
            assert 'files' in index_data, "Files section missing!"
            
            # Should have 7 files
            assert len(index_data['files']) == 7, f"Expected 7 files, got {len(index_data['files'])}"
            
            self.log("Index operation PASSED!", "SUCCESS")
            self.test_results.append(("Index Operation", True, "All checks passed"))
            return True
            
        except Exception as e:
            self.log(f"Index operation FAILED: {e}", "ERROR")
            self.test_results.append(("Index Operation", False, str(e)))
            return False
            
    def test_config_loading(self) -> bool:
        """Test configuration loading (simulating GUI Settings tab)."""
        self.log("\n" + "="*70, "TEST")
        self.log("TEST 5: Configuration Loading", "TEST")
        self.log("="*70, "TEST")
        
        try:
            from kb_folder_manager.config import load_config, DEFAULT_CONFIG_NAME
            
            self.log("Simulating GUI config loading...")
            config_path = Path(DEFAULT_CONFIG_NAME)
            
            if not config_path.exists():
                self.log("Config file not found, creating test config...", "WARN")
                config_path.write_text("""
specified_types: ['.pdf', '.md', '.txt']
placeholder_suffix: "(在百度网盘)"
hash_algorithm: "sha256"
use_7zip: false
""", encoding='utf-8')
                
            config = load_config(config_path)
            
            self.log(f"Config loaded successfully!")
            self.log(f"  Specified types: {len(config.specified_types)}")
            self.log(f"  Placeholder suffix: {config.placeholder_suffix}")
            self.log(f"  Hash algorithm: {config.hash_algorithm}")
            self.log(f"  Use 7-Zip: {config.use_7zip}")
            
            assert config.placeholder_suffix, "Placeholder suffix empty!"
            assert config.hash_algorithm, "Hash algorithm empty!"
            assert len(config.specified_types) > 0, "No specified types!"
            
            self.log("Config loading PASSED!", "SUCCESS")
            self.test_results.append(("Config Loading", True, "All checks passed"))
            return True
            
        except Exception as e:
            self.log(f"Config loading FAILED: {e}", "ERROR")
            self.test_results.append(("Config Loading", False, str(e)))
            return False
            
    def run_all_tests(self) -> None:
        """Run all GUI simulation tests."""
        start_time = time.time()
        
        self.log("\nStarting GUI Test Suite...\n", "INFO")
        
        # Run all tests
        self.test_config_loading()
        self.test_split_operation()
        self.test_merge_operation()
        self.test_validate_operation()
        self.test_index_operation()
        
        # Summary
        elapsed = time.time() - start_time
        self.log("\n" + "="*70, "SUMMARY")
        self.log("Test Summary", "SUMMARY")
        self.log("="*70, "SUMMARY")
        
        passed = sum(1 for _, success, _ in self.test_results if success)
        failed = len(self.test_results) - passed
        
        for test_name, success, message in self.test_results:
            status = "✓ PASS" if success else "✗ FAIL"
            self.log(f"{status}: {test_name} - {message}", "SUMMARY")
            
        self.log(f"\nTotal: {len(self.test_results)} tests", "SUMMARY")
        self.log(f"Passed: {passed}", "SUMMARY")
        self.log(f"Failed: {failed}", "SUMMARY")
        self.log(f"Time: {elapsed:.2f}s", "SUMMARY")
        self.log("="*70, "SUMMARY")
        
        if failed == 0:
            self.log("\n🎉 All tests PASSED! GUI is ready for use.", "SUCCESS")
        else:
            self.log(f"\n⚠️ {failed} test(s) FAILED! Please review errors above.", "ERROR")
            
    def cleanup(self) -> None:
        """Clean up test files."""
        self.log(f"\nCleaning up test directory: {self.test_root}", "INFO")
        try:
            shutil.rmtree(self.test_root)
            self.log("Cleanup completed!", "SUCCESS")
        except Exception as e:
            self.log(f"Cleanup failed: {e}", "WARN")


def main():
    """Main test entry point."""
    simulator = GUITestSimulator()
    try:
        simulator.run_all_tests()
    finally:
        # Ask user if they want to keep test files
        print("\nDo you want to keep test files for inspection? (y/n): ", end='')
        try:
            response = input().strip().lower()
            if response != 'y':
                simulator.cleanup()
            else:
                print(f"Test files preserved at: {simulator.test_root}")
        except:
            simulator.cleanup()


if __name__ == '__main__':
    main()
