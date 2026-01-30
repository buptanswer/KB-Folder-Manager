# KB Folder Manager - Copilot Instructions

## Project Overview

A Windows/Python tool for managing personal knowledge base folders. Splits Complete directories into Doc (documents) and Res (resources), merges them back, validates structure compliance, and generates hash-based indexes.

**Version 3.0** includes a modern GUI built with ttkbootstrap, making the tool accessible to non-technical users.

**Important**: The project uses relative imports and is not installed as a package. All commands should be run from the project root directory, or PYTHONPATH must be set to include the project root.

## Build, Test, and Lint

### Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- PyYAML (config management)
- ttkbootstrap (modern GUI framework)
- pillow (image support for GUI)

### Run GUI
```bash
# Launch graphical interface (from project root)
python kb_folder_manager_gui.py

# Or via module (requires PYTHONPATH)
export PYTHONPATH=$(pwd)  # Linux/Mac
$env:PYTHONPATH = "$PWD"  # Windows PowerShell
python -m kb_folder_manager.gui
```

### Dependencies
All dependencies are in `requirements.txt`:
- **PyYAML** (>= 6.0): Config file parsing
- **ttkbootstrap** (>= 1.20.0): Modern GUI framework
- **pillow** (>= 10.0.0): Image support for GUI

No additional dependencies like tqdm, pandas, numpy, etc. are used.

### Run Tests
```bash
# Run all tests
python -m pytest tests/

# Run single test file
python -m pytest tests/test_basic.py

# Run specific test
python -m pytest tests/test_basic.py::TestSplitMerge::test_split_merge_roundtrip

# Run GUI tests (simulated interactions)
python tests/test_gui.py
```

### Manual Testing Commands
```bash
# Split operation
python kb_folder_manager.py split --source "D:\Data\MyKB" --output-root "D:\Output\SplitRun"

# Merge operation
python kb_folder_manager.py merge --doc "D:\Output\doc\MyKB" --res "D:\Output\res\MyKB" --output-root "D:\Output\MergeRun"

# Validate
python kb_folder_manager.py validate --mode class1 --target "D:\Data\MyKB" --role complete --log-dir "D:\Output\logs"

# Index generation
python kb_folder_manager.py index --target "D:\Data\MyKB" --output "index.json" --log-dir "D:\Output\logs"
```

## Architecture

### User Interfaces

**GUI (v3.0+)**:
- Entry point: `kb_folder_manager_gui.py` → `kb_folder_manager/gui.py`
- Framework: ttkbootstrap (modern tkinter)
- Design: Multi-tab interface (Split/Merge/Validate/Index/Settings)
- Threading: Operations run in background threads to prevent UI freezing
- Features: Real-time progress bars, scrollable log output, file browsers

**CLI**:
- Entry point: `kb_folder_manager.py` → `kb_folder_manager/cli.py`
- Arguments parsed with argparse
- Direct calls to operations module

Both interfaces are thin wrappers around the same backend operations.

### Core Principles

1. **Complete Directory is Read-Only** - Never modify Complete folders directly; treat as immutable source of truth
2. **Placeholder Mechanism** - Empty folders with `placeholder_suffix` (e.g., `"(在百度网盘)"`) mark where files were moved during split
3. **Closed-Loop Operations** - All operations follow: Pre-check → User Confirmation → Execute → Post-check
4. **Hash Verification** - All file operations tracked with SHA256 hashes in `.kb_index.json` files

### Data Flow

**Split Operation:**
```
Complete/
  ├── file.pdf          →  doc/Complete/file.pdf
  ├── file.bin          →  res/Complete/file.bin
  └── nested/           →  doc/Complete/nested/ (preserved structure)
      ├── doc.txt       →  doc/Complete/nested/doc.txt
      │                     res/Complete/nested/doc.txt(在百度网盘)/ [placeholder]
      └── image.jpg     →  res/Complete/nested/image.jpg
                            doc/Complete/nested/image.jpg(在百度网盘)/ [placeholder]
```

**Merge Operation:**
```
doc/ + res/  →  complete/
- Placeholders are removed
- Files from both sides combined
- Structure integrity validated
```

### Module Responsibilities

- **gui.py** (NEW in v3.0) - Graphical user interface with ttkbootstrap
  - `KBFolderManagerGUI`: Main window class with tab management
  - `OperationThread`: Background thread for non-blocking operations
  - `LogCapture`: Captures operation logs for display in GUI
- **cli.py** - Command-line interface, argument parsing, top-level orchestration
- **operations.py** - Core split/merge/validate/index operations with pre-check → execute → post-check workflow
- **validator.py** - Structure validation (class1/class2/mutual/compare modes)
- **indexer.py** - File tree indexing with hash generation
- **config.py** - YAML config loading and validation
- **utils.py** - File I/O, logging, path handling, hash computation

## Key Conventions

### Configuration (config.yaml)

- **specified_types** - File extensions that go to Doc side; must be lowercase with dot prefix (e.g., `'.pdf'`, `'.md'`)
- **placeholder_suffix** - Reserved marker (default: `"(在百度网盘)"`). FATAL error if real directories end with this suffix
- **hash_algorithm** - Default is `"sha256"`, also supports MD5, SHA1, etc.
- **use_7zip** - Boolean for compression operations

### File Type Classification

Files are classified by **last extension only** using `is_specified_type()`:
```python
# In Doc: .pdf, .doc, .docx, .txt, .md, .xmind, images, videos, audio, code files
# In Res: Everything else (binary resources, unknown formats)
```

### Validation Modes

1. **class1** - Basic environment checks (no UNC paths, no symlinks, no invalid characters, case conflicts)
   - Used for Complete, Doc, and Res folders
   - `allow_placeholders=False` for Complete, `True` for Doc/Res
   
2. **class2** - Type purity checks (only specified types in Doc, non-specified in Res)
   - Only applies to Doc and Res folders
   - Ensures split was done correctly
   
3. **mutual** - Doc/Res consistency (structure mirrors, placeholders complement real files)
   - Validates Doc and Res are perfect complements
   
4. **compare** - Hash/size verification between old and new folders
   - mtime differences are warnings, not errors

### Logger Result Levels

Operations use `Logger` class with three severity levels:
- **fatal** - Operation must abort (e.g., placeholder suffix in Complete folder name)
- **error** - Serious issue but operation may continue (e.g., non-empty placeholder directory)
- **warning** - Informational (e.g., long paths >240 chars, mtime mismatch in compare)

Use `abort_if_blockers(logger, operation_name)` to halt if `logger.result.fatals > 0`

### Path Handling

- **Windows paths only** - Use backslashes, no UNC paths (`\\server\share`)
- **Relative paths in indexes** - All paths in `.kb_index.json` use forward slashes and are relative to index root
- **Normalization** - Use `Path.resolve()` for absolute normalization, but store/compare as relative

### Index Structure

`.kb_index.json` contains:
```json
{
  "files": {
    "path/to/file.txt": {
      "kind": "file",
      "size": 1234,
      "mtime": "2026-01-30T12:00:00",
      "hash": "abc123...",
      "hash_alg": "sha256"
    }
  },
  "dirs": {
    "path/to/dir": {"kind": "dir"}
  },
  "placeholders": {
    "path/to/file.txt(在百度网盘)": {
      "kind": "placeholder_dir",
      "placeholder_for_name": "file.txt",
      "placeholder_suffix": "(在百度网盘)"
    }
  },
  "metadata": {
    "root_path": "D:\\Data\\MyKB",
    "generated_at": "2026-01-30T12:00:00"
  }
}
```

### Common Patterns

**Pre-check validation before operations:**
```python
pre_log = Logger(log_dir / 'Operation_pre_check.log')
try:
    validate_class1(source, config, allow_placeholders=False, logger=pre_log)
    write_summary(pre_log)
    abort_if_blockers(pre_log, 'operation pre-check')
finally:
    pre_log.close()
```

**Iterating directory tree:**
```python
for rel_root, current_norm, dirs, files, placeholder_dirs in iter_walk(root, placeholder_suffix):
    # rel_root: Path relative to root
    # current_norm: Normalized absolute path to current directory
    # dirs, files: Regular entries
    # placeholder_dirs: Directories ending with placeholder_suffix
```

**Placeholder handling:**
```python
# Creating placeholder
placeholder_name = original_name + config.placeholder_suffix
placeholder_path = parent_dir / placeholder_name
ensure_dir(placeholder_path)  # Create empty directory

# Deriving original name from placeholder
original = derive_placeholder_original(placeholder_name, config.placeholder_suffix)
```

## Important Notes

- Always use `--yes` flag for automated testing to skip confirmation prompts
- Use `--force` with caution - allows operations on non-empty output directories
- Log files are timestamped and stored in `logs/<timestamp>/` subdirectories
- Entry point is `kb_folder_manager.py` which imports from `kb_folder_manager/cli.py`
- GUI entry point is `kb_folder_manager_gui.py` which imports from `kb_folder_manager/gui.py`
- Tests use `tempfile.TemporaryDirectory()` for isolation
- GUI operations run in threads - never block the main (UI) thread
- GUI tests are automated via `tests/test_gui.py` and simulate user interactions programmatically

## GUI Development Guidelines

- **Never modify backend operations** - GUI is a wrapper only
- **Use threading for operations** - Keep UI responsive
- **Update progress via callbacks** - Progress bar and status label
- **Display logs in real-time** - ScrolledText widget with auto-scroll
- **Handle errors gracefully** - Catch exceptions and show messagebox
- **Test via simulation** - `tests/test_gui.py` provides automated testing without actual GUI interaction
