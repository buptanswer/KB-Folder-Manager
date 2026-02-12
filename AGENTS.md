# Repository Guidelines

## Project Structure & Module Organization
- `kb_folder_manager/` contains core logic:
  - `operations.py` for split/merge/validate/index workflows
  - `cli.py` and `gui.py` for user interfaces
  - `config.py`, `validator.py`, `indexer.py`, and `utils.py` for support layers
- Root entry points: `kb_folder_manager.py` (CLI) and `kb_folder_manager_gui.py` (GUI).
- `tests/` includes unit tests plus GUI validation scripts.
- `docs/` contains user/developer guides and release notes.
- `config.yaml` stores runtime settings (file types, placeholder suffix, hash algorithm).

## Build, Test, and Development Commands
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python kb_folder_manager.py --help
python kb_folder_manager_gui.py
python -m unittest discover tests
python tests\test_gui.py
python tests\test_gui_launch.py
```
- Use the first three commands to prepare a local dev environment.
- Use CLI/GUI commands to verify entry points quickly.
- Run `unittest` for automated regression checks; run GUI scripts for interaction/startup sanity.

## Coding Style & Naming Conventions
- Target Python 3.10+ and follow PEP 8 with 4-space indentation.
- Keep line length near 88 characters.
- Naming: `PascalCase` for classes, `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants.
- Keep interface files thin; place business rules in `kb_folder_manager/operations.py` and related modules.
- Add type hints and concise docstrings for public functions when practical.

## Testing Guidelines
- Primary test framework is `unittest` (`tests/test_basic.py`).
- Name test files `test_*.py` and test methods `test_*`.
- Prefer `tempfile`-based test data and avoid machine-specific absolute paths.
- For GUI changes, run both simulation (`tests/test_gui.py`) and launch smoke test (`tests/test_gui_launch.py`).

## Commit & Pull Request Guidelines
- Current history mixes styles (`feat: ...`, `Add ...`, `Delete ...`). Prefer consistent `type: summary` messages (`feat`, `fix`, `docs`, `test`, `refactor`).
- Keep commits focused on one change area.
- PRs should include purpose, key implementation notes, test commands/results, linked issues, and GUI screenshots when UI behavior changes.

## Configuration & Safety Tips
- Treat `placeholder_suffix` in `config.yaml` as a reserved marker.
- Test split/merge workflows on copied data before running against critical knowledge-base folders.
