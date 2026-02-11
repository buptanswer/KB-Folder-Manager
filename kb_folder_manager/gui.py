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
    compare_operation,
    index_operation,
    merge_operation,
    split_operation,
    validate_mutual_operation,
    validate_operation,
)
from .utils import FatalError, now_timestamp


class LogCapture:
    """Captures log output for display in GUI."""

    _PROGRESS_RE = re.compile(
        r'progress(?:\s*\([^)]+\))?:\s*(?:files=)?(\d+)\s*/\s*(\d+)',
        re.IGNORECASE,
    )
    _COMPARE_PATH_PATTERNS = (
        'compare: missing file in new: ',
        'compare: extra file in new: ',
        'compare: size mismatch: ',
        'compare: hash mismatch: ',
        'compare: mtime differs but hash same: ',
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
    ):
        self.text_widget = text_widget
        self.progress_callback = progress_callback
        self.status_callback = status_callback
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
        else:
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
            self.progress_callback(current, total)

        if not self.status_callback:
            return

        lower = line.lower()
        marker = '| current:'
        if marker in lower:
            idx = lower.find(marker)
            current_file = line[idx + len(marker):].strip()
            if len(current_file) > 60:
                current_file = '...' + current_file[-57:]
            self.status_callback(f"Processing [{current}/{total}]: {current_file}")
        else:
            percent = int((current / total) * 100)
            self.status_callback(f"Processing [{current}/{total}] ({percent}%)")

    def _update_stage_status(self, lower: str) -> None:
        if not self.status_callback:
            return
        if 'started' in lower:
            self.status_callback("Operation started...")
        elif 'building' in lower and 'index' in lower:
            self.status_callback("Building index...")
        elif 'validation' in lower or 'validating' in lower:
            self.status_callback("Validating...")
        elif 'writing' in lower and 'index' in lower:
            self.status_callback("Writing indexes...")



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
            
            self.operation(*self.args, **self.kwargs)
            self.result_queue.put(('success', 'Operation completed successfully!'))
        except FatalError as e:
            self.result_queue.put(('fatal', str(e)))
        except Exception as e:
            self.result_queue.put(('error', str(e)))
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
        self.root.geometry("900x700")
        
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
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # Create tabs
        self.split_frame = ttk.Frame(self.notebook)
        self.merge_frame = ttk.Frame(self.notebook)
        self.validate_frame = ttk.Frame(self.notebook)
        self.index_frame = ttk.Frame(self.notebook)
        self.settings_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.split_frame, text="Split")
        self.notebook.add(self.merge_frame, text="Merge")
        self.notebook.add(self.validate_frame, text="Validate")
        self.notebook.add(self.index_frame, text="Index")
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Setup each tab
        self.setup_split_tab()
        self.setup_merge_tab()
        self.setup_validate_tab()
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
            
    def clear_log(self) -> None:
        """Clear log text area."""
        self.log_text.delete("1.0", END)
        
    def log_message(self, message: str) -> None:
        """Add message to log."""
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)
        self.log_text.update_idletasks()
        
    def update_progress(self, current: int, total: int) -> None:
        """Update progress bar."""
        if total > 0:
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
            self.status_label.config(text=f"{self._status_base_text} {frame}")
        else:
            self.status_label.config(text=self._status_base_text)

    def _start_status_spinner(self) -> None:
        self._stop_status_spinner()
        self._spinner_index = 0
        self._tick_status_spinner()

    def _tick_status_spinner(self) -> None:
        if not self.operation_running:
            self._spinner_after_id = None
            return
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
        self._render_status()
        self._spinner_after_id = self.root.after(250, self._tick_status_spinner)

    def _stop_status_spinner(self) -> None:
        if self._spinner_after_id is not None:
            try:
                self.root.after_cancel(self._spinner_after_id)
            except Exception:
                pass
            self._spinner_after_id = None
        self._render_status()
        
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
        self.progress_var.set(0)
        self.set_status("Running split operation...")
        self.operation_running = True
        self._start_status_spinner()
        
        # Create log capture with progress and status callbacks
        log_capture = LogCapture(
            self.log_text,
            progress_callback=self.update_progress,
            status_callback=self.set_status
        )
        
        # Start operation in thread
        thread = OperationThread(
            split_operation,
            self.result_queue,
            log_capture,
            Path(source),
            Path(output),
            self.config,
            self.split_force_var.get(),
            self.split_auto_yes_var.get()
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
        self.progress_var.set(0)
        self.set_status("Running merge operation...")
        self.operation_running = True
        self._start_status_spinner()
        
        # Create log capture with progress and status callbacks
        log_capture = LogCapture(
            self.log_text,
            progress_callback=self.update_progress,
            status_callback=self.set_status
        )
        
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
            self.merge_auto_yes_var.get()
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
        self.progress_var.set(0)
        self.set_status(f"Running {mode} validation...")
        self.operation_running = True
        self._start_status_spinner()
        
        # Create log capture with progress and status callbacks
        log_capture = LogCapture(
            self.log_text,
            progress_callback=self.update_progress,
            status_callback=self.set_status
        )
        
        # Prepare arguments based on mode
        if mode in ('class1', 'class2'):
            target = self.validate_widgets.get('target')
            role = self.validate_widgets.get('role')
            if not target or not target.get():
                messagebox.showerror("Input Error", "Please specify target folder!")
                self.operation_running = False
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
        elif mode == 'mutual':
            doc = self.validate_widgets.get('doc')
            res = self.validate_widgets.get('res')
            if not doc or not doc.get() or not res or not res.get():
                messagebox.showerror("Input Error", "Please specify doc and res folders!")
                self.operation_running = False
                self._stop_status_spinner()
                return
            thread = OperationThread(
                validate_mutual_operation,
                self.result_queue,
                log_capture,
                Path(doc.get()),
                Path(res.get()),
                self.config,
                log_dir_path
            )
        elif mode == 'compare':
            old = self.validate_widgets.get('old')
            new = self.validate_widgets.get('new')
            if not old or not old.get() or not new or not new.get():
                messagebox.showerror("Input Error", "Please specify old and new folders!")
                self.operation_running = False
                self._stop_status_spinner()
                return
            thread = OperationThread(
                compare_operation,
                self.result_queue,
                log_capture,
                Path(old.get()),
                Path(new.get()),
                self.config,
                log_dir_path
            )
        else:
            messagebox.showerror("Error", f"Unknown validation mode: {mode}")
            self.operation_running = False
            self._stop_status_spinner()
            return
            
        thread.start()
        self.log_message(f"[INFO] Starting {mode} validation")
        
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
        self.progress_var.set(0)
        self.set_status("Generating index...")
        self.operation_running = True
        self._start_status_spinner()
        
        # Create log capture with progress and status callbacks
        log_capture = LogCapture(
            self.log_text,
            progress_callback=self.update_progress,
            status_callback=self.set_status
        )
        
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
        
    def check_operation_results(self) -> None:
        """Check if operation thread has finished."""
        try:
            result_type, message = self.result_queue.get_nowait()
            self.operation_running = False
            self._stop_status_spinner()
            
            if result_type == 'success':
                self.progress_var.set(100)
                self.set_status("Completed successfully!")
                self.log_message(f"\n[SUCCESS] {message}")
                messagebox.showinfo("Success", message)
            elif result_type == 'fatal':
                self.set_status("Failed!")
                self.log_message(f"\n[FATAL] {message}")
                messagebox.showerror("Fatal Error", message)
            else:  # error
                self.set_status("Error occurred!")
                self.log_message(f"\n[ERROR] {message}")
                messagebox.showerror("Error", message)
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
