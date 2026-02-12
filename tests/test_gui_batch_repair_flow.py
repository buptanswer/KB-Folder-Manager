"""GUI batch-repair flow simulation test.

This script simulates user actions in GUI:
1. Run Validate->Compare
2. Auto-jump to Repair
3. Apply partial and full batch repairs by issue type
4. Re-run compare to verify issues are eliminated
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

import ttkbootstrap as ttk
from tkinter import messagebox

# Add project root to path for direct script execution
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from kb_folder_manager.gui import KBFolderManagerGUI
from kb_folder_manager import gui as gui_module
from kb_folder_manager.operations import (
    COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
    DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
    DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
    DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
    DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
)
from kb_folder_manager.validator import (
    COMPARE_ISSUE_CONTENT_MISMATCH,
    COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW,
    COMPARE_ISSUE_EXTRA_IN_NEW,
    COMPARE_ISSUE_MISSING_IN_NEW,
    COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW,
    COMPARE_ISSUE_MTIME_DIFF_HASH_SAME,
)


def _pump_until_idle(app: KBFolderManagerGUI, root: ttk.Window, timeout_sec: float = 20.0) -> None:
    start = time.time()
    while time.time() - start < timeout_sec:
        root.update()
        if not app.operation_running and app.result_queue.empty():
            return
        time.sleep(0.03)
    raise TimeoutError("GUI operation timeout")


def _select_issue_type(app: KBFolderManagerGUI, issue_type: str) -> None:
    for display, internal in app.repair_display_map.items():
        if internal == issue_type:
            app.repair_issue_type_var.set(display)
            app._on_repair_issue_type_changed()
            return
    raise AssertionError(f"Issue type not available in repair tab: {issue_type}")


def _select_strategy(app: KBFolderManagerGUI, strategy: str) -> None:
    for display, internal in app.repair_strategy_display_map.items():
        if internal == strategy:
            app.repair_strategy_var.set(display)
            return
    raise AssertionError(f"Strategy not available: {strategy}")


def _run_compare(app: KBFolderManagerGUI, root: ttk.Window, old_root: Path, new_root: Path, log_root: Path) -> dict[str, int]:
    app.validate_mode_var.set('compare')
    app.update_validate_inputs()
    app.validate_widgets['old'].set(str(old_root))
    app.validate_widgets['new'].set(str(new_root))
    app.validate_log_dir_var.set(str(log_root))
    app.execute_validate()
    _pump_until_idle(app, root)
    assert app.last_compare_result is not None
    return app.last_compare_result.issue_counts()


def _run_validate_mutual(app: KBFolderManagerGUI, root: ttk.Window, doc_root: Path, res_root: Path, log_root: Path) -> None:
    app.validate_mode_var.set('mutual')
    app.update_validate_inputs()
    app.validate_widgets['doc'].set(str(doc_root))
    app.validate_widgets['res'].set(str(res_root))
    app.validate_log_dir_var.set(str(log_root))
    app.execute_validate()
    _pump_until_idle(app, root)


def _run_split(app: KBFolderManagerGUI, root: ttk.Window, source: Path, output_root: Path) -> None:
    app.split_source_var.set(str(source))
    app.split_output_var.set(str(output_root))
    app.split_auto_yes_var.set(True)
    app.execute_split()
    _pump_until_idle(app, root)


def _run_repair(
    app: KBFolderManagerGUI,
    root: ttk.Window,
    issue_type: str,
    strategy: str,
    select_all: bool,
    select_count: int = 0,
) -> None:
    _select_issue_type(app, issue_type)
    _select_strategy(app, strategy)

    items = app.repair_tree.get_children()
    assert items, f"No items to repair for issue_type={issue_type}"

    if select_all:
        app.repair_select_all()
    else:
        chosen = items[:select_count]
        app.repair_tree.selection_set(chosen)

    app.execute_repair()
    _pump_until_idle(app, root)


def _assert_issue_row_has_metadata(app: KBFolderManagerGUI, issue_type: str) -> None:
    _select_issue_type(app, issue_type)
    items = app.repair_tree.get_children()
    assert items, f"No rows for issue_type={issue_type}"
    first = items[0]
    row = app.repair_tree.item(first, 'values')
    # row: path + side-by-side size/mtime/hash + hint
    assert len(row) == 8, f"Unexpected tree row shape: {row}"
    (
        path,
        folder1_size,
        folder2_size,
        folder1_mtime,
        folder2_mtime,
        folder1_hash,
        folder2_hash,
        hint,
    ) = row
    print(
        f'[ROW][{issue_type}] path={path} '
        f'f1_size={folder1_size} f2_size={folder2_size} '
        f'f1_mtime={folder1_mtime} f2_mtime={folder2_mtime} '
        f'f1_hash={folder1_hash} f2_hash={folder2_hash} hint={hint}'
    )
    assert path, "Path should not be empty"
    assert hint, "Hint should not be empty"
    if issue_type == COMPARE_ISSUE_MTIME_DIFF_HASH_SAME:
        assert folder1_mtime != '-' and folder2_mtime != '-', f"MTime should be visible in row: {row}"
        assert folder1_hash != '-' and folder2_hash != '-', f"Hash should be visible in row: {row}"
    if issue_type == COMPARE_ISSUE_CONTENT_MISMATCH:
        assert folder1_hash != folder2_hash, f"Hash cells should differ for content mismatch row: {row}"


def _prepare_test_data(root: Path, placeholder_suffix: str) -> tuple[Path, Path]:
    old_root = root / 'old'
    new_root = root / 'new'
    old_root.mkdir(parents=True)
    new_root.mkdir(parents=True)

    # mtime_diff_hash_same x2
    for idx in (1, 2):
        rel = Path('docs') / f'mtime_same_{idx}.txt'
        (old_root / rel).parent.mkdir(parents=True, exist_ok=True)
        (new_root / rel).parent.mkdir(parents=True, exist_ok=True)
        (old_root / rel).write_text(f'same-content-{idx}', encoding='utf-8')
        (new_root / rel).write_text(f'same-content-{idx}', encoding='utf-8')
        base_ts = 1700000000.0 + idx * 100
        os.utime(old_root / rel, (base_ts, base_ts))
        os.utime(new_root / rel, (base_ts + 5000.0, base_ts + 5000.0))

    # hash_mismatch x2
    for idx in (1, 2):
        rel = Path('data') / f'mismatch_{idx}.bin'
        (old_root / rel).parent.mkdir(parents=True, exist_ok=True)
        (new_root / rel).parent.mkdir(parents=True, exist_ok=True)
        (old_root / rel).write_bytes((b'old-' + bytes([idx])) * 20)
        (new_root / rel).write_bytes((b'new-' + bytes([idx])) * 5)

    # missing_in_new
    rel_old_only = Path('extra') / 'only_in_old.txt'
    (old_root / rel_old_only).parent.mkdir(parents=True, exist_ok=True)
    (old_root / rel_old_only).write_text('only old', encoding='utf-8')

    # extra_in_new
    rel_new_only = Path('extra') / 'only_in_new.txt'
    (new_root / rel_new_only).parent.mkdir(parents=True, exist_ok=True)
    (new_root / rel_new_only).write_text('only new', encoding='utf-8')

    # missing/extra placeholder in new
    ph_missing = Path('holder') / f'a{placeholder_suffix}'
    ph_extra = Path('holder') / f'b{placeholder_suffix}'
    (old_root / ph_missing).mkdir(parents=True, exist_ok=True)
    (new_root / ph_extra).mkdir(parents=True, exist_ok=True)

    return old_root, new_root


def main() -> int:
    print('=' * 80)
    print('GUI Batch Repair Flow Simulation Test')
    print('=' * 80)

    # Monkeypatch messagebox to avoid blocking dialogs during automated run
    msg_events: list[tuple[str, str, str]] = []
    original_showinfo = messagebox.showinfo
    original_showwarning = messagebox.showwarning
    original_showerror = messagebox.showerror
    original_askyesno = messagebox.askyesno
    original_append_line = gui_module.LogCapture._append_line
    original_handle_progress_callbacks = gui_module.LogCapture._handle_progress_callbacks
    original_update_stage_status = gui_module.LogCapture._update_stage_status

    def _capture(kind: str, title: str, msg: str) -> None:
        msg_events.append((kind, title, msg))
        print(f'[MSG][{kind}] {title}: {msg}')

    messagebox.showinfo = lambda title, msg: (_capture('info', title, str(msg)), True)[1]
    messagebox.showwarning = lambda title, msg: (_capture('warning', title, str(msg)), True)[1]
    messagebox.showerror = lambda title, msg: (_capture('error', title, str(msg)), True)[1]
    messagebox.askyesno = lambda title, msg: (_capture('askyesno', title, str(msg)), True)[1]
    gui_module.LogCapture._append_line = lambda self, line: None
    gui_module.LogCapture._handle_progress_callbacks = lambda self, line, progress: None
    gui_module.LogCapture._update_stage_status = lambda self, lower: None

    try:
        with tempfile.TemporaryDirectory(prefix='kbfm_gui_repair_') as tmp:
            temp_root = Path(tmp)
            log_root = temp_root / 'logs'

            root = ttk.Window(themename='cosmo')
            app = KBFolderManagerGUI(root)
            root.update()
            assert app.config is not None
            old_root, new_root = _prepare_test_data(temp_root, app.config.placeholder_suffix)

            print('\n[STEP 1] Initial compare')
            counts_1 = _run_compare(app, root, old_root, new_root, log_root)
            print(f'Initial issue counts: {counts_1}')

            assert counts_1.get(COMPARE_ISSUE_MTIME_DIFF_HASH_SAME, 0) == 2
            assert counts_1.get(COMPARE_ISSUE_CONTENT_MISMATCH, 0) == 2
            assert counts_1.get(COMPARE_ISSUE_MISSING_IN_NEW, 0) == 1
            assert counts_1.get(COMPARE_ISSUE_EXTRA_IN_NEW, 0) == 1
            assert counts_1.get(COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW, 0) == 1
            assert counts_1.get(COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW, 0) == 1
            _assert_issue_row_has_metadata(app, COMPARE_ISSUE_MTIME_DIFF_HASH_SAME)
            _assert_issue_row_has_metadata(app, COMPARE_ISSUE_CONTENT_MISMATCH)
            _select_issue_type(app, COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW)
            assert app.repair_strategy_combo['values'], 'Strategy list should not be empty for missing_placeholder_in_new'

            print('\n[STEP 2] Partial repair for mtime_diff_hash_same (select 1 of 2)')
            _run_repair(
                app,
                root,
                issue_type=COMPARE_ISSUE_MTIME_DIFF_HASH_SAME,
                strategy='sync_new_mtime_from_old',
                select_all=False,
                select_count=1,
            )
            # Local pruning should remove repaired row without compare rerun.
            assert app.last_compare_result is not None
            auto_counts = app.last_compare_result.issue_counts()
            print(f'Issue counts right after local prune: {auto_counts}')
            assert auto_counts.get(COMPARE_ISSUE_MTIME_DIFF_HASH_SAME, 0) == 1

            print('\n[STEP 3] Compare after partial mtime repair')
            counts_2 = _run_compare(app, root, old_root, new_root, log_root)
            print(f'Issue counts after partial mtime repair: {counts_2}')
            assert counts_2.get(COMPARE_ISSUE_MTIME_DIFF_HASH_SAME, 0) == 1

            print('\n[STEP 4] Repair remaining mtime + all hash mismatch + missing/extra')
            _run_repair(app, root, COMPARE_ISSUE_MTIME_DIFF_HASH_SAME, 'sync_new_mtime_from_old', True)
            _run_repair(app, root, COMPARE_ISSUE_CONTENT_MISMATCH, 'copy_old_to_new', True)
            _run_repair(app, root, COMPARE_ISSUE_MISSING_IN_NEW, 'copy_old_to_new', True)
            _run_repair(app, root, COMPARE_ISSUE_EXTRA_IN_NEW, 'delete_new_file', True)
            _run_repair(app, root, COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW, 'create_dir_in_new', True)
            _run_repair(app, root, COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW, 'delete_new_dir', True)

            print('\n[STEP 5] Final compare verification')
            counts_3 = _run_compare(app, root, old_root, new_root, log_root)
            print(f'Final issue counts: {counts_3}')
            assert counts_3 == {}, f'Expected no remaining issues, got: {counts_3}'

            print('\n[STEP 6] Validate mutual failure should auto-jump to Repair with doc/res strategies')
            doc_root = temp_root / 'doc_case'
            res_root = temp_root / 'res_case'
            doc_root.mkdir(parents=True, exist_ok=True)
            res_root.mkdir(parents=True, exist_ok=True)
            mutual_rel = Path('kb') / 'entry.md'
            (doc_root / mutual_rel).parent.mkdir(parents=True, exist_ok=True)
            (doc_root / mutual_rel).write_text('doc-only', encoding='utf-8')
            orphan_rel = Path('kb') / f'orphan{app.config.placeholder_suffix}'
            (res_root / orphan_rel).mkdir(parents=True, exist_ok=True)
            doc_only_dir = Path('dirs') / 'doc_only'
            res_only_dir = Path('dirs') / 'res_only'
            (doc_root / doc_only_dir).mkdir(parents=True, exist_ok=True)
            (res_root / res_only_dir).mkdir(parents=True, exist_ok=True)

            _run_validate_mutual(app, root, doc_root, res_root, log_root)
            assert app.last_compare_result is not None
            assert app.repair_context_type == 'doc_res'
            mutual_counts = app.last_compare_result.issue_counts()
            print(f'Mutual repair issue counts: {mutual_counts}')
            assert mutual_counts.get(DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES, 0) >= 1
            assert mutual_counts.get(DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER, 0) >= 1
            assert mutual_counts.get(DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES, 0) >= 1
            assert mutual_counts.get(DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC, 0) >= 1

            _select_issue_type(app, DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES)
            strategy_keys = set(app.repair_strategy_display_map.values())
            assert 'create_res_placeholder' in strategy_keys
            assert 'delete_doc_file' in strategy_keys

            _run_repair(
                app,
                root,
                issue_type=DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
                strategy='create_res_placeholder',
                select_all=True,
            )
            expected_placeholder = res_root / mutual_rel.parent / f'{mutual_rel.name}{app.config.placeholder_suffix}'
            assert expected_placeholder.is_dir(), 'Expected placeholder should be created in res side'

            _run_repair(
                app,
                root,
                issue_type=DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
                strategy='delete_res_placeholder',
                select_all=True,
            )
            assert not (res_root / orphan_rel).exists(), 'Expected orphan placeholder should be removed'

            _run_repair(
                app,
                root,
                issue_type=DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
                strategy='create_dir_in_new',
                select_all=True,
            )
            assert (res_root / doc_only_dir).is_dir(), 'Expected missing dir should be created in res side'

            _run_repair(
                app,
                root,
                issue_type=DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
                strategy='create_dir_in_old',
                select_all=True,
            )
            assert (doc_root / res_only_dir).is_dir(), 'Expected missing dir should be created in doc side'

            print('\n[STEP 7] Split pre-check failure should auto-jump to Repair with complete strategies')
            complete_src = temp_root / 'complete_case'
            complete_src.mkdir(parents=True, exist_ok=True)
            bad_name = f'bad{app.config.placeholder_suffix}'
            (complete_src / bad_name).mkdir(parents=True, exist_ok=True)
            split_out = temp_root / 'split_case_out'
            split_out.mkdir(parents=True, exist_ok=True)

            _run_split(app, root, complete_src, split_out)
            assert app.last_compare_result is not None
            assert app.repair_context_type == 'complete'
            split_counts = app.last_compare_result.issue_counts()
            print(f'Split pre-check repair issue counts: {split_counts}')
            assert split_counts.get(COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME, 0) >= 1

            _run_repair(
                app,
                root,
                issue_type=COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
                strategy='rename_remove_placeholder_suffix',
                select_all=True,
            )
            assert (complete_src / 'bad').exists(), 'Expected folder should be renamed after complete repair'
            assert not (complete_src / bad_name).exists(), 'Old placeholder-like name should not remain'

            # Dump a concise slice of GUI log output
            gui_log_text = app.log_text.get('1.0', 'end-1c').strip().splitlines()
            print('\n[GUI LOG TAIL]')
            for line in gui_log_text[-25:]:
                print(line)

            root.destroy()

        print('\n[RESULT] PASS - GUI compare->repair flow works as expected.')
        print(f'[RESULT] Captured dialog events: {len(msg_events)}')
        return 0
    finally:
        messagebox.showinfo = original_showinfo
        messagebox.showwarning = original_showwarning
        messagebox.showerror = original_showerror
        messagebox.askyesno = original_askyesno
        gui_module.LogCapture._append_line = original_append_line
        gui_module.LogCapture._handle_progress_callbacks = original_handle_progress_callbacks
        gui_module.LogCapture._update_stage_status = original_update_stage_status


if __name__ == '__main__':
    raise SystemExit(main())
