from __future__ import annotations

import os
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, as_completed, wait
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .config import Config
from .indexer import build_index, write_index
from .utils import (
    FatalError,
    Logger,
    abort_if_blockers,
    copy_file,
    ensure_dir,
    file_mtime,
    is_symlink,
    is_specified_type,
    iter_walk,
    now_timestamp,
    prompt_confirm,
    resolve_worker_count,
    safe_scandir,
    to_extended_path,
    write_summary,
)
from .validator import (
    COMPARE_FIXABLE_ISSUE_TYPES,
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
    _placeholder_original_path,
    collect_compare_issues,
    emit_compare_issue_logs,
    group_compare_issues_by_type,
    index_for_validation,
    validate_class1,
    validate_class2,
    validate_mutual,
)

COMPARE_STRATEGY_COPY_OLD_TO_NEW = 'copy_old_to_new'
COMPARE_STRATEGY_COPY_NEW_TO_OLD = 'copy_new_to_old'
COMPARE_STRATEGY_SYNC_NEW_MTIME_FROM_OLD = 'sync_new_mtime_from_old'
COMPARE_STRATEGY_SYNC_OLD_MTIME_FROM_NEW = 'sync_old_mtime_from_new'
COMPARE_STRATEGY_DELETE_OLD_FILE = 'delete_old_file'
COMPARE_STRATEGY_DELETE_NEW_FILE = 'delete_new_file'
COMPARE_STRATEGY_CREATE_DIR_IN_OLD = 'create_dir_in_old'
COMPARE_STRATEGY_CREATE_DIR_IN_NEW = 'create_dir_in_new'
COMPARE_STRATEGY_DELETE_OLD_DIR = 'delete_old_dir'
COMPARE_STRATEGY_DELETE_NEW_DIR = 'delete_new_dir'

DOCRES_ISSUE_DOC_NON_SPECIFIED = 'doc_contains_non_specified_file'
DOCRES_ISSUE_RES_SPECIFIED = 'res_contains_specified_file'
DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES = 'doc_file_missing_placeholder_in_res'
DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC = 'res_file_missing_placeholder_in_doc'
DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER = 'doc_orphan_placeholder_no_res_file'
DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER = 'res_orphan_placeholder_no_doc_file'
DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES = 'doc_dir_missing_in_res'
DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC = 'res_dir_missing_in_doc'

COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME = 'complete_placeholder_like_name'
COMPLETE_ISSUE_SYMLINK = 'complete_symlink'

REPAIR_STRATEGY_MOVE_DOC_FILE_TO_RES = 'move_doc_file_to_res'
REPAIR_STRATEGY_MOVE_RES_FILE_TO_DOC = 'move_res_file_to_doc'
REPAIR_STRATEGY_CREATE_RES_PLACEHOLDER = 'create_res_placeholder'
REPAIR_STRATEGY_CREATE_DOC_PLACEHOLDER = 'create_doc_placeholder'
REPAIR_STRATEGY_DELETE_DOC_FILE = 'delete_doc_file'
REPAIR_STRATEGY_DELETE_RES_FILE = 'delete_res_file'
REPAIR_STRATEGY_DELETE_DOC_PLACEHOLDER = 'delete_doc_placeholder'
REPAIR_STRATEGY_DELETE_RES_PLACEHOLDER = 'delete_res_placeholder'
REPAIR_STRATEGY_RENAME_REMOVE_PLACEHOLDER_SUFFIX = 'rename_remove_placeholder_suffix'
REPAIR_STRATEGY_DELETE_SYMLINK = 'delete_symlink'

COMPARE_FIX_STRATEGIES: dict[str, list[str]] = {
    COMPARE_ISSUE_CONTENT_MISMATCH: [
        COMPARE_STRATEGY_COPY_OLD_TO_NEW,
        COMPARE_STRATEGY_COPY_NEW_TO_OLD,
    ],
    COMPARE_ISSUE_MTIME_DIFF_HASH_SAME: [
        COMPARE_STRATEGY_SYNC_NEW_MTIME_FROM_OLD,
        COMPARE_STRATEGY_SYNC_OLD_MTIME_FROM_NEW,
    ],
    COMPARE_ISSUE_SIZE_MISMATCH: [
        COMPARE_STRATEGY_COPY_OLD_TO_NEW,
        COMPARE_STRATEGY_COPY_NEW_TO_OLD,
    ],
    COMPARE_ISSUE_HASH_MISMATCH: [
        COMPARE_STRATEGY_COPY_OLD_TO_NEW,
        COMPARE_STRATEGY_COPY_NEW_TO_OLD,
    ],
    COMPARE_ISSUE_MISSING_IN_NEW: [
        COMPARE_STRATEGY_COPY_OLD_TO_NEW,
        COMPARE_STRATEGY_DELETE_OLD_FILE,
    ],
    COMPARE_ISSUE_EXTRA_IN_NEW: [
        COMPARE_STRATEGY_COPY_NEW_TO_OLD,
        COMPARE_STRATEGY_DELETE_NEW_FILE,
    ],
    COMPARE_ISSUE_MISSING_DIR_IN_NEW: [
        COMPARE_STRATEGY_CREATE_DIR_IN_NEW,
        COMPARE_STRATEGY_DELETE_OLD_DIR,
    ],
    COMPARE_ISSUE_EXTRA_DIR_IN_NEW: [
        COMPARE_STRATEGY_CREATE_DIR_IN_OLD,
        COMPARE_STRATEGY_DELETE_NEW_DIR,
    ],
    COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW: [
        COMPARE_STRATEGY_CREATE_DIR_IN_NEW,
        COMPARE_STRATEGY_DELETE_OLD_DIR,
    ],
    COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW: [
        COMPARE_STRATEGY_CREATE_DIR_IN_OLD,
        COMPARE_STRATEGY_DELETE_NEW_DIR,
    ],
}

NON_COMPARE_FIX_STRATEGIES: dict[str, list[str]] = {
    DOCRES_ISSUE_DOC_NON_SPECIFIED: [
        REPAIR_STRATEGY_MOVE_DOC_FILE_TO_RES,
        REPAIR_STRATEGY_DELETE_DOC_FILE,
    ],
    DOCRES_ISSUE_RES_SPECIFIED: [
        REPAIR_STRATEGY_MOVE_RES_FILE_TO_DOC,
        REPAIR_STRATEGY_DELETE_RES_FILE,
    ],
    DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES: [
        REPAIR_STRATEGY_CREATE_RES_PLACEHOLDER,
        REPAIR_STRATEGY_DELETE_DOC_FILE,
    ],
    DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC: [
        REPAIR_STRATEGY_CREATE_DOC_PLACEHOLDER,
        REPAIR_STRATEGY_DELETE_RES_FILE,
    ],
    DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER: [
        REPAIR_STRATEGY_DELETE_DOC_PLACEHOLDER,
    ],
    DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER: [
        REPAIR_STRATEGY_DELETE_RES_PLACEHOLDER,
    ],
    DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES: [
        COMPARE_STRATEGY_CREATE_DIR_IN_NEW,
        COMPARE_STRATEGY_DELETE_OLD_DIR,
    ],
    DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC: [
        COMPARE_STRATEGY_CREATE_DIR_IN_OLD,
        COMPARE_STRATEGY_DELETE_NEW_DIR,
    ],
    COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME: [
        REPAIR_STRATEGY_RENAME_REMOVE_PLACEHOLDER_SUFFIX,
    ],
    COMPLETE_ISSUE_SYMLINK: [
        REPAIR_STRATEGY_DELETE_SYMLINK,
    ],
}

DOCRES_FIXABLE_ISSUE_TYPES = {
    DOCRES_ISSUE_DOC_NON_SPECIFIED,
    DOCRES_ISSUE_RES_SPECIFIED,
    DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
    DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC,
    DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER,
    DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
    DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
    DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
}

COMPLETE_FIXABLE_ISSUE_TYPES = {
    COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
    COMPLETE_ISSUE_SYMLINK,
}

ALL_FIX_STRATEGIES: dict[str, list[str]] = {
    **COMPARE_FIX_STRATEGIES,
    **NON_COMPARE_FIX_STRATEGIES,
}

ALL_FIXABLE_ISSUE_TYPES = set(ALL_FIX_STRATEGIES.keys()) | set(COMPARE_FIXABLE_ISSUE_TYPES)


@dataclass(frozen=True)
class CompareAnalysisResult:
    old_path: Path
    new_path: Path
    issues: list[CompareIssue]
    log_path: Path

    def issue_counts(self) -> dict[str, int]:
        grouped = group_compare_issues_by_type(self.issues)
        return {k: len(v) for k, v in grouped.items()}

    def has_blockers(self) -> bool:
        return any(issue.severity in ('ERROR', 'FATAL') for issue in self.issues)


@dataclass(frozen=True)
class CompareFixResult:
    issue_type: str
    strategy: str
    requested: int
    applied: int
    skipped: int
    failed: int
    applied_paths: tuple[str, ...]
    failed_paths: tuple[str, ...]
    log_path: Path


def list_compare_fix_strategies(issue_type: str) -> list[str]:
    return list(ALL_FIX_STRATEGIES.get(issue_type, []))


def list_fix_strategies(issue_type: str) -> list[str]:
    return list(ALL_FIX_STRATEGIES.get(issue_type, []))


def _check_output_root(output_root: Path, force: bool) -> tuple[bool, str | None]:
    if output_root.exists():
        with safe_scandir(output_root) as it:
            if any(True for _ in it):
                if not force:
                    return False, f'output root not empty: {output_root}'
                return True, f'output root not empty but continuing due to --force: {output_root}'
    else:
        ensure_dir(output_root)
    return True, None


def _make_log_dir(output_root: Path) -> Path:
    log_dir = output_root / 'logs' / now_timestamp()
    ensure_dir(log_dir)
    return log_dir


def _parallel_copy_files(
    copy_jobs: list[tuple[str, Path, Path]],
    logger: Logger,
    stage_name: str,
    progress_every: int = 10,
) -> None:
    total_files = len(copy_jobs)
    if total_files == 0:
        logger.info(f'{stage_name} started: total_files=0')
        return

    workers = min(resolve_worker_count(), total_files)
    logger.info(f'{stage_name} started: total_files={total_files} workers={workers}')
    adaptive_every = max(progress_every, total_files // 200)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(copy_file, src_file, dst_file): rel_path
            for rel_path, src_file, dst_file in copy_jobs
        }
        for completed, future in enumerate(as_completed(future_map), start=1):
            rel_path = future_map[future]
            try:
                future.result()
            except Exception as exc:
                logger.fatal(f'{stage_name} failed: {rel_path} ({exc})')
                raise
            if completed % adaptive_every == 0 or completed == total_files:
                logger.info(f'{stage_name} progress: {completed}/{total_files} | current: {rel_path}')


class _PrefixedLogger:
    """Forward logger methods with a side label for parallel stages."""

    def __init__(self, logger: Logger, side_label: str):
        self._logger = logger
        self._side_label = side_label

    def info(self, message: str) -> None:
        self._logger.info(f'{self._side_label}: {message}')

    def warning(self, message: str) -> None:
        self._logger.warning(f'{self._side_label}: {message}')

    def error(self, message: str) -> None:
        self._logger.error(f'{self._side_label}: {message}')

    def fatal(self, message: str) -> None:
        self._logger.fatal(f'{self._side_label}: {message}')


def _parallel_build_indexes(
    left_root: Path,
    right_root: Path,
    config: Config,
    logger: Logger,
    stage_name: str,
    left_label: str,
    right_label: str,
) -> tuple[dict, dict]:
    worker_budget = resolve_worker_count()
    per_index_workers = max(1, worker_budget // 2)
    logger.info(
        f'{stage_name} started: {left_label}+{right_label} with workers_per_index={per_index_workers}'
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        left_logger = _PrefixedLogger(logger, left_label)
        right_logger = _PrefixedLogger(logger, right_label)
        left_future = executor.submit(
            build_index,
            left_root,
            config.placeholder_suffix,
            config.hash_algorithm,
            left_logger,
            per_index_workers,
        )
        right_future = executor.submit(
            build_index,
            right_root,
            config.placeholder_suffix,
            config.hash_algorithm,
            right_logger,
            per_index_workers,
        )
        pending = {left_future: left_label, right_future: right_label}
        completed = 0
        left_index: dict | None = None
        right_index: dict | None = None
        logger.info(f'{stage_name} progress: files=0/2')
        last_heartbeat = time.monotonic()

        while pending:
            done, _ = wait(set(pending.keys()), timeout=0.25, return_when=FIRST_COMPLETED)
            if done:
                for finished in done:
                    label = pending.pop(finished)
                    index = finished.result()
                    if finished is left_future:
                        left_index = index
                    else:
                        right_index = index
                    completed += 1
                    logger.info(f'{stage_name} progress: files={completed}/2 | current: {label}')
                last_heartbeat = time.monotonic()
                continue

            now = time.monotonic()
            if now - last_heartbeat >= 3.0:
                logger.info(f'{stage_name} running: completed={completed}/2')
                last_heartbeat = now

    if left_index is None or right_index is None:
        raise FatalError(f'{stage_name} failed: index future did not complete')
    logger.info(f'{stage_name} complete: {left_label}+{right_label}')
    return left_index, right_index


def split_operation(
    source: Path,
    output_root: Path,
    config: Config,
    force: bool,
    auto_yes: bool,
    confirm_callback: Callable[[str], bool] | None = None,
) -> None:
    ok, warning = _check_output_root(output_root, force)
    if not ok:
        raise FatalError(warning or 'output root check failed')
    log_dir = _make_log_dir(output_root)
    pre_log = Logger(log_dir / 'Split_pre_check.log')
    try:
        if warning:
            pre_log.warning(warning)
        pre_log.info(f'output root ready: {output_root}')
        pre_log.info('building complete index')
        complete_index = build_index(source, config.placeholder_suffix, config.hash_algorithm, pre_log)
        write_index(output_root / 'index' / 'complete' / '.kb_index.json', complete_index)
        pre_log.info('running class1 validation on complete folder')
        validate_class1(source, config, allow_placeholders=False, logger=pre_log)
        write_summary(pre_log)
        abort_if_blockers(pre_log, 'split pre-check')
    finally:
        pre_log.close()

    prompt_confirm('Pre-check passed. Continue split?', auto_yes, confirm_callback)

    exec_log = Logger(log_dir / 'Split.log')
    try:
        folder_name = source.name
        doc_root = output_root / 'doc' / folder_name
        res_root = output_root / 'res' / folder_name
        ensure_dir(doc_root)
        ensure_dir(res_root)

        # Create directories from complete index
        for rel_dir in complete_index.get('dirs', {}).keys():
            ensure_dir(doc_root / rel_dir)
            ensure_dir(res_root / rel_dir)

        files_list = list(complete_index.get('files', {}).keys())
        copy_jobs: list[tuple[str, Path, Path]] = []
        for rel_path in files_list:
            name = Path(rel_path).name
            is_spec = is_specified_type(name, config.specified_types)
            src_file = source / rel_path
            if is_spec:
                copy_jobs.append((rel_path, src_file, doc_root / rel_path))
                placeholder_name = name + config.placeholder_suffix
                placeholder_path = (res_root / Path(rel_path).parent / placeholder_name)
                ensure_dir(placeholder_path)
            else:
                copy_jobs.append((rel_path, src_file, res_root / rel_path))
                placeholder_name = name + config.placeholder_suffix
                placeholder_path = (doc_root / Path(rel_path).parent / placeholder_name)
                ensure_dir(placeholder_path)
        _parallel_copy_files(copy_jobs, exec_log, stage_name='split copy')

        exec_log.info('writing doc/res indexes')
        doc_index, res_index = _parallel_build_indexes(
            doc_root,
            res_root,
            config,
            exec_log,
            stage_name='split indexing',
            left_label='doc',
            right_label='res',
        )
        write_index(output_root / 'index' / 'doc' / '.kb_index.json', doc_index)
        write_index(output_root / 'index' / 'res' / '.kb_index.json', res_index)

        exec_log.info('running post-check validations')
        validate_class2(doc_index, 'doc', config, exec_log)
        validate_class2(res_index, 'res', config, exec_log)
        validate_mutual(doc_index, res_index, config, exec_log)
        write_summary(exec_log)
        abort_if_blockers(exec_log, 'split post-check')
    finally:
        exec_log.close()


def merge_operation(
    doc_path: Path,
    res_path: Path,
    output_root: Path,
    config: Config,
    force: bool,
    auto_yes: bool,
    confirm_callback: Callable[[str], bool] | None = None,
) -> None:
    ok, warning = _check_output_root(output_root, force)
    if not ok:
        raise FatalError(warning or 'output root check failed')
    log_dir = _make_log_dir(output_root)
    pre_log = Logger(log_dir / 'Merge_pre_check.log')
    try:
        if warning:
            pre_log.warning(warning)
        pre_log.info(f'output root ready: {output_root}')
        name_mismatch_message: str | None = None
        if doc_path.name != res_path.name:
            name_mismatch_message = (
                f'folder name mismatch detected: doc={doc_path.name} vs res={res_path.name}. '
                'If they belong to the same knowledge base, you can continue.'
            )
            pre_log.warning(name_mismatch_message)

        pre_log.info('building doc/res indexes')
        doc_index, res_index = _parallel_build_indexes(
            doc_path,
            res_path,
            config,
            pre_log,
            stage_name='merge pre-check indexing',
            left_label='doc',
            right_label='res',
        )
        write_index(output_root / 'index' / 'merge_check_doc' / '.kb_index.json', doc_index)
        write_index(output_root / 'index' / 'merge_check_res' / '.kb_index.json', res_index)

        pre_log.info('running class1 validation on doc/res')
        validate_class1(doc_path, config, allow_placeholders=True, logger=pre_log)
        validate_class1(res_path, config, allow_placeholders=True, logger=pre_log)
        pre_log.info('running class2 validation on doc/res')
        validate_class2(doc_index, 'doc', config, pre_log)
        validate_class2(res_index, 'res', config, pre_log)
        pre_log.info('running mutual validation')
        validate_mutual(doc_index, res_index, config, pre_log)
        write_summary(pre_log)
        abort_if_blockers(pre_log, 'merge pre-check')
    finally:
        pre_log.close()

    confirm_message = 'Pre-check passed. Continue merge?'
    if doc_path.name != res_path.name:
        confirm_message = (
            f'Doc/Res folder names differ:\n'
            f'  doc: {doc_path.name}\n'
            f'  res: {res_path.name}\n\n'
            'Please confirm they are the same knowledge base.\n'
            'Continue merge?'
        )
    prompt_confirm(confirm_message, auto_yes, confirm_callback)

    exec_log = Logger(log_dir / 'Merge.log')
    try:
        folder_name = doc_path.name
        if doc_path.name != res_path.name:
            exec_log.warning(
                f'merge continuing with mismatched root names: doc={doc_path.name}, res={res_path.name}; '
                f'output uses doc name: {folder_name}'
            )
        complete_root = output_root / 'complete' / folder_name
        ensure_dir(complete_root)

        # Pre-create directory structure
        for rel_dir in doc_index.get('dirs', {}).keys():
            ensure_dir(complete_root / rel_dir)

        # Copy files from doc
        doc_files = list(doc_index.get('files', {}).keys())
        res_files = list(res_index.get('files', {}).keys())
        file_conflicts = set(doc_files) & set(res_files)
        if file_conflicts:
            exec_log.fatal(f'conflict during merge: {len(file_conflicts)} duplicate relative paths')
            abort_if_blockers(exec_log, 'merge execution')

        total_doc = len(doc_files)
        total_res = len(res_files)
        existing_targets = [
            rel_path for rel_path in (doc_files + res_files) if (complete_root / rel_path).exists()
        ]
        if existing_targets:
            exec_log.fatal(
                f'conflict during merge: {len(existing_targets)} target files already exist (e.g. {existing_targets[0]})'
            )
            abort_if_blockers(exec_log, 'merge execution')

        exec_log.info(f'merge copy queue prepared: doc_files={total_doc} res_files={total_res}')
        doc_copy_jobs = [(rel_path, doc_path / rel_path, complete_root / rel_path) for rel_path in doc_files]
        res_copy_jobs = [(rel_path, res_path / rel_path, complete_root / rel_path) for rel_path in res_files]
        _parallel_copy_files(doc_copy_jobs, exec_log, stage_name='merge copy (doc)')
        _parallel_copy_files(res_copy_jobs, exec_log, stage_name='merge copy (res)')

        merged_index = build_index(complete_root, config.placeholder_suffix, config.hash_algorithm, exec_log)
        write_index(output_root / 'index' / 'complete' / '.kb_index.json', merged_index)

        exec_log.info('running merge post-check (reverse split validation)')
        _merge_post_check(merged_index, doc_index, res_index, config, exec_log)
        write_summary(exec_log)
        abort_if_blockers(exec_log, 'merge post-check')
    finally:
        exec_log.close()


def _merge_post_check(complete_index: dict, doc_index: dict, res_index: dict, config: Config, logger: Logger) -> None:
    complete_files = set(complete_index.get('files', {}).keys())
    complete_dirs = set(complete_index.get('dirs', {}).keys())

    doc_files = set(doc_index.get('files', {}).keys())
    res_files = set(res_index.get('files', {}).keys())

    doc_placeholder_originals = {
        _placeholder_original_path(p, config.placeholder_suffix) for p in doc_index.get('placeholders', {}).keys()
    }
    res_placeholder_originals = {
        _placeholder_original_path(p, config.placeholder_suffix) for p in res_index.get('placeholders', {}).keys()
    }

    expected_doc_files = {p for p in complete_files if is_specified_type(Path(p).name, config.specified_types)}
    expected_res_files = complete_files - expected_doc_files
    expected_doc_placeholders = expected_res_files
    expected_res_placeholders = expected_doc_files

    if doc_files != expected_doc_files:
        logger.error(f'post-check mismatch: doc files expected {len(expected_doc_files)} got {len(doc_files)}')
    if res_files != expected_res_files:
        logger.error(f'post-check mismatch: res files expected {len(expected_res_files)} got {len(res_files)}')

    if doc_placeholder_originals != expected_doc_placeholders:
        logger.error('post-check mismatch: doc placeholders do not match expected')
    if res_placeholder_originals != expected_res_placeholders:
        logger.error('post-check mismatch: res placeholders do not match expected')

    doc_dirs = set(doc_index.get('dirs', {}).keys())
    res_dirs = set(res_index.get('dirs', {}).keys())
    if doc_dirs != complete_dirs:
        logger.error('post-check mismatch: doc dirs do not match complete dirs')
    if res_dirs != complete_dirs:
        logger.error('post-check mismatch: res dirs do not match complete dirs')


def index_operation(target: Path, output: Path, config: Config, log_dir: Path) -> None:
    log_path = log_dir / 'Index.log'
    log = Logger(log_path)
    try:
        index = build_index(target, config.placeholder_suffix, config.hash_algorithm, log)
        write_index(output, index)
        write_summary(log)
        abort_if_blockers(log, 'index generation')
    finally:
        log.close()


def validate_operation(target: Path, mode: str, config: Config, log_dir: Path, role: str) -> None:
    log = Logger(log_dir / 'Validate.log')
    try:
        if mode == 'class1':
            allow_placeholders = role in ('doc', 'res')
            validate_class1(target, config, allow_placeholders=allow_placeholders, logger=log)
        elif mode == 'class2':
            index = index_for_validation(target, config, log)
            validate_class2(index, role, config, log)
        else:
            log.fatal(f'unknown validate mode: {mode}')
        write_summary(log)
        abort_if_blockers(log, 'validation')
    finally:
        log.close()


def validate_mutual_operation(
    doc_path: Path,
    res_path: Path,
    config: Config,
    log_dir: Path,
    auto_yes: bool = False,
    confirm_callback: Callable[[str], bool] | None = None,
) -> None:
    log = Logger(log_dir / 'Validate_mutual.log')
    try:
        if doc_path.name != res_path.name:
            log.warning(
                f'folder name mismatch detected: doc={doc_path.name} vs res={res_path.name}. '
                'If they belong to the same knowledge base, you can continue.'
            )
            prompt_confirm(
                (
                    f'Doc/Res folder names differ:\n'
                    f'  doc: {doc_path.name}\n'
                    f'  res: {res_path.name}\n\n'
                    'Continue mutual validation?'
                ),
                auto_yes,
                confirm_callback,
            )
        doc_index, res_index = _parallel_build_indexes(
            doc_path,
            res_path,
            config,
            log,
            stage_name='validate mutual indexing',
            left_label='doc',
            right_label='res',
        )
        validate_mutual(doc_index, res_index, config, log)
        write_summary(log)
        abort_if_blockers(log, 'mutual validation')
    finally:
        log.close()


def _file_side_details(entry: dict | None) -> tuple[Any, Any, Any]:
    if not entry:
        return None, None, None
    return entry.get('size'), entry.get('mtime'), entry.get('hash')


def collect_doc_res_repair_issues(doc_index: dict, res_index: dict, config: Config) -> list[CompareIssue]:
    issues: list[CompareIssue] = []
    doc_files = doc_index.get('files', {})
    res_files = res_index.get('files', {})
    doc_placeholders = set(doc_index.get('placeholders', {}).keys())
    res_placeholders = set(res_index.get('placeholders', {}).keys())

    for rel_path, doc_entry in sorted(doc_files.items()):
        name = Path(rel_path).name
        if not is_specified_type(name, config.specified_types):
            doc_size, doc_mtime, doc_hash = _file_side_details(doc_entry)
            res_entry = res_files.get(rel_path)
            res_size, res_mtime, res_hash = _file_side_details(res_entry)
            issues.append(
                CompareIssue(
                    DOCRES_ISSUE_DOC_NON_SPECIFIED,
                    rel_path,
                    'ERROR',
                    details={
                        'old_size': doc_size,
                        'old_mtime': doc_mtime,
                        'old_hash': doc_hash,
                        'new_size': res_size,
                        'new_mtime': res_mtime,
                        'new_hash': res_hash,
                        'old_exists': True,
                        'new_exists': res_entry is not None,
                    },
                )
            )
        placeholder_rel = (Path(rel_path).parent / f'{name}{config.placeholder_suffix}').as_posix()
        if placeholder_rel not in res_placeholders:
            doc_size, doc_mtime, doc_hash = _file_side_details(doc_entry)
            issues.append(
                CompareIssue(
                    DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
                    rel_path,
                    'ERROR',
                    details={
                        'old_size': doc_size,
                        'old_mtime': doc_mtime,
                        'old_hash': doc_hash,
                        'new_size': None,
                        'new_mtime': None,
                        'new_hash': None,
                        'placeholder_path': placeholder_rel,
                        'old_exists': True,
                        'new_exists': False,
                    },
                )
            )

    for rel_path, res_entry in sorted(res_files.items()):
        name = Path(rel_path).name
        if is_specified_type(name, config.specified_types):
            res_size, res_mtime, res_hash = _file_side_details(res_entry)
            doc_entry = doc_files.get(rel_path)
            doc_size, doc_mtime, doc_hash = _file_side_details(doc_entry)
            issues.append(
                CompareIssue(
                    DOCRES_ISSUE_RES_SPECIFIED,
                    rel_path,
                    'ERROR',
                    details={
                        'old_size': doc_size,
                        'old_mtime': doc_mtime,
                        'old_hash': doc_hash,
                        'new_size': res_size,
                        'new_mtime': res_mtime,
                        'new_hash': res_hash,
                        'old_exists': doc_entry is not None,
                        'new_exists': True,
                    },
                )
            )
        placeholder_rel = (Path(rel_path).parent / f'{name}{config.placeholder_suffix}').as_posix()
        if placeholder_rel not in doc_placeholders:
            res_size, res_mtime, res_hash = _file_side_details(res_entry)
            issues.append(
                CompareIssue(
                    DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC,
                    rel_path,
                    'ERROR',
                    details={
                        'old_size': None,
                        'old_mtime': None,
                        'old_hash': None,
                        'new_size': res_size,
                        'new_mtime': res_mtime,
                        'new_hash': res_hash,
                        'placeholder_path': placeholder_rel,
                        'old_exists': False,
                        'new_exists': True,
                    },
                )
            )

    doc_placeholder_originals = {
        p: _placeholder_original_path(p, config.placeholder_suffix)
        for p in doc_placeholders
    }
    res_placeholder_originals = {
        p: _placeholder_original_path(p, config.placeholder_suffix)
        for p in res_placeholders
    }

    for placeholder_rel, original_rel in sorted(doc_placeholder_originals.items()):
        if original_rel not in res_files:
            issues.append(
                CompareIssue(
                    DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER,
                    placeholder_rel,
                    'ERROR',
                    details={
                        'old_exists': True,
                        'new_exists': False,
                        'original_rel_path': original_rel,
                    },
                )
            )

    for placeholder_rel, original_rel in sorted(res_placeholder_originals.items()):
        if original_rel not in doc_files:
            issues.append(
                CompareIssue(
                    DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
                    placeholder_rel,
                    'ERROR',
                    details={
                        'old_exists': False,
                        'new_exists': True,
                        'original_rel_path': original_rel,
                    },
                )
            )

    doc_dirs = set(doc_index.get('dirs', {}).keys())
    res_dirs = set(res_index.get('dirs', {}).keys())
    for rel_path in sorted(doc_dirs - res_dirs):
        issues.append(
            CompareIssue(
                DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
                rel_path,
                'ERROR',
                details={
                    'old_exists': True,
                    'new_exists': False,
                },
            )
        )
    for rel_path in sorted(res_dirs - doc_dirs):
        issues.append(
            CompareIssue(
                DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
                rel_path,
                'ERROR',
                details={
                    'old_exists': False,
                    'new_exists': True,
                },
            )
        )

    return sorted(issues, key=lambda x: (x.issue_type, x.rel_path))


def emit_doc_res_repair_issue_logs(issues: list[CompareIssue], logger: Logger) -> None:
    for issue in issues:
        if issue.issue_type == DOCRES_ISSUE_DOC_NON_SPECIFIED:
            logger.error(f'repair(doc/res): doc contains non-specified file: {issue.rel_path}')
        elif issue.issue_type == DOCRES_ISSUE_RES_SPECIFIED:
            logger.error(f'repair(doc/res): res contains specified file: {issue.rel_path}')
        elif issue.issue_type == DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES:
            logger.error(f'repair(doc/res): doc file missing placeholder in res: {issue.rel_path}')
        elif issue.issue_type == DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC:
            logger.error(f'repair(doc/res): res file missing placeholder in doc: {issue.rel_path}')
        elif issue.issue_type == DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER:
            logger.error(f'repair(doc/res): doc orphan placeholder: {issue.rel_path}')
        elif issue.issue_type == DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER:
            logger.error(f'repair(doc/res): res orphan placeholder: {issue.rel_path}')
        elif issue.issue_type == DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES:
            logger.error(f'repair(doc/res): doc directory missing in res: {issue.rel_path}')
        elif issue.issue_type == DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC:
            logger.error(f'repair(doc/res): res directory missing in doc: {issue.rel_path}')
        elif issue.severity == 'WARNING':
            logger.warning(f'repair(doc/res): {issue.issue_type}: {issue.rel_path}')
        elif issue.severity == 'FATAL':
            logger.fatal(f'repair(doc/res): {issue.issue_type}: {issue.rel_path}')
        else:
            logger.error(f'repair(doc/res): {issue.issue_type}: {issue.rel_path}')


def collect_complete_repair_issues(root: Path, config: Config) -> list[CompareIssue]:
    issues: list[CompareIssue] = []
    for rel_root, current_norm, dirs, files, placeholder_dirs in iter_walk(root, config.placeholder_suffix):
        for name in dirs + files + placeholder_dirs:
            full = current_norm / name
            rel_path = (rel_root / name).as_posix()
            if name.endswith(config.placeholder_suffix):
                issues.append(
                    CompareIssue(
                        COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
                        rel_path,
                        'ERROR',
                        details={
                            'old_exists': True,
                            'new_exists': False,
                            'is_dir': full.is_dir(),
                        },
                    )
                )
            if is_symlink(full):
                issues.append(
                    CompareIssue(
                        COMPLETE_ISSUE_SYMLINK,
                        rel_path,
                        'FATAL',
                        details={'old_exists': True, 'new_exists': False},
                    )
                )
    return sorted(issues, key=lambda x: (x.issue_type, x.rel_path))


def emit_complete_repair_issue_logs(issues: list[CompareIssue], logger: Logger) -> None:
    for issue in issues:
        if issue.issue_type == COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME:
            logger.error(f'repair(complete): placeholder-like name in complete: {issue.rel_path}')
        elif issue.issue_type == COMPLETE_ISSUE_SYMLINK:
            logger.fatal(f'repair(complete): symlink not allowed: {issue.rel_path}')
        elif issue.severity == 'WARNING':
            logger.warning(f'repair(complete): {issue.issue_type}: {issue.rel_path}')
        elif issue.severity == 'FATAL':
            logger.fatal(f'repair(complete): {issue.issue_type}: {issue.rel_path}')
        else:
            logger.error(f'repair(complete): {issue.issue_type}: {issue.rel_path}')


def analyze_doc_res_repair_operation(doc_path: Path, res_path: Path, config: Config, log_dir: Path) -> CompareAnalysisResult:
    log = Logger(log_dir / 'Repair_doc_res_analysis.log')
    try:
        doc_index, res_index = _parallel_build_indexes(
            doc_path,
            res_path,
            config,
            log,
            stage_name='repair doc/res indexing',
            left_label='doc',
            right_label='res',
        )
        issues = collect_doc_res_repair_issues(doc_index, res_index, config)
        emit_doc_res_repair_issue_logs(issues, log)
        write_summary(log)
    finally:
        log.close()
    return CompareAnalysisResult(old_path=doc_path, new_path=res_path, issues=issues, log_path=log.log_path)


def analyze_complete_repair_operation(root: Path, config: Config, log_dir: Path) -> CompareAnalysisResult:
    log = Logger(log_dir / 'Repair_complete_analysis.log')
    try:
        issues = collect_complete_repair_issues(root, config)
        emit_complete_repair_issue_logs(issues, log)
        write_summary(log)
    finally:
        log.close()
    return CompareAnalysisResult(old_path=root, new_path=root, issues=issues, log_path=log.log_path)


def analyze_compare_operation(old_path: Path, new_path: Path, config: Config, log_dir: Path) -> CompareAnalysisResult:
    log = Logger(log_dir / 'Compare.log')
    try:
        old_index, new_index = _parallel_build_indexes(
            old_path,
            new_path,
            config,
            log,
            stage_name='compare indexing',
            left_label='old',
            right_label='new',
        )
        issues = collect_compare_issues(old_index, new_index)
        emit_compare_issue_logs(issues, log)
        write_summary(log)
    finally:
        log.close()
    return CompareAnalysisResult(old_path=old_path, new_path=new_path, issues=issues, log_path=log.log_path)


def compare_operation(old_path: Path, new_path: Path, config: Config, log_dir: Path) -> None:
    result = analyze_compare_operation(old_path, new_path, config, log_dir)
    if result.has_blockers():
        raise FatalError(f'compare validation blocked due to errors; see log: {result.log_path}')


def apply_compare_fixes(
    old_path: Path,
    new_path: Path,
    issue_type: str,
    strategy: str,
    rel_paths: list[str],
    log_dir: Path,
) -> CompareFixResult:
    if issue_type not in COMPARE_FIXABLE_ISSUE_TYPES:
        raise FatalError(f'issue type not fixable in batch mode: {issue_type}')
    valid_strategies = list_compare_fix_strategies(issue_type)
    if strategy not in valid_strategies:
        raise FatalError(f'invalid strategy for {issue_type}: {strategy}')

    log = Logger(log_dir / 'Repair.log')
    return _apply_batch_paths(
        log=log,
        issue_type=issue_type,
        strategy=strategy,
        rel_paths=rel_paths,
        apply_func=lambda rel_path: _apply_single_compare_fix(old_path, new_path, issue_type, strategy, rel_path),
    )


def _apply_batch_paths(
    log: Logger,
    issue_type: str,
    strategy: str,
    rel_paths: list[str],
    apply_func: Callable[[str], bool],
) -> CompareFixResult:
    requested = len(rel_paths)
    applied = 0
    skipped = 0
    failed = 0
    applied_paths: list[str] = []
    failed_paths: list[str] = []
    try:
        if requested == 0:
            log.warning('repair requested with empty selection')
            write_summary(log)
            return CompareFixResult(
                issue_type=issue_type,
                strategy=strategy,
                requested=requested,
                applied=0,
                skipped=0,
                failed=0,
                applied_paths=(),
                failed_paths=(),
                log_path=log.log_path,
            )

        unique_paths = set(rel_paths)
        if strategy in (COMPARE_STRATEGY_DELETE_OLD_DIR, COMPARE_STRATEGY_DELETE_NEW_DIR):
            # Delete deeper paths first so parent dir deletions do not fail on non-empty state.
            selected = sorted(unique_paths, key=lambda p: (-p.count('/'), p))
        elif strategy in (COMPARE_STRATEGY_CREATE_DIR_IN_OLD, COMPARE_STRATEGY_CREATE_DIR_IN_NEW):
            # Create parent paths first for predictable directory creation order.
            selected = sorted(unique_paths, key=lambda p: (p.count('/'), p))
        else:
            selected = sorted(unique_paths)
        total = len(selected)
        log.info(
            f'repair started: issue_type={issue_type} strategy={strategy} selected={total}'
        )
        progress_every = max(1, total // 200)
        for idx, rel_path in enumerate(selected, start=1):
            if idx == 1 or idx == total or (idx % progress_every) == 0:
                log.info(f'repair progress: files={idx}/{total} | current: {rel_path}')
            try:
                changed = apply_func(rel_path)
                if changed:
                    applied += 1
                    applied_paths.append(rel_path)
                else:
                    skipped += 1
            except Exception as exc:
                failed += 1
                failed_paths.append(rel_path)
                log.error(f'repair failed: {rel_path} ({exc})')
        log.info(
            f'repair complete: requested={requested} applied={applied} skipped={skipped} failed={failed}'
        )
        write_summary(log)
    finally:
        log.close()

    return CompareFixResult(
        issue_type=issue_type,
        strategy=strategy,
        requested=requested,
        applied=applied,
        skipped=skipped,
        failed=failed,
        applied_paths=tuple(applied_paths),
        failed_paths=tuple(failed_paths),
        log_path=log.log_path,
    )


def apply_doc_res_fixes(
    doc_path: Path,
    res_path: Path,
    config: Config,
    issue_type: str,
    strategy: str,
    rel_paths: list[str],
    log_dir: Path,
) -> CompareFixResult:
    if issue_type not in DOCRES_FIXABLE_ISSUE_TYPES:
        raise FatalError(f'issue type not fixable in doc/res batch mode: {issue_type}')
    valid_strategies = list_fix_strategies(issue_type)
    if strategy not in valid_strategies:
        raise FatalError(f'invalid strategy for {issue_type}: {strategy}')

    log = Logger(log_dir / 'Repair_doc_res.log')
    return _apply_batch_paths(
        log=log,
        issue_type=issue_type,
        strategy=strategy,
        rel_paths=rel_paths,
        apply_func=lambda rel_path: _apply_single_doc_res_fix(
            doc_path, res_path, config, issue_type, strategy, rel_path
        ),
    )


def apply_complete_fixes(
    root_path: Path,
    config: Config,
    issue_type: str,
    strategy: str,
    rel_paths: list[str],
    log_dir: Path,
) -> CompareFixResult:
    if issue_type not in COMPLETE_FIXABLE_ISSUE_TYPES:
        raise FatalError(f'issue type not fixable in complete batch mode: {issue_type}')
    valid_strategies = list_fix_strategies(issue_type)
    if strategy not in valid_strategies:
        raise FatalError(f'invalid strategy for {issue_type}: {strategy}')

    log = Logger(log_dir / 'Repair_complete.log')
    return _apply_batch_paths(
        log=log,
        issue_type=issue_type,
        strategy=strategy,
        rel_paths=rel_paths,
        apply_func=lambda rel_path: _apply_single_complete_fix(
            root_path, config, issue_type, strategy, rel_path
        ),
    )


def _apply_single_compare_fix(
    old_path: Path,
    new_path: Path,
    issue_type: str,
    strategy: str,
    rel_path: str,
) -> bool:
    rel = Path(rel_path)
    old_node = old_path / rel
    new_node = new_path / rel

    if strategy == COMPARE_STRATEGY_COPY_OLD_TO_NEW:
        if not old_node.exists():
            raise FileNotFoundError(f'old file not found: {old_node}')
        copy_file(old_node, new_node)
        return True

    if strategy == COMPARE_STRATEGY_COPY_NEW_TO_OLD:
        if not new_node.exists():
            raise FileNotFoundError(f'new file not found: {new_node}')
        copy_file(new_node, old_node)
        return True

    if strategy == COMPARE_STRATEGY_SYNC_NEW_MTIME_FROM_OLD:
        if not old_node.exists() or not new_node.exists():
            raise FileNotFoundError(f'cannot sync mtime, missing path: {rel_path}')
        mtime = file_mtime(old_node)
        os.utime(to_extended_path(new_node), (mtime, mtime))
        return True

    if strategy == COMPARE_STRATEGY_SYNC_OLD_MTIME_FROM_NEW:
        if not old_node.exists() or not new_node.exists():
            raise FileNotFoundError(f'cannot sync mtime, missing path: {rel_path}')
        mtime = file_mtime(new_node)
        os.utime(to_extended_path(old_node), (mtime, mtime))
        return True

    if strategy == COMPARE_STRATEGY_DELETE_OLD_FILE:
        if old_node.exists():
            os.remove(to_extended_path(old_node))
            return True
        return False

    if strategy == COMPARE_STRATEGY_DELETE_NEW_FILE:
        if new_node.exists():
            os.remove(to_extended_path(new_node))
            return True
        return False

    if strategy == COMPARE_STRATEGY_CREATE_DIR_IN_NEW:
        ensure_dir(new_node)
        return True

    if strategy == COMPARE_STRATEGY_CREATE_DIR_IN_OLD:
        ensure_dir(old_node)
        return True

    if strategy == COMPARE_STRATEGY_DELETE_OLD_DIR:
        if old_node.exists():
            os.rmdir(to_extended_path(old_node))
            return True
        return False

    if strategy == COMPARE_STRATEGY_DELETE_NEW_DIR:
        if new_node.exists():
            os.rmdir(to_extended_path(new_node))
            return True
        return False

    raise FatalError(f'unsupported repair strategy: {strategy}')


def _placeholder_rel_for_file(rel_path: str, placeholder_suffix: str) -> Path:
    rel = Path(rel_path)
    return rel.parent / f'{rel.name}{placeholder_suffix}'


def _delete_empty_dir(path: Path) -> bool:
    if not path.exists():
        return False
    os.rmdir(to_extended_path(path))
    return True


def _apply_single_doc_res_fix(
    doc_path: Path,
    res_path: Path,
    config: Config,
    issue_type: str,
    strategy: str,
    rel_path: str,
) -> bool:
    rel = Path(rel_path)
    doc_node = doc_path / rel
    res_node = res_path / rel

    if strategy == REPAIR_STRATEGY_MOVE_DOC_FILE_TO_RES:
        if not doc_node.exists():
            raise FileNotFoundError(f'doc file not found: {doc_node}')
        copy_file(doc_node, res_node)
        os.remove(to_extended_path(doc_node))
        placeholder_rel = _placeholder_rel_for_file(rel_path, config.placeholder_suffix)
        ensure_dir(doc_path / placeholder_rel)
        return True

    if strategy == REPAIR_STRATEGY_MOVE_RES_FILE_TO_DOC:
        if not res_node.exists():
            raise FileNotFoundError(f'res file not found: {res_node}')
        copy_file(res_node, doc_node)
        os.remove(to_extended_path(res_node))
        placeholder_rel = _placeholder_rel_for_file(rel_path, config.placeholder_suffix)
        ensure_dir(res_path / placeholder_rel)
        return True

    if strategy == REPAIR_STRATEGY_CREATE_RES_PLACEHOLDER:
        placeholder_rel = _placeholder_rel_for_file(rel_path, config.placeholder_suffix)
        ensure_dir(res_path / placeholder_rel)
        return True

    if strategy == REPAIR_STRATEGY_CREATE_DOC_PLACEHOLDER:
        placeholder_rel = _placeholder_rel_for_file(rel_path, config.placeholder_suffix)
        ensure_dir(doc_path / placeholder_rel)
        return True

    if strategy == REPAIR_STRATEGY_DELETE_DOC_FILE:
        if doc_node.exists():
            os.remove(to_extended_path(doc_node))
            return True
        return False

    if strategy == REPAIR_STRATEGY_DELETE_RES_FILE:
        if res_node.exists():
            os.remove(to_extended_path(res_node))
            return True
        return False

    if strategy == REPAIR_STRATEGY_DELETE_DOC_PLACEHOLDER:
        return _delete_empty_dir(doc_path / rel)

    if strategy == REPAIR_STRATEGY_DELETE_RES_PLACEHOLDER:
        return _delete_empty_dir(res_path / rel)

    if strategy == COMPARE_STRATEGY_CREATE_DIR_IN_NEW:
        ensure_dir(res_node)
        return True

    if strategy == COMPARE_STRATEGY_CREATE_DIR_IN_OLD:
        ensure_dir(doc_node)
        return True

    if strategy == COMPARE_STRATEGY_DELETE_OLD_DIR:
        return _delete_empty_dir(doc_node)

    if strategy == COMPARE_STRATEGY_DELETE_NEW_DIR:
        return _delete_empty_dir(res_node)

    raise FatalError(f'unsupported doc/res repair strategy: {strategy} ({issue_type})')


def _apply_single_complete_fix(
    root_path: Path,
    config: Config,
    issue_type: str,
    strategy: str,
    rel_path: str,
) -> bool:
    rel = Path(rel_path)
    node = root_path / rel

    if strategy == REPAIR_STRATEGY_RENAME_REMOVE_PLACEHOLDER_SUFFIX:
        name = node.name
        suffix = config.placeholder_suffix
        if not name.endswith(suffix):
            return False
        new_name = name[:-len(suffix)]
        if not new_name:
            raise FatalError(f'cannot rename to empty name: {rel_path}')
        target = node.parent / new_name
        if target.exists():
            raise FatalError(f'cannot rename, target exists: {target}')
        os.rename(to_extended_path(node), to_extended_path(target))
        return True

    if strategy == REPAIR_STRATEGY_DELETE_SYMLINK:
        if not node.exists() and not os.path.lexists(to_extended_path(node)):
            return False
        if node.is_dir() and is_symlink(node):
            os.rmdir(to_extended_path(node))
            return True
        os.unlink(to_extended_path(node))
        return True

    raise FatalError(f'unsupported complete repair strategy: {strategy} ({issue_type})')
