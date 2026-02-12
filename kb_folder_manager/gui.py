"""GUI for KB Folder Manager using ttkbootstrap."""
from __future__ import annotations

import queue
import re
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable

import ttkbootstrap as ttk
from ttkbootstrap.constants import *

from . import __version__
from .config import Config, load_config, DEFAULT_CONFIG_NAME
from .operations import (
    CompareAnalysisResult,
    CompareFixResult,
    COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
    COMPLETE_ISSUE_SYMLINK,
    DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
    DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
    DOCRES_ISSUE_DOC_NON_SPECIFIED,
    DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER,
    DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
    DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC,
    DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
    DOCRES_ISSUE_RES_SPECIFIED,
    analyze_compare_operation,
    apply_complete_fixes,
    apply_compare_fixes,
    apply_doc_res_fixes,
    index_operation,
    list_fix_strategies,
    merge_operation,
    split_operation,
    validate_mutual_operation,
    validate_operation,
)
from .repair_presenter import (
    MANUAL_ISSUE_TYPE,
    build_issue_hint,
    format_hash_short,
    format_mtime,
    format_size,
    issue_type_label,
    recommended_strategy_label,
    strategy_label,
)
from .utils import FatalError, now_timestamp
from .validator import (
    COMPARE_ISSUE_CONTENT_MISMATCH,
    COMPARE_ISSUE_EXTRA_DIR_IN_NEW,
    COMPARE_ISSUE_EXTRA_IN_NEW,
    COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW,
    COMPARE_ISSUE_HASH_MISMATCH,
    COMPARE_ISSUE_MISSING_DIR_IN_NEW,
    COMPARE_ISSUE_MISSING_IN_NEW,
    COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW,
    COMPARE_ISSUE_MTIME_DIFF_HASH_SAME,
    COMPARE_ISSUE_SIZE_MISMATCH,
    CompareIssue,
    group_compare_issues_by_type,
)


class LogCapture:
    """Captures log output for display in GUI."""

    _PROGRESS_RE = re.compile(
        r'progress(?:\s*\([^)]+\))?:\s*(?:files=)?(\d+)\s*/\s*(\d+)',
        re.IGNORECASE,
    )
    _COMPARE_PATH_PATTERNS = (
        'compare: missing file in new: ',
        'compare: extra file in new: ',
        'compare: content mismatch (size/hash): ',
        'compare: size mismatch: ',
        'compare: hash mismatch: ',
        'compare: mtime differs but hash same: ',
        'compare: missing dir in new: ',
        'compare: extra dir in new: ',
        'compare: missing placeholder in new: ',
        'compare: extra placeholder in new: ',
        'repair(doc/res): doc contains non-specified file: ',
        'repair(doc/res): res contains specified file: ',
        'repair(doc/res): doc file missing placeholder in res: ',
        'repair(doc/res): res file missing placeholder in doc: ',
        'repair(doc/res): doc orphan placeholder: ',
        'repair(doc/res): res orphan placeholder: ',
        'doc directory missing in res: ',
        'res directory missing in doc: ',
        'repair(doc/res): doc directory missing in res: ',
        'repair(doc/res): res directory missing in doc: ',
        'repair(complete): placeholder-like name in complete: ',
        'repair(complete): symlink not allowed: ',
    )
    _PATH_HINT_RE = re.compile(r'\.[A-Za-z0-9]{1,10}$')
    _ISSUE_LEVELS = ('FATAL', 'ERROR', 'WARNING')
    _KEY_INFO_HINTS = (
        'started',
        'complete',
        'completed',
        'pre-check',
        'post-check',
        'building',
        'writing',
        'running',
        'queue prepared',
        'output root ready',
        'summary:',
    )

    def __init__(
        self,
        text_widget: ScrolledText,
        progress_callback: Callable[[int, int], None] | None = None,
        status_callback: Callable[[str], None] | None = None,
        line_callback: Callable[[], None] | None = None,
    ):
        self.text_widget = text_widget
        self.progress_callback = progress_callback
        self.status_callback = status_callback
        self.line_callback = line_callback
        self._buffer = ''
        self._last_progress_log_ts = 0.0
        self._last_progress_logged_current = 0
        self._last_progress_logged_percent = -1
        self._suppressed_info_lines = 0
        self._max_visible_lines = 800
        self._seen_issue_categories: set[tuple[str, str]] = set()
        self._pending_issue_groups: dict[str, dict[str, dict[str, int]]] = {
            level: {} for level in self._ISSUE_LEVELS
        }
        self._pending_issue_totals: dict[str, int] = {
            level: 0 for level in self._ISSUE_LEVELS
        }
        self._pending_path_issue_categories: dict[str, set[str]] = {}
        self._pending_issues_since_breakdown = 0
        self._pending_issues_since_snapshot = 0
        self._last_issue_snapshot_ts = time.monotonic()

    def write(self, message: str) -> None:
        """Filter and route log lines for GUI display."""
        if not message:
            return

        self._buffer += message
        while '\n' in self._buffer:
            line, self._buffer = self._buffer.split('\n', 1)
            self._process_line(line.rstrip('\r'))

    def flush(self) -> None:
        """File-like flush for stdout/stderr compatibility."""
        if self._buffer:
            self._process_line(self._buffer.rstrip('\r'))
            self._buffer = ''
        self._emit_issue_breakdown(force=True)
        self._emit_suppressed_hint_if_needed(force=True)

    def _process_line(self, line: str) -> None:
        if not line:
            return

        lower = line.lower()
        level = self._extract_level(line)
        progress = self._parse_progress(line)
        if level in self._ISSUE_LEVELS:
            issue_content = self._strip_level_prefix(line, level)
            self._record_issue(level, issue_content)
            self._maybe_emit_issue_snapshot()
            return

        show_line = False
        if progress is not None:
            current, total = progress
            show_line = self._should_show_progress_line(current, total)
        elif 'summary:' in lower:
            self._emit_issue_breakdown(force=False)
            show_line = True
        elif level == 'INFO':
            show_line = self._is_key_info(lower)
        else:
            show_line = True

        if show_line:
            self._emit_suppressed_hint_if_needed(force=(progress is None))
            self._append_line(line)
        else:
            self._suppressed_info_lines += 1

        if progress is not None:
            self._handle_progress_callbacks(line, progress)
        elif level == 'INFO':
            self._update_stage_status(lower)

    def _extract_level(self, line: str) -> str | None:
        if line.startswith('['):
            right = line.find(']')
            if right > 1:
                return line[1:right].strip().upper()
        return None

    def _strip_level_prefix(self, line: str, level: str | None) -> str:
        if not level:
            return line.strip()
        prefix = f'[{level}]'
        if line.startswith(prefix):
            return line[len(prefix):].strip()
        return line.strip()

    def _parse_progress(self, line: str) -> tuple[int, int] | None:
        m = self._PROGRESS_RE.search(line)
        if not m:
            return None
        try:
            current = int(m.group(1))
            total = int(m.group(2))
        except ValueError:
            return None
        if total <= 0:
            return None
        return current, total

    def _should_show_progress_line(self, current: int, total: int) -> bool:
        now = time.monotonic()
        percent = int((current / total) * 100)
        # Keep GUI progress lines concise: show roughly every 5% (or every 3s), plus first/last.
        should_show = (
            current >= total
            or self._last_progress_logged_current == 0
            or (percent - self._last_progress_logged_percent) >= 5
            or (now - self._last_progress_log_ts) >= 3.0
        )
        if should_show:
            self._last_progress_logged_current = current
            self._last_progress_logged_percent = percent
            self._last_progress_log_ts = now
        return should_show

    def _is_key_info(self, lower: str) -> bool:
        return any(hint in lower for hint in self._KEY_INFO_HINTS)

    def _emit_suppressed_hint_if_needed(self, force: bool = False) -> None:
        if self._suppressed_info_lines <= 0:
            return
        if not force and self._suppressed_info_lines < 50:
            return
        hint = (
            f'[INFO] (GUI 已省略 {self._suppressed_info_lines} 条详细日志；'
            '完整内容请查看输出目录日志文件)'
        )
        self._append_line(hint)
        self._suppressed_info_lines = 0

    def _record_issue(self, level: str, issue_content: str) -> None:
        category, item, has_path = self._extract_issue_category_and_item(issue_content)
        level_groups = self._pending_issue_groups[level]
        item_counts = level_groups.setdefault(category, {})
        item_counts[item] = item_counts.get(item, 0) + 1
        self._pending_issue_totals[level] += 1
        self._pending_issues_since_breakdown += 1
        self._pending_issues_since_snapshot += 1

        if has_path:
            cats = self._pending_path_issue_categories.setdefault(item, set())
            cats.add(f'{level}:{category}')

        issue_key = (level, category)
        if issue_key not in self._seen_issue_categories:
            self._seen_issue_categories.add(issue_key)
            preview = self._shorten_text(item, 90) if has_path else self._shorten_text(issue_content, 90)
            self._append_line(f'[{level}] 问题类别: {category} | 示例: {preview}')

    def _extract_issue_category_and_item(self, issue_content: str) -> tuple[str, str, bool]:
        text = issue_content.strip()
        if not text:
            return 'unknown issue', 'unknown issue', False

        extracted = self._extract_issue_by_known_patterns(text)
        if extracted is not None:
            return extracted

        for token in (' for ', ': '):
            if token not in text:
                continue
            head, tail = text.rsplit(token, 1)
            candidate = tail.strip()
            if self._looks_like_path(candidate):
                category = head.strip()
                if not category:
                    category = text
                return category, candidate, True

        return text, text, False

    def _extract_issue_by_known_patterns(self, text: str) -> tuple[str, str, bool] | None:
        lower = text.lower()
        for prefix in self._COMPARE_PATH_PATTERNS:
            if lower.startswith(prefix):
                return prefix[:-2], text[len(prefix):].strip(), True
        return None

    def _looks_like_path(self, value: str) -> bool:
        s = value.strip()
        if not s:
            return False
        lower = s.lower()
        if ' old=' in lower or ' new=' in lower or ' vs ' in lower:
            return False
        if '/' in s or '\\' in s:
            return True
        if self._PATH_HINT_RE.search(s):
            return True
        return False

    def _maybe_emit_issue_snapshot(self) -> None:
        if self._pending_issues_since_snapshot <= 0:
            return
        now = time.monotonic()
        total = sum(self._pending_issue_totals.values())
        if total < 200:
            return
        if self._pending_issues_since_snapshot < 300 and (now - self._last_issue_snapshot_ts) < 12.0:
            return
        f = self._pending_issue_totals['FATAL']
        e = self._pending_issue_totals['ERROR']
        w = self._pending_issue_totals['WARNING']
        self._append_line(f'[DIAG] 问题累计: FATAL={f}, ERROR={e}, WARNING={w}（阶段汇总将按类别展示）')
        self._pending_issues_since_snapshot = 0
        self._last_issue_snapshot_ts = now

    def _emit_issue_breakdown(self, force: bool = False) -> None:
        if self._pending_issues_since_breakdown <= 0 and not force:
            return
        total_pending = sum(self._pending_issue_totals.values())
        if total_pending <= 0:
            return

        f = self._pending_issue_totals['FATAL']
        e = self._pending_issue_totals['ERROR']
        w = self._pending_issue_totals['WARNING']
        self._append_line(f'[DIAG] 问题分类汇总: FATAL={f}, ERROR={e}, WARNING={w}')

        for level in self._ISSUE_LEVELS:
            groups = self._pending_issue_groups[level]
            if not groups:
                continue
            sorted_categories = sorted(groups.keys())
            for category in sorted_categories:
                item_counts = groups[category]
                sorted_items = sorted(item_counts.keys())
                unique_count = len(sorted_items)
                hit_count = sum(item_counts.values())
                self._append_line(f'[DIAG][{level}] {category} | paths={unique_count}, hits={hit_count}')
                show_n = min(5, unique_count)
                for item in sorted_items[:show_n]:
                    self._append_line(f'  - {self._shorten_text(item, 110)}')
                if unique_count > show_n:
                    self._append_line(f'  - ... +{unique_count - show_n} more')

        multi_issue_paths = [
            (path, cats)
            for path, cats in self._pending_path_issue_categories.items()
            if len(cats) > 1
        ]
        if multi_issue_paths:
            self._append_line(f'[DIAG] 同一路径存在多类问题: {len(multi_issue_paths)} 个')
            for path, cats in sorted(multi_issue_paths, key=lambda x: x[0])[:5]:
                cat_text = ' | '.join(sorted(cats))
                self._append_line(f'  - {self._shorten_text(path, 100)} => {self._shorten_text(cat_text, 120)}')
            if len(multi_issue_paths) > 5:
                self._append_line(f'  - ... +{len(multi_issue_paths) - 5} more')

        self._pending_issue_groups = {level: {} for level in self._ISSUE_LEVELS}
        self._pending_issue_totals = {level: 0 for level in self._ISSUE_LEVELS}
        self._pending_path_issue_categories = {}
        self._pending_issues_since_breakdown = 0
        self._pending_issues_since_snapshot = 0

    def _shorten_text(self, text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return '...' + text[-(max_len - 3):]

    def _append_line(self, line: str) -> None:
        if threading.current_thread() is not threading.main_thread():
            try:
                self.text_widget.after(0, lambda: self._append_line(line))
            except Exception:
                pass
            return
        gui_line = self._simplify_line_for_gui(line)
        self.text_widget.insert(END, gui_line + '\n')
        self.text_widget.see(END)
        try:
            total_lines = int(self.text_widget.index('end-1c').split('.')[0])
            if total_lines > self._max_visible_lines:
                delete_upto = total_lines - self._max_visible_lines
                self.text_widget.delete('1.0', f'{delete_upto + 1}.0')
        except Exception:
            # Never fail operation due to UI log trimming issues.
            pass
        if self.line_callback:
            try:
                self.line_callback()
            except Exception:
                pass
        self.text_widget.update_idletasks()

    def _simplify_line_for_gui(self, line: str) -> str:
        lower = line.lower()
        marker = '| current:'
        if 'progress' in lower and marker in lower:
            idx = lower.find(marker)
            if idx > 0:
                return line[:idx].rstrip()
        return line

    def _handle_progress_callbacks(self, line: str, progress: tuple[int, int]) -> None:
        current, total = progress
        if self.progress_callback:
            self._run_on_ui_thread(self.progress_callback, current, total)

        if not self.status_callback:
            return

        lower = line.lower()
        marker = '| current:'
        if marker in lower:
            idx = lower.find(marker)
            current_file = line[idx + len(marker):].strip()
            if len(current_file) > 60:
                current_file = '...' + current_file[-57:]
            self._run_on_ui_thread(self.status_callback, f"Processing [{current}/{total}]: {current_file}")
        else:
            percent = int((current / total) * 100)
            self._run_on_ui_thread(self.status_callback, f"Processing [{current}/{total}] ({percent}%)")

    def _update_stage_status(self, lower: str) -> None:
        if not self.status_callback:
            return
        if 'started' in lower:
            self._run_on_ui_thread(self.status_callback, "Operation started...")
        elif 'building' in lower and 'index' in lower:
            self._run_on_ui_thread(self.status_callback, "Building index...")
        elif 'validation' in lower or 'validating' in lower:
            self._run_on_ui_thread(self.status_callback, "Validating...")
        elif 'writing' in lower and 'index' in lower:
            self._run_on_ui_thread(self.status_callback, "Writing indexes...")

    def _run_on_ui_thread(self, callback: Callable, *args: Any) -> None:
        if threading.current_thread() is threading.main_thread():
            callback(*args)
            return
        try:
            self.text_widget.after(0, lambda: callback(*args))
        except Exception:
            pass


class MultiLogCapture:
    """Fan-out log output to multiple capture sinks."""

    def __init__(self, *targets: Any):
        self.targets = [t for t in targets if t is not None]

    def write(self, message: str) -> None:
        for target in self.targets:
            target.write(message)

    def flush(self) -> None:
        for target in self.targets:
            try:
                target.flush()
            except Exception:
                pass



class OperationThread(threading.Thread):
    """Thread for running operations without blocking GUI."""
    
    def __init__(self, operation: Callable, result_queue: queue.Queue, 
                 log_capture: LogCapture | None = None, *args, **kwargs):
        super().__init__(daemon=True)
        self.operation = operation
        self.result_queue = result_queue
        self.log_capture = log_capture
        self.args = args
        self.kwargs = kwargs
        
    def run(self) -> None:
        """Execute operation and put result in queue."""
        import sys
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        try:
            # Redirect stdout/stderr to GUI if log_capture provided
            if self.log_capture:
                sys.stdout = self.log_capture
                sys.stderr = self.log_capture
            
            result = self.operation(*self.args, **self.kwargs)
            self.result_queue.put(('success', 'Operation completed successfully!', result))
        except FatalError as e:
            self.result_queue.put(('fatal', str(e), None))
        except Exception as e:
            self.result_queue.put(('error', str(e), None))
        finally:
            if self.log_capture:
                try:
                    self.log_capture.flush()
                except Exception:
                    pass
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class KBFolderManagerGUI:
    """Main GUI application for KB Folder Manager."""
    
    VERSION = __version__
    
    def __init__(self, root: ttk.Window):
        self.root = root
        self.root.title(f"KB Folder Manager v{self.VERSION}")
        self.root.geometry("1240x800")
        self.root.minsize(980, 680)
        
        # Load config
        self.config: Config | None = None
        self.config_path = Path(DEFAULT_CONFIG_NAME)
        self.load_config()
        
        # Operation state
        self.operation_running = False
        self.result_queue: queue.Queue = queue.Queue()
        self._status_base_text = 'Ready'
        self._spinner_frames = ('|', '/', '-', '\\')
        self._spinner_index = 0
        self._spinner_after_id: str | None = None
        self._operation_started_at: float | None = None
        self._current_operation_name = ''
        self._progress_indeterminate = False
        self._pending_validate_context: dict[str, Any] | None = None
        self._pending_merge_context: dict[str, Any] | None = None
        self._pending_split_context: dict[str, Any] | None = None
        self._last_log_update_ts = time.monotonic()
        self._last_heartbeat_emit_ts = 0.0

        # Compare/repair state
        self.repair_context_type = 'compare'
        self.last_compare_result: CompareAnalysisResult | None = None
        self.repair_issue_groups: dict[str, list[CompareIssue]] = {}
        self.repair_display_map: dict[str, str] = {}
        self.repair_strategy_display_map: dict[str, str] = {}
        self.repair_issue_item_map: dict[str, CompareIssue] = {}
        
        # Setup UI
        self.setup_ui()
        
        # Check for operation results periodically
        self.check_operation_results()
        
    def load_config(self) -> None:
        """Load configuration file."""
        try:
            self.config = load_config(self.config_path)
        except Exception as e:
            messagebox.showerror("Config Error", f"Failed to load config: {e}")
            
    def setup_ui(self) -> None:
        """Setup main UI components."""
        self.activity_var = ttk.StringVar(value="Idle")

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # Create tabs
        self.split_frame = ttk.Frame(self.notebook)
        self.merge_frame = ttk.Frame(self.notebook)
        self.validate_frame = ttk.Frame(self.notebook)
        self.repair_frame = ttk.Frame(self.notebook)
        self.index_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.split_frame, text="Split")
        self.notebook.add(self.merge_frame, text="Merge")
        self.notebook.add(self.validate_frame, text="Validate")
        self.notebook.add(self.repair_frame, text="Repair")
        self.notebook.add(self.index_frame, text="Index")
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Setup each tab
        self.setup_split_tab()
        self.setup_merge_tab()
        self.setup_validate_tab()
        self.setup_repair_tab()
        self.setup_index_tab()
        self.setup_settings_tab()
        
        # Progress bar (shared across all tabs)
        progress_frame = ttk.Frame(self.root)
        progress_frame.pack(fill=X, padx=10, pady=5)
        
        ttk.Label(progress_frame, text="Progress:", font=("Arial", 10, "bold")).pack(side=LEFT, padx=5)
        self.progress_var = ttk.IntVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            maximum=100, 
            bootstyle="success-striped"
        )
        self.progress_bar.pack(side=LEFT, fill=X, expand=YES, padx=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready", font=("Arial", 9))
        self.status_label.pack(side=RIGHT, padx=5)
        
        # Log output area (shared)
        log_frame = ttk.Labelframe(self.root, text="Log Output", bootstyle="info")
        log_frame.pack(fill=BOTH, expand=YES, padx=10, pady=5)

        activity_frame = ttk.Frame(log_frame)
        activity_frame.pack(fill=X, padx=5, pady=(5, 0))
        ttk.Label(activity_frame, text="Activity:", font=("Arial", 9, "bold")).pack(side=LEFT)
        ttk.Label(activity_frame, textvariable=self.activity_var, bootstyle="secondary").pack(
            side=LEFT, padx=(6, 0)
        )
        
        self.log_text = ScrolledText(log_frame, height=10, wrap=WORD, state=NORMAL)
        self.log_text.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
    def setup_split_tab(self) -> None:
        """Setup Split operation tab."""
        frame = self.split_frame
        
        # Input section
        input_frame = ttk.Labelframe(frame, text="Split Configuration", padding=15, bootstyle="primary")
        input_frame.pack(fill=X, padx=10, pady=10)
        
        # Source folder
        ttk.Label(input_frame, text="Source (Complete Folder):", font=("Arial", 10)).grid(
            row=0, column=0, sticky=W, pady=5
        )
        self.split_source_var = ttk.StringVar()
        ttk.Entry(input_frame, textvariable=self.split_source_var, width=50).grid(
            row=0, column=1, padx=5, pady=5, sticky=EW
        )
        ttk.Button(
            input_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.split_source_var),
            bootstyle="info-outline"
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Output root
        ttk.Label(input_frame, text="Output Root:", font=("Arial", 10)).grid(
            row=1, column=0, sticky=W, pady=5
        )
        self.split_output_var = ttk.StringVar()
        ttk.Entry(input_frame, textvariable=self.split_output_var, width=50).grid(
            row=1, column=1, padx=5, pady=5, sticky=EW
        )
        ttk.Button(
            input_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.split_output_var),
            bootstyle="info-outline"
        ).grid(row=1, column=2, padx=5, pady=5)
        
        input_frame.columnconfigure(1, weight=1)
        
        # Options
        options_frame = ttk.Labelframe(frame, text="Options", padding=15, bootstyle="secondary")
        options_frame.pack(fill=X, padx=10, pady=10)
        
        self.split_force_var = ttk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, 
            text="Force (Allow non-empty output root)", 
            variable=self.split_force_var,
            bootstyle="warning-round-toggle"
        ).pack(anchor=W, pady=5)
        
        self.split_auto_yes_var = ttk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, 
            text="Auto-confirm (Skip confirmation prompts)", 
            variable=self.split_auto_yes_var,
            bootstyle="info-round-toggle"
        ).pack(anchor=W, pady=5)
        
        # Execute button
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Execute Split Operation", 
            command=self.execute_split,
            bootstyle="success",
            width=30
        ).pack(pady=10)

        self._create_inline_log_section(frame, "Split Log (Current Tab)", "split_log_text")
        
    def setup_merge_tab(self) -> None:
        """Setup Merge operation tab."""
        frame = self.merge_frame
        
        # Input section
        input_frame = ttk.Labelframe(frame, text="Merge Configuration", padding=15, bootstyle="primary")
        input_frame.pack(fill=X, padx=10, pady=10)
        
        # Doc folder
        ttk.Label(input_frame, text="Doc Folder:", font=("Arial", 10)).grid(
            row=0, column=0, sticky=W, pady=5
        )
        self.merge_doc_var = ttk.StringVar()
        ttk.Entry(input_frame, textvariable=self.merge_doc_var, width=50).grid(
            row=0, column=1, padx=5, pady=5, sticky=EW
        )
        ttk.Button(
            input_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.merge_doc_var),
            bootstyle="info-outline"
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Res folder
        ttk.Label(input_frame, text="Res Folder:", font=("Arial", 10)).grid(
            row=1, column=0, sticky=W, pady=5
        )
        self.merge_res_var = ttk.StringVar()
        ttk.Entry(input_frame, textvariable=self.merge_res_var, width=50).grid(
            row=1, column=1, padx=5, pady=5, sticky=EW
        )
        ttk.Button(
            input_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.merge_res_var),
            bootstyle="info-outline"
        ).grid(row=1, column=2, padx=5, pady=5)
        
        # Output root
        ttk.Label(input_frame, text="Output Root:", font=("Arial", 10)).grid(
            row=2, column=0, sticky=W, pady=5
        )
        self.merge_output_var = ttk.StringVar()
        ttk.Entry(input_frame, textvariable=self.merge_output_var, width=50).grid(
            row=2, column=1, padx=5, pady=5, sticky=EW
        )
        ttk.Button(
            input_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.merge_output_var),
            bootstyle="info-outline"
        ).grid(row=2, column=2, padx=5, pady=5)
        
        input_frame.columnconfigure(1, weight=1)
        
        # Options
        options_frame = ttk.Labelframe(frame, text="Options", padding=15, bootstyle="secondary")
        options_frame.pack(fill=X, padx=10, pady=10)
        
        self.merge_force_var = ttk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, 
            text="Force (Allow non-empty output root)", 
            variable=self.merge_force_var,
            bootstyle="warning-round-toggle"
        ).pack(anchor=W, pady=5)
        
        self.merge_auto_yes_var = ttk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, 
            text="Auto-confirm (Skip confirmation prompts)", 
            variable=self.merge_auto_yes_var,
            bootstyle="info-round-toggle"
        ).pack(anchor=W, pady=5)
        
        # Execute button
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Execute Merge Operation", 
            command=self.execute_merge,
            bootstyle="success",
            width=30
        ).pack(pady=10)

        self._create_inline_log_section(frame, "Merge Log (Current Tab)", "merge_log_text")
        
    def setup_validate_tab(self) -> None:
        """Setup Validate operation tab."""
        frame = self.validate_frame
        
        # Mode selection
        mode_frame = ttk.Labelframe(frame, text="Validation Mode", padding=15, bootstyle="primary")
        mode_frame.pack(fill=X, padx=10, pady=10)
        
        self.validate_mode_var = ttk.StringVar(value="class1")
        
        modes = [
            ("Class1 (Basic & Environment)", "class1"),
            ("Class2 (Type Purity)", "class2"),
            ("Mutual (Doc/Res Consistency)", "mutual"),
            ("Compare (Hash/Size Verification)", "compare")
        ]
        
        for text, mode in modes:
            ttk.Radiobutton(
                mode_frame, 
                text=text, 
                variable=self.validate_mode_var, 
                value=mode,
                command=self.update_validate_inputs,
                bootstyle="info-toolbutton"
            ).pack(anchor=W, pady=3)
        
        # Input section (dynamic based on mode)
        self.validate_input_frame = ttk.Labelframe(frame, text="Input Configuration", padding=15, bootstyle="secondary")
        self.validate_input_frame.pack(fill=X, padx=10, pady=10)
        
        self.validate_widgets: dict[str, Any] = {}
        self.update_validate_inputs()
        
        # Log directory
        log_frame = ttk.Frame(frame)
        log_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Label(log_frame, text="Log Directory:", font=("Arial", 10)).pack(side=LEFT, padx=5)
        self.validate_log_dir_var = ttk.StringVar()
        ttk.Entry(log_frame, textvariable=self.validate_log_dir_var, width=40).pack(
            side=LEFT, fill=X, expand=YES, padx=5
        )
        ttk.Button(
            log_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.validate_log_dir_var),
            bootstyle="info-outline"
        ).pack(side=LEFT, padx=5)
        
        # Execute button
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Execute Validation", 
            command=self.execute_validate,
            bootstyle="success",
            width=30
        ).pack(pady=10)

        self._create_inline_log_section(frame, "Validation Log (Current Tab)", "validate_log_text")

    def setup_repair_tab(self) -> None:
        """Setup batch repair tab for compare issues."""
        frame = self.repair_frame

        context_frame = ttk.Labelframe(frame, text="Compare Context", padding=12, bootstyle="primary")
        context_frame.pack(fill=X, padx=10, pady=10)

        self.repair_old_var = ttk.StringVar(value="(No compare result yet)")
        self.repair_new_var = ttk.StringVar(value="(No compare result yet)")
        self.repair_summary_var = ttk.StringVar(value="Run Validate -> Compare first.")

        ttk.Label(context_frame, text="Folder 1:", font=("Arial", 10, "bold")).grid(
            row=0, column=0, sticky=W, pady=3
        )
        ttk.Label(context_frame, textvariable=self.repair_old_var).grid(
            row=0, column=1, sticky=W, pady=3
        )
        ttk.Label(context_frame, text="Folder 2:", font=("Arial", 10, "bold")).grid(
            row=1, column=0, sticky=W, pady=3
        )
        ttk.Label(context_frame, textvariable=self.repair_new_var).grid(
            row=1, column=1, sticky=W, pady=3
        )
        ttk.Label(context_frame, textvariable=self.repair_summary_var, bootstyle="secondary").grid(
            row=2, column=0, columnspan=2, sticky=W, pady=3
        )
        context_frame.columnconfigure(1, weight=1)

        controls_frame = ttk.Labelframe(frame, text="Batch Repair", padding=12, bootstyle="secondary")
        controls_frame.pack(fill=X, padx=10, pady=10)

        ttk.Label(controls_frame, text="Issue Type:").grid(row=0, column=0, sticky=W, pady=4)
        self.repair_issue_type_var = ttk.StringVar()
        self.repair_issue_type_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.repair_issue_type_var,
            values=[],
            state="readonly",
            width=40,
        )
        self.repair_issue_type_combo.grid(row=0, column=1, sticky=EW, padx=5, pady=4)
        self.repair_issue_type_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_repair_issue_type_changed())

        ttk.Label(controls_frame, text="Strategy:").grid(row=1, column=0, sticky=W, pady=4)
        self.repair_strategy_var = ttk.StringVar()
        self.repair_strategy_combo = ttk.Combobox(
            controls_frame,
            textvariable=self.repair_strategy_var,
            values=[],
            state="readonly",
            width=40,
        )
        self.repair_strategy_combo.grid(row=1, column=1, sticky=EW, padx=5, pady=4)

        ttk.Button(
            controls_frame,
            text="Select All",
            command=self.repair_select_all,
            bootstyle="info-outline",
            width=14,
        ).grid(row=0, column=2, padx=4, pady=4)

        ttk.Button(
            controls_frame,
            text="Clear Selection",
            command=self.repair_clear_selection,
            bootstyle="secondary-outline",
            width=14,
        ).grid(row=1, column=2, padx=4, pady=4)

        ttk.Button(
            controls_frame,
            text="Apply to Selected",
            command=self.execute_repair,
            bootstyle="warning",
            width=18,
        ).grid(row=0, column=3, rowspan=2, padx=8, pady=4)

        controls_frame.columnconfigure(1, weight=1)

        list_frame = ttk.Labelframe(
            frame,
            text="Issue Comparison (multi-select supported)",
            padding=12,
            bootstyle="info",
        )
        list_frame.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        tree_columns = (
            "path",
            "folder1_size",
            "folder2_size",
            "folder1_mtime",
            "folder2_mtime",
            "folder1_hash",
            "folder2_hash",
            "hint",
        )
        self.repair_tree = ttk.Treeview(
            list_frame,
            columns=tree_columns,
            show="headings",
            selectmode="extended",
            height=10,
        )
        self.repair_tree.heading("path", text="Relative Path")
        self.repair_tree.heading("folder1_size", text="Folder1 Size")
        self.repair_tree.heading("folder2_size", text="Folder2 Size")
        self.repair_tree.heading("folder1_mtime", text="Folder1 MTime")
        self.repair_tree.heading("folder2_mtime", text="Folder2 MTime")
        self.repair_tree.heading("folder1_hash", text="Folder1 Hash")
        self.repair_tree.heading("folder2_hash", text="Folder2 Hash")
        self.repair_tree.heading("hint", text="Hint")

        self.repair_tree.column("path", width=360, minwidth=260, anchor=W, stretch=True)
        self.repair_tree.column("folder1_size", width=120, minwidth=100, anchor=W, stretch=False)
        self.repair_tree.column("folder2_size", width=120, minwidth=100, anchor=W, stretch=False)
        self.repair_tree.column("folder1_mtime", width=160, minwidth=150, anchor=W, stretch=False)
        self.repair_tree.column("folder2_mtime", width=160, minwidth=150, anchor=W, stretch=False)
        self.repair_tree.column("folder1_hash", width=160, minwidth=140, anchor=W, stretch=False)
        self.repair_tree.column("folder2_hash", width=160, minwidth=140, anchor=W, stretch=False)
        self.repair_tree.column("hint", width=320, minwidth=240, anchor=W, stretch=True)
        self.repair_tree.bind("<<TreeviewSelect>>", lambda _e: self._on_repair_selection_changed())

        tree_container = ttk.Frame(list_frame)
        tree_container.grid(row=0, column=0, sticky=NSEW)
        scrollbar = ttk.Scrollbar(tree_container, orient=VERTICAL, command=self.repair_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient=HORIZONTAL, command=self.repair_tree.xview)
        scrollbar.pack(side=RIGHT, fill=Y)
        h_scrollbar.pack(side=BOTTOM, fill=X)
        self.repair_tree.pack(in_=tree_container, side=LEFT, fill=BOTH, expand=YES)
        self.repair_tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=h_scrollbar.set)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        detail_frame = ttk.Labelframe(frame, text="Selected Item Details", padding=12, bootstyle="secondary")
        detail_frame.pack(fill=X, padx=10, pady=(0, 10))
        self.repair_detail_text = ScrolledText(detail_frame, height=7, wrap=WORD)
        self.repair_detail_text.pack(fill=X, expand=YES)
        self.repair_detail_text.insert(END, "Select an issue row to view full metadata and recommendation.")
        self.repair_detail_text.config(state=DISABLED)

        self.repair_selection_status_var = ttk.StringVar(value="Selected: 0 / 0")
        ttk.Label(frame, textvariable=self.repair_selection_status_var, bootstyle="secondary").pack(
            anchor=W, padx=14, pady=(0, 10)
        )

        self._create_inline_log_section(frame, "Repair Log (Current Tab)", "repair_log_text", height=7)

    def _on_repair_issue_type_changed(self) -> None:
        self._update_repair_strategy_options()
        self._refresh_repair_issue_list()

    def _issue_type_from_display(self, display_value: str) -> str | None:
        return self.repair_display_map.get(display_value)

    def _strategy_from_display(self, display_value: str) -> str | None:
        return self.repair_strategy_display_map.get(display_value)

    def _update_repair_strategy_options(self) -> None:
        issue_type = self._issue_type_from_display(self.repair_issue_type_var.get())
        if not issue_type:
            self.repair_strategy_combo['values'] = []
            self.repair_strategy_var.set('')
            return

        strategies = list_fix_strategies(issue_type)
        display_values: list[str] = []
        self.repair_strategy_display_map.clear()
        for strategy in strategies:
            label = strategy_label(strategy)
            display = f"{label} [{strategy}]"
            self.repair_strategy_display_map[display] = strategy
            display_values.append(display)

        self.repair_strategy_combo['values'] = display_values
        if display_values:
            self.repair_strategy_var.set(display_values[0])
        else:
            self.repair_strategy_var.set('')

    def _refresh_repair_issue_list(self) -> None:
        self.repair_issue_item_map.clear()
        for item in self.repair_tree.get_children():
            self.repair_tree.delete(item)

        issue_type = self._issue_type_from_display(self.repair_issue_type_var.get())
        items = self.repair_issue_groups.get(issue_type, []) if issue_type else []
        for idx, issue in enumerate(items):
            iid = f'{idx:08d}'
            row_values = self._build_repair_tree_row(issue)
            self.repair_tree.insert('', END, iid=iid, values=row_values)
            self.repair_issue_item_map[iid] = issue
        self._on_repair_selection_changed()

    def _build_repair_tree_row(
        self,
        issue: CompareIssue,
    ) -> tuple[str, str, str, str, str, str, str, str]:
        details = issue.details or {}
        old_size = format_size(details.get('old_size'))
        new_size = format_size(details.get('new_size'))
        old_mtime = format_mtime(details.get('old_mtime'))
        new_mtime = format_mtime(details.get('new_mtime'))
        old_hash = format_hash_short(details.get('old_hash'))
        new_hash = format_hash_short(details.get('new_hash'))
        hint = build_issue_hint(issue)
        return (
            issue.rel_path,
            old_size,
            new_size,
            old_mtime,
            new_mtime,
            old_hash,
            new_hash,
            hint,
        )

    def _format_size(self, value: Any) -> str:
        return format_size(value)

    def _format_mtime(self, value: Any) -> str:
        return format_mtime(value)

    def _build_issue_hint(self, issue: CompareIssue) -> str:
        return build_issue_hint(issue)

    def _on_repair_selection_changed(self) -> None:
        self._update_repair_selection_status()
        selection = self.repair_tree.selection()
        if len(selection) != 1:
            self._set_repair_detail_text('Select exactly one row to view full metadata.')
            return
        issue = self.repair_issue_item_map.get(selection[0])
        if not issue:
            self._set_repair_detail_text('No detail data found for selected row.')
            return
        self._set_repair_detail_text(self._build_issue_detail_text(issue))

    def _set_repair_detail_text(self, text: str) -> None:
        self.repair_detail_text.config(state=NORMAL)
        self.repair_detail_text.delete('1.0', END)
        self.repair_detail_text.insert(END, text)
        self.repair_detail_text.config(state=DISABLED)

    def _build_issue_detail_text(self, issue: CompareIssue) -> str:
        details = issue.details or {}
        recommended = self._recommend_strategy_for_issue(issue)
        issue_label = issue_type_label(issue.issue_type)
        mtime_delta = details.get('mtime_delta_seconds')
        mtime_delta_text = (
            f'{int(round(float(mtime_delta))):+d}s'
            if isinstance(mtime_delta, (int, float))
            else '-'
        )
        lines = [
            f'Issue Type: {issue_label} [{issue.issue_type}]',
            f'Path: {issue.rel_path}',
            f'Recommended Strategy: {recommended}',
            '',
            f'Folder1 size: {self._format_size(details.get("old_size"))}',
            f'Folder2 size: {self._format_size(details.get("new_size"))}',
            f'Folder1 mtime: {self._format_mtime(details.get("old_mtime"))}',
            f'Folder2 mtime: {self._format_mtime(details.get("new_mtime"))}',
            f'MTime delta (old-new): {mtime_delta_text}',
            f'Folder1 hash: {details.get("old_hash") or "-"}',
            f'Folder2 hash: {details.get("new_hash") or "-"}',
        ]
        placeholder_path = details.get('placeholder_path')
        if placeholder_path:
            lines.append(f'Expected placeholder path: {placeholder_path}')
        original_rel = details.get('original_rel_path')
        if original_rel:
            lines.append(f'Placeholder maps to: {original_rel}')
        return '\n'.join(lines)

    def _recommend_strategy_for_issue(self, issue: CompareIssue) -> str:
        return recommended_strategy_label(issue)

    def _update_repair_selection_status(self) -> None:
        selected = len(self.repair_tree.selection())
        total = len(self.repair_tree.get_children())
        self.repair_selection_status_var.set(f"Selected: {selected} / {total}")

    def repair_select_all(self) -> None:
        all_items = self.repair_tree.get_children()
        self.repair_tree.selection_set(all_items)
        self._on_repair_selection_changed()

    def repair_clear_selection(self) -> None:
        self.repair_tree.selection_set(())
        self._on_repair_selection_changed()

    def load_compare_result_for_repair(
        self,
        result: CompareAnalysisResult,
        context_type: str = 'compare',
        summary_title: str = 'Compare',
    ) -> None:
        self.repair_context_type = context_type
        self.last_compare_result = result
        self.repair_old_var.set(str(result.old_path))
        self.repair_new_var.set(str(result.new_path))

        grouped = group_compare_issues_by_type(result.issues)
        self.repair_issue_groups = dict(grouped)

        total_issues = len(result.issues)
        total_fixable = sum(
            len(issues)
            for issue_type, issues in self.repair_issue_groups.items()
            if list_fix_strategies(issue_type)
        )
        self.repair_summary_var.set(
            f"{summary_title} finished: total_issues={total_issues}, fixable={total_fixable}. "
            f"Select issue type and strategy for batch repair."
        )

        display_values: list[str] = []
        self.repair_display_map.clear()
        for issue_type in sorted(self.repair_issue_groups.keys()):
            count = len(self.repair_issue_groups[issue_type])
            label = issue_type_label(issue_type)
            display = f"{label} [{issue_type}] ({count})"
            self.repair_display_map[display] = issue_type
            display_values.append(display)

        self.repair_issue_type_combo['values'] = display_values
        if display_values:
            self.repair_issue_type_var.set(display_values[0])
            self._on_repair_issue_type_changed()
        else:
            self.repair_issue_type_var.set('')
            self.repair_strategy_combo['values'] = []
            self.repair_strategy_var.set('')
            self._refresh_repair_issue_list()
            self._set_repair_detail_text('No batch-fixable issues found.')

    def execute_repair(self) -> None:
        """Execute batch repair for selected compare issues."""
        if self.operation_running:
            messagebox.showwarning("Operation Running", "Another operation is already running!")
            return

        if not self.last_compare_result:
            messagebox.showerror("Input Error", "No compare result available. Run Validate -> Compare first.")
            return

        issue_display = self.repair_issue_type_var.get()
        issue_type = self._issue_type_from_display(issue_display)
        if not issue_type:
            messagebox.showerror("Input Error", "Please choose an issue type.")
            return

        strategy_display = self.repair_strategy_var.get()
        strategy = self._strategy_from_display(strategy_display)
        if not strategy:
            messagebox.showerror("Input Error", "Please choose a repair strategy.")
            return

        selected_items = self.repair_tree.selection()
        if not selected_items:
            messagebox.showerror("Input Error", "Please select at least one issue path.")
            return

        selected_paths = [self.repair_tree.item(iid, 'values')[0] for iid in selected_items]
        if not selected_paths:
            messagebox.showerror("Input Error", "Failed to read selected issue paths.")
            return

        confirm = messagebox.askyesno(
            "Confirm Batch Repair",
            f"Issue type: {issue_type}\n"
            f"Strategy: {strategy}\n"
            f"Selected items: {len(selected_paths)}\n\n"
            f"Apply changes now?",
        )
        if not confirm:
            return

        log_root_raw = self.validate_log_dir_var.get().strip()
        if log_root_raw:
            log_dir_path = Path(log_root_raw) / now_timestamp()
        else:
            log_dir_path = self.last_compare_result.new_path / '.kbfm_repair_logs' / now_timestamp()

        self.clear_log()
        self._clear_text_widget(getattr(self, 'repair_log_text', None))
        self._pending_validate_context = None
        self._pending_merge_context = None
        self._pending_split_context = None
        self._set_progress_indeterminate(False)
        self.progress_var.set(0)
        self.set_status("Running batch repair...")
        self.operation_running = True
        self._current_operation_name = 'repair'
        self._reset_runtime_feedback_clock()
        self._start_status_spinner()
        self._set_progress_indeterminate(True)

        log_capture = self._build_log_capture(getattr(self, 'repair_log_text', None))

        if self.repair_context_type == 'compare':
            thread = OperationThread(
                apply_compare_fixes,
                self.result_queue,
                log_capture,
                self.last_compare_result.old_path,
                self.last_compare_result.new_path,
                issue_type,
                strategy,
                selected_paths,
                log_dir_path,
            )
        elif self.repair_context_type == 'doc_res':
            thread = OperationThread(
                apply_doc_res_fixes,
                self.result_queue,
                log_capture,
                self.last_compare_result.old_path,
                self.last_compare_result.new_path,
                self.config,
                issue_type,
                strategy,
                selected_paths,
                log_dir_path,
            )
        elif self.repair_context_type == 'complete':
            thread = OperationThread(
                apply_complete_fixes,
                self.result_queue,
                log_capture,
                self.last_compare_result.old_path,
                self.config,
                issue_type,
                strategy,
                selected_paths,
                log_dir_path,
            )
        else:
            messagebox.showerror("Error", f"Unknown repair context: {self.repair_context_type}")
            self.operation_running = False
            self._current_operation_name = ''
            self._stop_status_spinner()
            self._set_progress_indeterminate(False)
            return
        thread.start()

        self.log_message(
            f"[INFO] Starting repair: issue_type={issue_type}, strategy={strategy}, selected={len(selected_paths)}"
        )
        
    def setup_index_tab(self) -> None:
        """Setup Index operation tab."""
        frame = self.index_frame
        
        # Input section
        input_frame = ttk.Labelframe(frame, text="Index Configuration", padding=15, bootstyle="primary")
        input_frame.pack(fill=X, padx=10, pady=10)
        
        # Target folder
        ttk.Label(input_frame, text="Target Folder:", font=("Arial", 10)).grid(
            row=0, column=0, sticky=W, pady=5
        )
        self.index_target_var = ttk.StringVar()
        ttk.Entry(input_frame, textvariable=self.index_target_var, width=50).grid(
            row=0, column=1, padx=5, pady=5, sticky=EW
        )
        ttk.Button(
            input_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.index_target_var),
            bootstyle="info-outline"
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # Output file
        ttk.Label(input_frame, text="Output Index File:", font=("Arial", 10)).grid(
            row=1, column=0, sticky=W, pady=5
        )
        self.index_output_var = ttk.StringVar()
        ttk.Entry(input_frame, textvariable=self.index_output_var, width=50).grid(
            row=1, column=1, padx=5, pady=5, sticky=EW
        )
        ttk.Button(
            input_frame, 
            text="Browse...", 
            command=lambda: self.browse_save_file(self.index_output_var),
            bootstyle="info-outline"
        ).grid(row=1, column=2, padx=5, pady=5)
        
        # Log directory
        ttk.Label(input_frame, text="Log Directory:", font=("Arial", 10)).grid(
            row=2, column=0, sticky=W, pady=5
        )
        self.index_log_dir_var = ttk.StringVar()
        ttk.Entry(input_frame, textvariable=self.index_log_dir_var, width=50).grid(
            row=2, column=1, padx=5, pady=5, sticky=EW
        )
        ttk.Button(
            input_frame, 
            text="Browse...", 
            command=lambda: self.browse_folder(self.index_log_dir_var),
            bootstyle="info-outline"
        ).grid(row=2, column=2, padx=5, pady=5)
        
        input_frame.columnconfigure(1, weight=1)
        
        # Execute button
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Generate Index", 
            command=self.execute_index,
            bootstyle="success",
            width=30
        ).pack(pady=10)

        self._create_inline_log_section(frame, "Index Log (Current Tab)", "index_log_text")
        
    def setup_settings_tab(self) -> None:
        """Setup Settings tab."""
        frame = self.settings_frame
        
        # Config info
        info_frame = ttk.Labelframe(frame, text="Configuration", padding=15, bootstyle="primary")
        info_frame.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        config_text = ScrolledText(info_frame, height=15, wrap=WORD)
        config_text.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        if self.config:
            config_text.insert(END, f"Config File: {self.config_path}\n\n")
            config_text.insert(END, f"Specified Types ({len(self.config.specified_types)}):\n")
            for ext in sorted(self.config.specified_types):
                config_text.insert(END, f"  {ext}\n")
            config_text.insert(END, f"\nPlaceholder Suffix: {self.config.placeholder_suffix}\n")
            config_text.insert(END, f"Hash Algorithm: {self.config.hash_algorithm}\n")
            config_text.insert(END, f"Use 7-Zip: {self.config.use_7zip}\n")
        else:
            config_text.insert(END, "Configuration not loaded!")
            
        config_text.config(state=DISABLED)
        
        # Reload button
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=X, padx=10, pady=10)
        
        ttk.Button(
            btn_frame, 
            text="Reload Configuration", 
            command=self.reload_config,
            bootstyle="info",
            width=25
        ).pack(side=LEFT, padx=5)
        
        ttk.Button(
            btn_frame, 
            text="Open Config File", 
            command=self.open_config_file,
            bootstyle="secondary",
            width=25
        ).pack(side=LEFT, padx=5)
        
    def update_validate_inputs(self) -> None:
        """Update validation inputs based on selected mode."""
        # Clear existing widgets
        for widget in self.validate_input_frame.winfo_children():
            widget.destroy()
        self.validate_widgets.clear()
        
        mode = self.validate_mode_var.get()
        
        if mode in ('class1', 'class2'):
            # Target and Role
            ttk.Label(self.validate_input_frame, text="Target Folder:", font=("Arial", 10)).grid(
                row=0, column=0, sticky=W, pady=5
            )
            var = ttk.StringVar()
            self.validate_widgets['target'] = var
            ttk.Entry(self.validate_input_frame, textvariable=var, width=45).grid(
                row=0, column=1, padx=5, pady=5, sticky=EW
            )
            ttk.Button(
                self.validate_input_frame, 
                text="Browse...", 
                command=lambda: self.browse_folder(var),
                bootstyle="info-outline"
            ).grid(row=0, column=2, padx=5, pady=5)
            
            ttk.Label(self.validate_input_frame, text="Role:", font=("Arial", 10)).grid(
                row=1, column=0, sticky=W, pady=5
            )
            role_var = ttk.StringVar(value="complete")
            self.validate_widgets['role'] = role_var
            role_combo = ttk.Combobox(
                self.validate_input_frame, 
                textvariable=role_var, 
                values=["complete", "doc", "res"],
                state="readonly",
                width=20
            )
            role_combo.grid(row=1, column=1, padx=5, pady=5, sticky=W)
            
        elif mode == 'mutual':
            # Doc and Res folders
            ttk.Label(self.validate_input_frame, text="Doc Folder:", font=("Arial", 10)).grid(
                row=0, column=0, sticky=W, pady=5
            )
            doc_var = ttk.StringVar()
            self.validate_widgets['doc'] = doc_var
            ttk.Entry(self.validate_input_frame, textvariable=doc_var, width=45).grid(
                row=0, column=1, padx=5, pady=5, sticky=EW
            )
            ttk.Button(
                self.validate_input_frame, 
                text="Browse...", 
                command=lambda: self.browse_folder(doc_var),
                bootstyle="info-outline"
            ).grid(row=0, column=2, padx=5, pady=5)
            
            ttk.Label(self.validate_input_frame, text="Res Folder:", font=("Arial", 10)).grid(
                row=1, column=0, sticky=W, pady=5
            )
            res_var = ttk.StringVar()
            self.validate_widgets['res'] = res_var
            ttk.Entry(self.validate_input_frame, textvariable=res_var, width=45).grid(
                row=1, column=1, padx=5, pady=5, sticky=EW
            )
            ttk.Button(
                self.validate_input_frame, 
                text="Browse...", 
                command=lambda: self.browse_folder(res_var),
                bootstyle="info-outline"
            ).grid(row=1, column=2, padx=5, pady=5)
            
        elif mode == 'compare':
            # Old and New folders
            ttk.Label(self.validate_input_frame, text="Old Folder:", font=("Arial", 10)).grid(
                row=0, column=0, sticky=W, pady=5
            )
            old_var = ttk.StringVar()
            self.validate_widgets['old'] = old_var
            ttk.Entry(self.validate_input_frame, textvariable=old_var, width=45).grid(
                row=0, column=1, padx=5, pady=5, sticky=EW
            )
            ttk.Button(
                self.validate_input_frame, 
                text="Browse...", 
                command=lambda: self.browse_folder(old_var),
                bootstyle="info-outline"
            ).grid(row=0, column=2, padx=5, pady=5)
            
            ttk.Label(self.validate_input_frame, text="New Folder:", font=("Arial", 10)).grid(
                row=1, column=0, sticky=W, pady=5
            )
            new_var = ttk.StringVar()
            self.validate_widgets['new'] = new_var
            ttk.Entry(self.validate_input_frame, textvariable=new_var, width=45).grid(
                row=1, column=1, padx=5, pady=5, sticky=EW
            )
            ttk.Button(
                self.validate_input_frame, 
                text="Browse...", 
                command=lambda: self.browse_folder(new_var),
                bootstyle="info-outline"
            ).grid(row=1, column=2, padx=5, pady=5)
            
        self.validate_input_frame.columnconfigure(1, weight=1)
        
    def browse_folder(self, var: ttk.StringVar) -> None:
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(title="Select Folder")
        if folder:
            var.set(folder)
            
    def browse_save_file(self, var: ttk.StringVar) -> None:
        """Open save file dialog."""
        file = filedialog.asksaveasfilename(
            title="Save Index File",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if file:
            var.set(file)

    def _create_inline_log_section(
        self,
        frame: ttk.Frame,
        title: str,
        widget_attr: str,
        height: int = 8,
    ) -> None:
        panel = ttk.Labelframe(frame, text=title, padding=8, bootstyle="info")
        panel.pack(fill=BOTH, expand=YES, padx=10, pady=(0, 10))

        activity_row = ttk.Frame(panel)
        activity_row.pack(fill=X, padx=2, pady=(0, 4))
        ttk.Label(activity_row, text="Activity:", font=("Arial", 9, "bold")).pack(side=LEFT)
        ttk.Label(activity_row, textvariable=self.activity_var, bootstyle="secondary").pack(
            side=LEFT, padx=(6, 0)
        )

        text_widget = ScrolledText(panel, height=height, wrap=WORD, state=NORMAL)
        text_widget.pack(fill=BOTH, expand=YES)
        setattr(self, widget_attr, text_widget)

    def _clear_text_widget(self, widget: Any) -> None:
        if widget is None:
            return
        try:
            widget.delete("1.0", END)
        except Exception:
            pass

    def _build_log_capture(self, tab_widget: Any = None) -> Any:
        global_capture = LogCapture(
            self.log_text,
            progress_callback=self.update_progress,
            status_callback=self.set_status,
            line_callback=self._note_log_line,
        )
        if tab_widget is None:
            return global_capture
        tab_capture = LogCapture(
            tab_widget,
            progress_callback=None,
            status_callback=None,
            line_callback=self._note_log_line,
        )
        return MultiLogCapture(global_capture, tab_capture)

    def _note_log_line(self) -> None:
        self._last_log_update_ts = time.monotonic()

    def _active_inline_log_widget(self) -> Any:
        op_name = self._current_operation_name
        if op_name.startswith('validate_'):
            return getattr(self, 'validate_log_text', None)
        if op_name == 'split':
            return getattr(self, 'split_log_text', None)
        if op_name == 'merge':
            return getattr(self, 'merge_log_text', None)
        if op_name == 'repair':
            return getattr(self, 'repair_log_text', None)
        if op_name == 'index':
            return getattr(self, 'index_log_text', None)
        return None

    def _append_to_log_widget(self, widget: Any, message: str) -> None:
        if widget is None:
            return
        try:
            widget.insert(END, message + "\n")
            widget.see(END)
            widget.update_idletasks()
        except Exception:
            pass

    def _confirm_from_worker(self, message: str) -> bool:
        if threading.current_thread() is threading.main_thread():
            return messagebox.askyesno('Confirm', message)

        decision = {'value': False}
        done = threading.Event()

        def _ask() -> None:
            try:
                decision['value'] = messagebox.askyesno('Confirm', message)
            except Exception:
                decision['value'] = False
            finally:
                done.set()

        try:
            self.root.after(0, _ask)
        except Exception:
            return False

        while not done.wait(0.05):
            continue
        return bool(decision['value'])

    def _emit_runtime_heartbeat(self) -> None:
        if not self.operation_running:
            return
        now = time.monotonic()
        if (now - self._last_log_update_ts) < 6.0:
            return
        if (now - self._last_heartbeat_emit_ts) < 6.0:
            return
        op_name = self._current_operation_name or 'operation'
        elapsed = 0
        if self._operation_started_at is not None:
            elapsed = max(0, int(now - self._operation_started_at))
        message = f"[INFO] {op_name} running... elapsed={elapsed // 60:02d}:{elapsed % 60:02d}"
        self.log_message(message)
        inline_widget = self._active_inline_log_widget()
        if inline_widget is not None and inline_widget is not self.log_text:
            self._append_to_log_widget(inline_widget, message)
        self._last_heartbeat_emit_ts = now
        self._last_log_update_ts = now

    def clear_log(self) -> None:
        """Clear log text area."""
        self._clear_text_widget(self.log_text)

    def clear_validate_log(self) -> None:
        """Clear validation tab inline log area."""
        self._clear_text_widget(getattr(self, 'validate_log_text', None))
        
    def log_message(self, message: str) -> None:
        """Add message to log."""
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)
        self.log_text.update_idletasks()
        self._last_log_update_ts = time.monotonic()
        
    def update_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        if total > 0:
            if current <= 0:
                # Keep the indeterminate animation until there is real progress.
                if not self._progress_indeterminate:
                    self.progress_var.set(0)
                return
            percentage = int((current / total) * 100)
            self.progress_var.set(percentage)
            self.set_status(f"{current}/{total} ({percentage}%)")
            
    def set_status(self, message: str) -> None:
        """Set status label text."""
        self._status_base_text = message
        self._render_status()

    def _render_status(self) -> None:
        if self.operation_running:
            frame = self._spinner_frames[self._spinner_index % len(self._spinner_frames)]
            elapsed = 0
            if self._operation_started_at is not None:
                elapsed = max(0, int(time.monotonic() - self._operation_started_at))
            elapsed_text = f"{elapsed // 60:02d}:{elapsed % 60:02d}"
            self.status_label.config(text=f"{self._status_base_text} {frame} [{elapsed_text}]")
            op_name = self._current_operation_name or 'running'
            self.activity_var.set(f"{op_name} {frame}  elapsed={elapsed_text}")
        else:
            self.status_label.config(text=self._status_base_text)
            self.activity_var.set("Idle")

    def _start_status_spinner(self) -> None:
        self._stop_status_spinner()
        self._operation_started_at = time.monotonic()
        self._spinner_index = 0
        self._tick_status_spinner()

    def _tick_status_spinner(self) -> None:
        if not self.operation_running:
            self._spinner_after_id = None
            return
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
        self._render_status()
        self._emit_runtime_heartbeat()
        self._spinner_after_id = self.root.after(250, self._tick_status_spinner)

    def _stop_status_spinner(self) -> None:
        if self._spinner_after_id is not None:
            try:
                self.root.after_cancel(self._spinner_after_id)
            except Exception:
                pass
            self._spinner_after_id = None
        self._operation_started_at = None
        self._render_status()

    def _set_progress_indeterminate(self, active: bool) -> None:
        if active:
            if self._progress_indeterminate:
                return
            self.progress_bar.config(mode='indeterminate')
            self.progress_bar.start(10)
            self._progress_indeterminate = True
            return
        if not self._progress_indeterminate:
            self.progress_bar.config(mode='determinate')
            return
        try:
            self.progress_bar.stop()
        except Exception:
            pass
        self.progress_bar.config(mode='determinate')
        self._progress_indeterminate = False

    def _reset_runtime_feedback_clock(self) -> None:
        now = time.monotonic()
        self._last_log_update_ts = now
        self._last_heartbeat_emit_ts = 0.0
        
    def execute_split(self) -> None:
        """Execute split operation."""
        if self.operation_running:
            messagebox.showwarning("Operation Running", "Another operation is already running!")
            return
            
        source = self.split_source_var.get()
        output = self.split_output_var.get()
        
        if not source or not output:
            messagebox.showerror("Input Error", "Please specify source and output folders!")
            return
            
        if not self.config:
            messagebox.showerror("Config Error", "Configuration not loaded!")
            return
            
        self.clear_log()
        self._clear_text_widget(getattr(self, 'split_log_text', None))
        self._pending_validate_context = None
        self._pending_merge_context = None
        self._pending_split_context = None
        self._set_progress_indeterminate(False)
        self.progress_var.set(0)
        self.set_status("Running split operation...")
        self.operation_running = True
        self._current_operation_name = 'split'
        self._reset_runtime_feedback_clock()
        self._pending_split_context = {
            'source': Path(source),
            'log_dir_root': Path(output) / 'logs',
        }
        self._start_status_spinner()
        self._set_progress_indeterminate(True)
        
        log_capture = self._build_log_capture(getattr(self, 'split_log_text', None))
        
        # Start operation in thread
        thread = OperationThread(
            split_operation,
            self.result_queue,
            log_capture,
            Path(source),
            Path(output),
            self.config,
            self.split_force_var.get(),
            self.split_auto_yes_var.get(),
            confirm_callback=self._confirm_from_worker,
        )
        thread.start()
        
        self.log_message(f"[INFO] Starting split operation: {source} -> {output}")
        
    def execute_merge(self) -> None:
        """Execute merge operation."""
        if self.operation_running:
            messagebox.showwarning("Operation Running", "Another operation is already running!")
            return
            
        doc = self.merge_doc_var.get()
        res = self.merge_res_var.get()
        output = self.merge_output_var.get()
        
        if not doc or not res or not output:
            messagebox.showerror("Input Error", "Please specify doc, res, and output folders!")
            return
            
        if not self.config:
            messagebox.showerror("Config Error", "Configuration not loaded!")
            return
            
        self.clear_log()
        self._clear_text_widget(getattr(self, 'merge_log_text', None))
        self._pending_validate_context = None
        self._pending_merge_context = None
        self._pending_split_context = None
        self._set_progress_indeterminate(False)
        self.progress_var.set(0)
        self.set_status("Running merge operation...")
        self.operation_running = True
        self._current_operation_name = 'merge'
        self._reset_runtime_feedback_clock()
        self._pending_merge_context = {
            'doc': Path(doc),
            'res': Path(res),
            'log_dir_root': Path(output) / 'logs',
        }
        self._start_status_spinner()
        self._set_progress_indeterminate(True)
        
        log_capture = self._build_log_capture(getattr(self, 'merge_log_text', None))
        
        # Start operation in thread
        thread = OperationThread(
            merge_operation,
            self.result_queue,
            log_capture,
            Path(doc),
            Path(res),
            Path(output),
            self.config,
            self.merge_force_var.get(),
            self.merge_auto_yes_var.get(),
            confirm_callback=self._confirm_from_worker,
        )
        thread.start()
        
        self.log_message(f"[INFO] Starting merge operation: {doc} + {res} -> {output}")
        
    def execute_validate(self) -> None:
        """Execute validation operation."""
        if self.operation_running:
            messagebox.showwarning("Operation Running", "Another operation is already running!")
            return
            
        mode = self.validate_mode_var.get()
        log_dir = self.validate_log_dir_var.get()
        
        if not log_dir:
            messagebox.showerror("Input Error", "Please specify log directory!")
            return
            
        if not self.config:
            messagebox.showerror("Config Error", "Configuration not loaded!")
            return
            
        log_dir_path = Path(log_dir) / now_timestamp()
        
        self.clear_log()
        self.clear_validate_log()
        self._pending_validate_context = None
        self._pending_merge_context = None
        self._pending_split_context = None
        self._set_progress_indeterminate(False)
        self.progress_var.set(0)
        self.set_status(f"Running {mode} validation...")
        self.operation_running = True
        self._current_operation_name = f'validate_{mode}'
        self._reset_runtime_feedback_clock()
        self._pending_validate_context = {
            'mode': mode,
            'log_dir': log_dir_path,
        }
        self._start_status_spinner()
        self._set_progress_indeterminate(True)
        
        log_capture: Any = self._build_log_capture(getattr(self, 'validate_log_text', None))
        
        # Prepare arguments based on mode
        if mode in ('class1', 'class2'):
            target = self.validate_widgets.get('target')
            role = self.validate_widgets.get('role')
            if not target or not target.get():
                messagebox.showerror("Input Error", "Please specify target folder!")
                self.operation_running = False
                self._current_operation_name = ''
                self._pending_validate_context = None
                self._set_progress_indeterminate(False)
                self._stop_status_spinner()
                return
            thread = OperationThread(
                validate_operation,
                self.result_queue,
                log_capture,
                Path(target.get()),
                mode,
                self.config,
                log_dir_path,
                role.get() if role else 'complete'
            )
            self._pending_validate_context.update({
                'target': Path(target.get()),
                'role': role.get() if role else 'complete',
            })
        elif mode == 'mutual':
            doc = self.validate_widgets.get('doc')
            res = self.validate_widgets.get('res')
            if not doc or not doc.get() or not res or not res.get():
                messagebox.showerror("Input Error", "Please specify doc and res folders!")
                self.operation_running = False
                self._current_operation_name = ''
                self._pending_validate_context = None
                self._set_progress_indeterminate(False)
                self._stop_status_spinner()
                return
            thread = OperationThread(
                validate_mutual_operation,
                self.result_queue,
                log_capture,
                Path(doc.get()),
                Path(res.get()),
                self.config,
                log_dir_path,
                True,
                confirm_callback=self._confirm_from_worker,
            )
            self._pending_validate_context.update({
                'doc': Path(doc.get()),
                'res': Path(res.get()),
            })
        elif mode == 'compare':
            old = self.validate_widgets.get('old')
            new = self.validate_widgets.get('new')
            if not old or not old.get() or not new or not new.get():
                messagebox.showerror("Input Error", "Please specify old and new folders!")
                self.operation_running = False
                self._current_operation_name = ''
                self._pending_validate_context = None
                self._set_progress_indeterminate(False)
                self._stop_status_spinner()
                return
            thread = OperationThread(
                analyze_compare_operation,
                self.result_queue,
                log_capture,
                Path(old.get()),
                Path(new.get()),
                self.config,
                log_dir_path
            )
            self._pending_validate_context.update({
                'old': Path(old.get()),
                'new': Path(new.get()),
            })
        else:
            messagebox.showerror("Error", f"Unknown validation mode: {mode}")
            self.operation_running = False
            self._current_operation_name = ''
            self._pending_validate_context = None
            self._set_progress_indeterminate(False)
            self._stop_status_spinner()
            return
            
        thread.start()
        self.log_message(f"[INFO] Starting {mode} validation")
        if mode == 'compare':
            self.log_message("[INFO] Compare analysis started: indexing both folders...")
        
    def execute_index(self) -> None:
        """Execute index operation."""
        if self.operation_running:
            messagebox.showwarning("Operation Running", "Another operation is already running!")
            return
            
        target = self.index_target_var.get()
        output = self.index_output_var.get()
        log_dir = self.index_log_dir_var.get()
        
        if not target or not output or not log_dir:
            messagebox.showerror("Input Error", "Please specify target, output, and log directory!")
            return
            
        if not self.config:
            messagebox.showerror("Config Error", "Configuration not loaded!")
            return
            
        log_dir_path = Path(log_dir) / now_timestamp()
        
        self.clear_log()
        self._clear_text_widget(getattr(self, 'index_log_text', None))
        self._pending_validate_context = None
        self._pending_merge_context = None
        self._pending_split_context = None
        self._set_progress_indeterminate(False)
        self.progress_var.set(0)
        self.set_status("Generating index...")
        self.operation_running = True
        self._current_operation_name = 'index'
        self._reset_runtime_feedback_clock()
        self._start_status_spinner()
        self._set_progress_indeterminate(True)
        
        log_capture = self._build_log_capture(getattr(self, 'index_log_text', None))
        
        # Start operation in thread
        thread = OperationThread(
            index_operation,
            self.result_queue,
            log_capture,
            Path(target),
            Path(output),
            self.config,
            log_dir_path
        )
        thread.start()
        
        self.log_message(f"[INFO] Starting index generation: {target} -> {output}")

    def _prune_repair_issues_after_apply(self, payload: CompareFixResult) -> None:
        if not self.last_compare_result:
            return
        if not payload.applied_paths:
            return

        removed = set(payload.applied_paths)
        remaining = [
            issue for issue in self.last_compare_result.issues
            if not (issue.issue_type == payload.issue_type and issue.rel_path in removed)
        ]
        self.last_compare_result = CompareAnalysisResult(
            old_path=self.last_compare_result.old_path,
            new_path=self.last_compare_result.new_path,
            issues=remaining,
            log_path=self.last_compare_result.log_path,
        )
        self.load_compare_result_for_repair(
            self.last_compare_result,
            context_type=self.repair_context_type,
            summary_title=self._repair_summary_title_for_context(self.repair_context_type),
        )

    def _repair_summary_title_for_context(self, context_type: str) -> str:
        if context_type == 'doc_res':
            return 'Doc/Res repair'
        if context_type == 'complete':
            return 'Complete repair'
        if context_type == 'compare':
            return 'Compare'
        return 'Repair'

    def _extract_log_path_from_message(self, message: str) -> Path | None:
        m = re.search(r'see log:\s*(.+)$', message.strip(), flags=re.IGNORECASE)
        if not m:
            return None
        raw = m.group(1).strip().strip('"')
        if not raw:
            return None
        p = Path(raw)
        if p.exists():
            return p
        return None

    def _infer_doc_res_peer(self, target: Path, role: str) -> Path | None:
        if role not in ('doc', 'res'):
            return None
        side = role
        peer_side = 'res' if side == 'doc' else 'doc'
        parent = target.parent
        if parent.name.lower() != side:
            return None
        peer = parent.parent / peer_side / target.name
        if peer.exists():
            return peer
        return None

    def _failure_context_paths(self, op_name: str) -> tuple[Path, Path]:
        if op_name == 'split' and self._pending_split_context:
            src = self._pending_split_context.get('source')
            if isinstance(src, Path):
                return src, src
        if op_name == 'merge' and self._pending_merge_context:
            doc = self._pending_merge_context.get('doc')
            res = self._pending_merge_context.get('res')
            if isinstance(doc, Path) and isinstance(res, Path):
                return doc, res
        if op_name.startswith('validate_') and self._pending_validate_context:
            mode = str(self._pending_validate_context.get('mode') or '')
            if mode == 'mutual':
                doc = self._pending_validate_context.get('doc')
                res = self._pending_validate_context.get('res')
                if isinstance(doc, Path) and isinstance(res, Path):
                    return doc, res
            if mode == 'class2':
                target = self._pending_validate_context.get('target')
                role = str(self._pending_validate_context.get('role') or '')
                if isinstance(target, Path) and role in ('doc', 'res'):
                    peer = self._infer_doc_res_peer(target, role)
                    if peer:
                        doc = target if role == 'doc' else peer
                        res = peer if role == 'doc' else target
                        return doc, res
            target = self._pending_validate_context.get('target')
            if isinstance(target, Path):
                return target, target
        return Path('.'), Path('.')

    def _expected_repair_context_for_failure(self, op_name: str) -> str | None:
        if op_name == 'split':
            return 'complete'
        if op_name == 'merge':
            return 'doc_res'
        if op_name == 'validate_mutual':
            return 'doc_res'
        if op_name == 'validate_class1':
            role = str((self._pending_validate_context or {}).get('role') or 'complete')
            if role == 'complete':
                return 'complete'
            return None
        if op_name == 'validate_class2':
            role = str((self._pending_validate_context or {}).get('role') or '')
            if role in ('doc', 'res'):
                return 'doc_res'
            if role == 'complete':
                return 'complete'
            return None
        return None

    def _failure_summary_title(self, op_name: str) -> str:
        if op_name == 'split':
            return 'Split pre-check'
        if op_name == 'merge':
            return 'Merge pre-check'
        if op_name == 'validate_mutual':
            return 'Validate mutual'
        if op_name == 'validate_class2':
            return 'Validate class2'
        if op_name == 'validate_class1':
            return 'Validate class1'
        return 'Repair suggestions'

    def _normalize_structured_issue_rel_path(self, issue_type: str, rel_path: str) -> str:
        # validate_mutual reports orphan-placeholder items by original file path;
        # repair execution needs the actual placeholder directory path.
        if issue_type not in (DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER, DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER):
            return rel_path
        suffix = self.config.placeholder_suffix if self.config else ''
        if not suffix:
            return rel_path
        rel = Path(rel_path)
        if rel.name.endswith(suffix):
            return rel.as_posix()
        placeholder_rel = rel.parent / f'{rel.name}{suffix}'
        return placeholder_rel.as_posix()

    def _build_structured_repair_result_from_log(
        self,
        op_name: str,
        message: str,
    ) -> tuple[CompareAnalysisResult, str, str] | None:
        log_path = self._extract_log_path_from_message(message)
        if not log_path:
            return None
        try:
            lines = log_path.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            return None

        doc_res_prefixes: dict[str, str] = {
            'doc contains non-specified file: ': DOCRES_ISSUE_DOC_NON_SPECIFIED,
            'res contains specified file: ': DOCRES_ISSUE_RES_SPECIFIED,
            'doc file missing placeholder in res: ': DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
            'res file missing placeholder in doc: ': DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC,
            'doc placeholder has no file in res: ': DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER,
            'res placeholder has no file in doc: ': DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
            'doc directory missing in res: ': DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
            'res directory missing in doc: ': DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
            'repair(doc/res): doc contains non-specified file: ': DOCRES_ISSUE_DOC_NON_SPECIFIED,
            'repair(doc/res): res contains specified file: ': DOCRES_ISSUE_RES_SPECIFIED,
            'repair(doc/res): doc file missing placeholder in res: ': DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
            'repair(doc/res): res file missing placeholder in doc: ': DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC,
            'repair(doc/res): doc orphan placeholder: ': DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER,
            'repair(doc/res): res orphan placeholder: ': DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
            'repair(doc/res): doc directory missing in res: ': DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
            'repair(doc/res): res directory missing in doc: ': DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
        }
        complete_prefixes: dict[str, str] = {
            'placeholder-like name not allowed in complete folder: ': COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
            'symlink not allowed: ': COMPLETE_ISSUE_SYMLINK,
            'repair(complete): placeholder-like name in complete: ': COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
            'repair(complete): symlink not allowed: ': COMPLETE_ISSUE_SYMLINK,
        }
        compare_prefixes: dict[str, str] = {
            'compare: missing file in new: ': COMPARE_ISSUE_MISSING_IN_NEW,
            'compare: extra file in new: ': COMPARE_ISSUE_EXTRA_IN_NEW,
            'compare: content mismatch (size/hash): ': COMPARE_ISSUE_CONTENT_MISMATCH,
            'compare: mtime differs but hash same: ': COMPARE_ISSUE_MTIME_DIFF_HASH_SAME,
            'compare: missing dir in new: ': COMPARE_ISSUE_MISSING_DIR_IN_NEW,
            'compare: extra dir in new: ': COMPARE_ISSUE_EXTRA_DIR_IN_NEW,
            'compare: missing placeholder in new: ': COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW,
            'compare: extra placeholder in new: ': COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW,
        }
        all_prefixes = {**doc_res_prefixes, **complete_prefixes, **compare_prefixes}

        expected_context = self._expected_repair_context_for_failure(op_name)
        context_issue_sets = {
            'doc_res': {
                DOCRES_ISSUE_DOC_NON_SPECIFIED,
                DOCRES_ISSUE_RES_SPECIFIED,
                DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
                DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC,
                DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER,
                DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
                DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
                DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
            },
            'complete': {
                COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
                COMPLETE_ISSUE_SYMLINK,
            },
            'compare': {
                COMPARE_ISSUE_MISSING_IN_NEW,
                COMPARE_ISSUE_EXTRA_IN_NEW,
                COMPARE_ISSUE_CONTENT_MISMATCH,
                COMPARE_ISSUE_MTIME_DIFF_HASH_SAME,
                COMPARE_ISSUE_MISSING_DIR_IN_NEW,
                COMPARE_ISSUE_EXTRA_DIR_IN_NEW,
                COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW,
                COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW,
            },
        }

        issues: list[CompareIssue] = []
        seen_keys: set[tuple[str, str]] = set()
        for line in lines:
            if not (line.startswith('[ERROR]') or line.startswith('[FATAL]') or line.startswith('[WARNING]')):
                continue
            content = line.split(']', 1)[1].strip() if ']' in line else line.strip()
            lower = content.lower()
            matched_issue: str | None = None
            rel_path: str | None = None
            for prefix, issue_type in all_prefixes.items():
                if lower.startswith(prefix):
                    matched_issue = issue_type
                    rel_path = content[len(prefix):].strip()
                    break
            if not matched_issue:
                continue
            if expected_context:
                allowed = context_issue_sets.get(expected_context, set())
                if matched_issue not in allowed:
                    continue
            if not list_fix_strategies(matched_issue):
                continue
            rel = rel_path or '(unknown)'
            if rel != '(unknown)':
                rel = self._normalize_structured_issue_rel_path(matched_issue, rel)
            key = (matched_issue, rel)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            issues.append(
                CompareIssue(
                    matched_issue,
                    rel,
                    'ERROR',
                    details={},
                )
            )

        if not issues:
            return None

        old_path, new_path = self._failure_context_paths(op_name)
        context = expected_context or 'manual'
        if context == 'manual':
            issue_types = {issue.issue_type for issue in issues}
            if issue_types <= context_issue_sets['doc_res']:
                context = 'doc_res'
            elif issue_types <= context_issue_sets['complete']:
                context = 'complete'
            elif issue_types <= context_issue_sets['compare']:
                context = 'compare'
        if context == 'manual':
            return None

        result = CompareAnalysisResult(
            old_path=old_path,
            new_path=new_path,
            issues=issues,
            log_path=log_path,
        )
        return result, context, self._failure_summary_title(op_name)

    def _build_manual_repair_result_from_log(self, op_name: str, message: str) -> CompareAnalysisResult | None:
        log_path = self._extract_log_path_from_message(message)
        if not log_path:
            return None
        try:
            lines = log_path.read_text(encoding='utf-8', errors='ignore').splitlines()
        except Exception:
            return None
        issues: list[CompareIssue] = []
        for line in lines:
            if not (line.startswith('[ERROR]') or line.startswith('[FATAL]') or line.startswith('[WARNING]')):
                continue
            content = line.split(']', 1)[1].strip() if ']' in line else line
            rel_path = content
            if ': ' in content:
                rel_path = content.rsplit(': ', 1)[-1].strip()
            issues.append(
                CompareIssue(
                    MANUAL_ISSUE_TYPE,
                    rel_path or '(see log)',
                    'ERROR',
                    details={'message': content},
                )
            )
        if not issues:
            return None
        old_path, new_path = self._failure_context_paths(op_name)
        return CompareAnalysisResult(
            old_path=old_path,
            new_path=new_path,
            issues=issues,
            log_path=log_path,
        )

    def _load_repair_from_failure(self, op_name: str, message: str) -> bool:
        structured = self._build_structured_repair_result_from_log(op_name, message)
        if structured is not None:
            result, context_type, summary_title = structured
            self.load_compare_result_for_repair(
                result,
                context_type=context_type,
                summary_title=summary_title,
            )
            self.notebook.select(self.repair_frame)
            return True
        manual = self._build_manual_repair_result_from_log(op_name, message)
        if manual is not None:
            self.load_compare_result_for_repair(
                manual,
                context_type='manual',
                summary_title='Manual review',
            )
            self.notebook.select(self.repair_frame)
            return True
        return False
        
    def check_operation_results(self) -> None:
        """Check if operation thread has finished."""
        try:
            payload: Any = None
            result = self.result_queue.get_nowait()
            if isinstance(result, tuple) and len(result) == 3:
                result_type, message, payload = result
            else:
                result_type, message = result
            self.operation_running = False
            self._stop_status_spinner()
            self._set_progress_indeterminate(False)
            
            if result_type == 'success':
                self.progress_var.set(100)
                op_name = self._current_operation_name

                if op_name == 'validate_compare' and isinstance(payload, CompareAnalysisResult):
                    self.load_compare_result_for_repair(payload)
                    blockers = payload.has_blockers()
                    issue_total = len(payload.issues)
                    if blockers:
                        self.set_status("Compare finished with issues.")
                        self.log_message(
                            f"\n[WARNING] Compare found {issue_total} issue(s). "
                            "Switched to Repair tab for batch fix."
                        )
                        self.notebook.select(self.repair_frame)
                        messagebox.showwarning(
                            "Compare Completed",
                            f"Found {issue_total} issue(s).\n"
                            "Switched to Repair tab. Select issue type and strategy to batch-fix.",
                        )
                    else:
                        self.set_status("Compare passed with no blockers.")
                        self.log_message("\n[SUCCESS] Compare found no blocking issues.")
                        messagebox.showinfo("Success", "Compare completed with no blocking issues.")
                elif op_name == 'repair' and isinstance(payload, CompareFixResult):
                    self._prune_repair_issues_after_apply(payload)
                    self.set_status("Repair completed.")
                    self.log_message(
                        f"\n[SUCCESS] Repair done: applied={payload.applied}, "
                        f"skipped={payload.skipped}, failed={payload.failed}"
                    )
                    messagebox.showinfo(
                        "Repair Completed",
                        f"Applied: {payload.applied}\n"
                        f"Skipped: {payload.skipped}\n"
                        f"Failed: {payload.failed}\n\n"
                        "Applied items are removed from current repair list immediately.",
                    )
                else:
                    self.set_status("Completed successfully!")
                    self.log_message(f"\n[SUCCESS] {message}")
                    messagebox.showinfo("Success", message)
            elif result_type == 'fatal':
                self.set_status("Failed!")
                self.log_message(f"\n[FATAL] {message}")
                suggested = self._load_repair_from_failure(self._current_operation_name, message)
                if suggested:
                    self.log_message(
                        "[INFO] Generated repair suggestions and switched to Repair tab."
                    )
                    messagebox.showwarning(
                        "Operation Failed",
                        f"{message}\n\n已自动生成可修复问题并跳转到 Repair 标签页。",
                    )
                else:
                    messagebox.showerror("Fatal Error", message)
            else:  # error
                self.set_status("Error occurred!")
                self.log_message(f"\n[ERROR] {message}")
                messagebox.showerror("Error", message)
            self._current_operation_name = ''
            self._pending_validate_context = None
            self._pending_merge_context = None
            self._pending_split_context = None
        except queue.Empty:
            pass
            
        # Schedule next check
        self.root.after(100, self.check_operation_results)
        
    def reload_config(self) -> None:
        """Reload configuration file."""
        self.load_config()
        messagebox.showinfo("Config Reloaded", "Configuration reloaded successfully!")
        # Refresh settings tab
        self.setup_settings_tab()
        
    def open_config_file(self) -> None:
        """Open config file in default editor."""
        import subprocess
        import sys
        
        try:
            if sys.platform == 'win32':
                subprocess.run(['notepad', str(self.config_path)])
            else:
                subprocess.run(['xdg-open', str(self.config_path)])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open config file: {e}")


def launch_gui() -> None:
    """Launch the GUI application."""
    root = ttk.Window(themename="cosmo")  # Modern theme
    app = KBFolderManagerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    launch_gui()
