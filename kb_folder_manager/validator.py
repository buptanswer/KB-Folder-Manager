from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import Config
from .indexer import build_index
from .utils import (
    Logger,
    derive_placeholder_original,
    is_invalid_name_component,
    is_specified_type,
    is_symlink,
    is_unc_path,
    iter_walk,
    path_has_invalid_components,
    safe_scandir,
)

COMPARE_ISSUE_MISSING_IN_NEW = 'missing_in_new'
COMPARE_ISSUE_EXTRA_IN_NEW = 'extra_in_new'
COMPARE_ISSUE_CONTENT_MISMATCH = 'content_mismatch'
COMPARE_ISSUE_SIZE_MISMATCH = 'size_mismatch'
COMPARE_ISSUE_HASH_MISMATCH = 'hash_mismatch'
COMPARE_ISSUE_MTIME_DIFF_HASH_SAME = 'mtime_diff_hash_same'
COMPARE_ISSUE_MISSING_DIR_IN_NEW = 'missing_dir_in_new'
COMPARE_ISSUE_EXTRA_DIR_IN_NEW = 'extra_dir_in_new'
COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW = 'missing_placeholder_in_new'
COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW = 'extra_placeholder_in_new'
COMPARE_MTIME_TOLERANCE_SECONDS = 1.0

COMPARE_FIXABLE_ISSUE_TYPES = {
    COMPARE_ISSUE_MISSING_IN_NEW,
    COMPARE_ISSUE_EXTRA_IN_NEW,
    COMPARE_ISSUE_CONTENT_MISMATCH,
    COMPARE_ISSUE_SIZE_MISMATCH,  # Backward compatible alias
    COMPARE_ISSUE_HASH_MISMATCH,  # Backward compatible alias
    COMPARE_ISSUE_MTIME_DIFF_HASH_SAME,
    COMPARE_ISSUE_MISSING_DIR_IN_NEW,
    COMPARE_ISSUE_EXTRA_DIR_IN_NEW,
    COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW,
    COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW,
}


@dataclass(frozen=True)
class CompareIssue:
    issue_type: str
    rel_path: str
    severity: str
    details: dict[str, Any] = field(default_factory=dict)


def collect_compare_issues(old_index: dict, new_index: dict) -> list[CompareIssue]:
    issues: list[CompareIssue] = []
    old_files = old_index.get('files', {})
    new_files = new_index.get('files', {})

    old_file_keys = set(old_files.keys())
    new_file_keys = set(new_files.keys())

    for rel_path in sorted(old_file_keys - new_file_keys):
        old_entry = old_files[rel_path]
        details = {
            'old_exists': True,
            'new_exists': False,
            'old_size': old_entry.get('size'),
            'new_size': None,
            'old_hash': old_entry.get('hash'),
            'new_hash': None,
            'old_mtime': old_entry.get('mtime'),
            'new_mtime': None,
        }
        issues.append(CompareIssue(COMPARE_ISSUE_MISSING_IN_NEW, rel_path, 'ERROR', details=details))
    for rel_path in sorted(new_file_keys - old_file_keys):
        new_entry = new_files[rel_path]
        details = {
            'old_exists': False,
            'new_exists': True,
            'old_size': None,
            'new_size': new_entry.get('size'),
            'old_hash': None,
            'new_hash': new_entry.get('hash'),
            'old_mtime': None,
            'new_mtime': new_entry.get('mtime'),
        }
        issues.append(CompareIssue(COMPARE_ISSUE_EXTRA_IN_NEW, rel_path, 'ERROR', details=details))

    common = old_file_keys & new_file_keys
    for rel_path in sorted(common):
        old_entry = old_files[rel_path]
        new_entry = new_files[rel_path]
        old_size = old_entry.get('size')
        new_size = new_entry.get('size')
        old_hash = old_entry.get('hash')
        new_hash = new_entry.get('hash')
        old_mtime = old_entry.get('mtime')
        new_mtime = new_entry.get('mtime')
        common_details = {
            'old_exists': True,
            'new_exists': True,
            'old_size': old_size,
            'new_size': new_size,
            'old_hash': old_hash,
            'new_hash': new_hash,
            'old_mtime': old_mtime,
            'new_mtime': new_mtime,
        }

        if old_size != new_size or old_hash != new_hash:
            issues.append(
                CompareIssue(
                    COMPARE_ISSUE_CONTENT_MISMATCH,
                    rel_path,
                    'ERROR',
                    details={
                        **common_details,
                        'size_delta': (old_size - new_size) if isinstance(old_size, int) and isinstance(new_size, int) else None,
                        'size_equal': old_size == new_size,
                        'hash_equal': old_hash == new_hash,
                    },
                )
            )
        elif (
            isinstance(old_mtime, (int, float))
            and isinstance(new_mtime, (int, float))
            and abs(old_mtime - new_mtime) > COMPARE_MTIME_TOLERANCE_SECONDS
        ):
            issues.append(
                CompareIssue(
                    COMPARE_ISSUE_MTIME_DIFF_HASH_SAME,
                    rel_path,
                    'WARNING',
                    details={
                        **common_details,
                        'mtime_delta_seconds': (
                            old_mtime - new_mtime
                            if isinstance(old_mtime, (int, float)) and isinstance(new_mtime, (int, float))
                            else None
                        ),
                    },
                )
            )

    old_dirs = set(old_index.get('dirs', {}).keys())
    new_dirs = set(new_index.get('dirs', {}).keys())
    for rel_path in sorted(old_dirs - new_dirs):
        issues.append(
            CompareIssue(
                COMPARE_ISSUE_MISSING_DIR_IN_NEW,
                rel_path,
                'ERROR',
                details={'old_exists': True, 'new_exists': False},
            )
        )
    for rel_path in sorted(new_dirs - old_dirs):
        issues.append(
            CompareIssue(
                COMPARE_ISSUE_EXTRA_DIR_IN_NEW,
                rel_path,
                'ERROR',
                details={'old_exists': False, 'new_exists': True},
            )
        )

    old_placeholders = set(old_index.get('placeholders', {}).keys())
    new_placeholders = set(new_index.get('placeholders', {}).keys())
    for rel_path in sorted(old_placeholders - new_placeholders):
        issues.append(
            CompareIssue(
                COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW,
                rel_path,
                'ERROR',
                details={'old_exists': True, 'new_exists': False},
            )
        )
    for rel_path in sorted(new_placeholders - old_placeholders):
        issues.append(
            CompareIssue(
                COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW,
                rel_path,
                'ERROR',
                details={'old_exists': False, 'new_exists': True},
            )
        )

    return sorted(issues, key=lambda x: (x.issue_type, x.rel_path))


def group_compare_issues_by_type(issues: list[CompareIssue]) -> dict[str, list[CompareIssue]]:
    grouped: dict[str, list[CompareIssue]] = {}
    for issue in issues:
        grouped.setdefault(issue.issue_type, []).append(issue)
    return grouped


def emit_compare_issue_logs(issues: list[CompareIssue], logger: Logger) -> None:
    for issue in issues:
        if issue.issue_type == COMPARE_ISSUE_MISSING_IN_NEW:
            logger.error(f'compare: missing file in new: {issue.rel_path}')
        elif issue.issue_type == COMPARE_ISSUE_EXTRA_IN_NEW:
            logger.error(f'compare: extra file in new: {issue.rel_path}')
        elif issue.issue_type == COMPARE_ISSUE_CONTENT_MISMATCH:
            logger.error(f'compare: content mismatch (size/hash): {issue.rel_path}')
        elif issue.issue_type == COMPARE_ISSUE_SIZE_MISMATCH:
            logger.error(f'compare: size mismatch: {issue.rel_path}')
        elif issue.issue_type == COMPARE_ISSUE_HASH_MISMATCH:
            logger.error(f'compare: hash mismatch: {issue.rel_path}')
        elif issue.issue_type == COMPARE_ISSUE_MTIME_DIFF_HASH_SAME:
            logger.warning(f'compare: mtime differs but hash same: {issue.rel_path}')
        elif issue.issue_type == COMPARE_ISSUE_MISSING_DIR_IN_NEW:
            logger.error(f'compare: missing dir in new: {issue.rel_path}')
        elif issue.issue_type == COMPARE_ISSUE_EXTRA_DIR_IN_NEW:
            logger.error(f'compare: extra dir in new: {issue.rel_path}')
        elif issue.issue_type == COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW:
            logger.error(f'compare: missing placeholder in new: {issue.rel_path}')
        elif issue.issue_type == COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW:
            logger.error(f'compare: extra placeholder in new: {issue.rel_path}')
        else:
            if issue.severity == 'WARNING':
                logger.warning(f'compare: {issue.issue_type}: {issue.rel_path}')
            elif issue.severity == 'FATAL':
                logger.fatal(f'compare: {issue.issue_type}: {issue.rel_path}')
            else:
                logger.error(f'compare: {issue.issue_type}: {issue.rel_path}')


def _check_case_conflicts(root: Path, placeholder_suffix: str, logger: Logger) -> None:
    seen: dict[str, str] = {}
    for rel_root, current_norm, dirs, files, placeholder_dirs in iter_walk(root, placeholder_suffix):
        for name in dirs + files + placeholder_dirs:
            rel_path = (rel_root / name).as_posix()
            key = rel_path.lower()
            if key in seen and seen[key] != rel_path:
                logger.fatal(f'case conflict: {seen[key]} vs {rel_path}')
            else:
                seen[key] = rel_path


def _check_placeholder_dirs(root: Path, placeholder_suffix: str, allow_placeholders: bool, logger: Logger) -> None:
    for rel_root, current_norm, dirs, files, placeholder_dirs in iter_walk(root, placeholder_suffix):
        if not allow_placeholders:
            for name in dirs + files + placeholder_dirs:
                if name.endswith(placeholder_suffix):
                    rel_path = (rel_root / name).as_posix()
                    logger.fatal(f'placeholder-like name not allowed in complete folder: {rel_path}')
        for d in placeholder_dirs:
            rel_path = (rel_root / d).as_posix()
            if not allow_placeholders:
                continue
            full = current_norm / d
            try:
                with safe_scandir(full) as it:
                    if any(True for _ in it):
                        logger.error(f'placeholder dir not empty: {rel_path}')
            except Exception as exc:
                logger.error(f'failed to scan placeholder dir: {rel_path} ({exc})')


def _check_invalid_names(root: Path, placeholder_suffix: str, logger: Logger) -> None:
    if path_has_invalid_components(root):
        logger.fatal(f'root path has invalid components: {root}')
    for rel_root, _current_norm, dirs, files, placeholder_dirs in iter_walk(root, placeholder_suffix):
        for name in dirs + files + placeholder_dirs:
            if is_invalid_name_component(name):
                rel_path = (rel_root / name).as_posix()
                logger.fatal(f'invalid name component: {rel_path}')


def _check_symlinks(root: Path, placeholder_suffix: str, logger: Logger) -> None:
    for rel_root, current_norm, dirs, files, placeholder_dirs in iter_walk(root, placeholder_suffix):
        for name in dirs + files + placeholder_dirs:
            full = current_norm / name
            if is_symlink(full):
                rel_path = (rel_root / name).as_posix()
                logger.fatal(f'symlink not allowed: {rel_path}')


def _check_long_paths(root: Path, placeholder_suffix: str, logger: Logger) -> None:
    threshold = 240
    for rel_root, current_norm, dirs, files, placeholder_dirs in iter_walk(root, placeholder_suffix):
        for name in dirs + files + placeholder_dirs:
            full = current_norm / name
            if len(str(full)) >= threshold:
                rel_path = (rel_root / name).as_posix()
                logger.warning(f'long path detected (len>={threshold}): {rel_path}')


def validate_class1(root: Path, config: Config, allow_placeholders: bool, logger: Logger) -> None:
    if is_unc_path(root):
        logger.fatal(f'UNC path not allowed: {root}')
    _check_invalid_names(root, config.placeholder_suffix, logger)
    _check_symlinks(root, config.placeholder_suffix, logger)
    _check_case_conflicts(root, config.placeholder_suffix, logger)
    _check_long_paths(root, config.placeholder_suffix, logger)
    _check_placeholder_dirs(root, config.placeholder_suffix, allow_placeholders, logger)


def _placeholder_original_path(rel_path: str, placeholder_suffix: str) -> str:
    p = Path(rel_path)
    name = p.name
    original = derive_placeholder_original(name, placeholder_suffix)
    return (p.parent / original).as_posix() if p.parent != Path('.') else original


def validate_class2(index: dict, folder_role: str, config: Config, logger: Logger) -> None:
    if folder_role not in ('doc', 'res'):
        logger.fatal(f'class2 only supports doc/res, got: {folder_role}')
        return
    specified = config.specified_types
    for rel_path, entry in index.get('files', {}).items():
        name = Path(rel_path).name
        is_spec = is_specified_type(name, specified)
        if folder_role == 'doc' and not is_spec:
            logger.error(f'doc contains non-specified file: {rel_path}')
        if folder_role == 'res' and is_spec:
            logger.error(f'res contains specified file: {rel_path}')

    for rel_path, entry in index.get('placeholders', {}).items():
        if entry.get('placeholder_suffix') != config.placeholder_suffix:
            logger.error(f'placeholder suffix mismatch: {rel_path}')
        original = _placeholder_original_path(rel_path, config.placeholder_suffix)
        original_name = Path(original).name
        is_spec = is_specified_type(original_name, specified)
        if folder_role == 'doc' and is_spec:
            logger.error(f'doc placeholder should map to non-specified: {rel_path}')
        if folder_role == 'res' and not is_spec:
            logger.error(f'res placeholder should map to specified: {rel_path}')

    # placeholder vs dirs collision
    placeholder_paths = set(index.get('placeholders', {}).keys())
    dir_paths = set(index.get('dirs', {}).keys())
    collision = placeholder_paths & dir_paths
    for rel_path in sorted(collision):
        logger.error(f'placeholder path also in dirs: {rel_path}')


def validate_mutual(doc_index: dict, res_index: dict, config: Config, logger: Logger) -> None:
    doc_files = set(doc_index.get('files', {}).keys())
    res_files = set(res_index.get('files', {}).keys())

    doc_placeholders = set(doc_index.get('placeholders', {}).keys())
    res_placeholders = set(res_index.get('placeholders', {}).keys())

    doc_placeholder_originals = {
        _placeholder_original_path(p, config.placeholder_suffix) for p in doc_placeholders
    }
    res_placeholder_originals = {
        _placeholder_original_path(p, config.placeholder_suffix) for p in res_placeholders
    }

    conflicts = doc_files & res_files
    for rel_path in sorted(conflicts):
        logger.error(f'conflict: file exists in both doc and res: {rel_path}')

    both_placeholder = doc_placeholder_originals & res_placeholder_originals
    for rel_path in sorted(both_placeholder):
        logger.error(f'missing file: placeholder on both sides for {rel_path}')

    for rel_path in sorted(doc_files):
        if rel_path not in res_placeholder_originals:
            logger.error(f'doc file missing placeholder in res: {rel_path}')

    for rel_path in sorted(res_files):
        if rel_path not in doc_placeholder_originals:
            logger.error(f'res file missing placeholder in doc: {rel_path}')

    for rel_path in sorted(doc_placeholder_originals):
        if rel_path not in res_files:
            logger.error(f'doc placeholder has no file in res: {rel_path}')

    for rel_path in sorted(res_placeholder_originals):
        if rel_path not in doc_files:
            logger.error(f'res placeholder has no file in doc: {rel_path}')

    logical_doc = doc_files | doc_placeholder_originals
    logical_res = res_files | res_placeholder_originals
    if logical_doc != logical_res:
        missing_in_res = logical_doc - logical_res
        missing_in_doc = logical_res - logical_doc
        if missing_in_res:
            logger.info(f'logical files missing in res (derived): {len(missing_in_res)}')
        if missing_in_doc:
            logger.info(f'logical files missing in doc (derived): {len(missing_in_doc)}')

    doc_dirs = set(doc_index.get('dirs', {}).keys())
    res_dirs = set(res_index.get('dirs', {}).keys())
    if doc_dirs != res_dirs:
        missing_in_res_dirs = sorted(doc_dirs - res_dirs)
        missing_in_doc_dirs = sorted(res_dirs - doc_dirs)
        for rel_path in missing_in_res_dirs:
            logger.error(f'doc directory missing in res: {rel_path}')
        for rel_path in missing_in_doc_dirs:
            logger.error(f'res directory missing in doc: {rel_path}')
        logger.info(
            f'directory structure mismatch summary: doc={len(doc_dirs)} res={len(res_dirs)} '
            f'missing_in_res={len(missing_in_res_dirs)} missing_in_doc={len(missing_in_doc_dirs)}'
        )


def compare_indexes(old_index: dict, new_index: dict, logger: Logger) -> None:
    issues = collect_compare_issues(old_index, new_index)
    emit_compare_issue_logs(issues, logger)


def index_for_validation(root: Path, config: Config, logger: Logger) -> dict:
    return build_index(root, config.placeholder_suffix, config.hash_algorithm, logger)
