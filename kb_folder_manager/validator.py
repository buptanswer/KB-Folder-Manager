from __future__ import annotations

from pathlib import Path

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
            logger.error(f'logical files missing in res: {len(missing_in_res)}')
        if missing_in_doc:
            logger.error(f'logical files missing in doc: {len(missing_in_doc)}')

    doc_dirs = set(doc_index.get('dirs', {}).keys())
    res_dirs = set(res_index.get('dirs', {}).keys())
    if doc_dirs != res_dirs:
        logger.error(f'directory structure mismatch: doc={len(doc_dirs)} res={len(res_dirs)}')


def compare_indexes(old_index: dict, new_index: dict, logger: Logger) -> None:
    old_files = old_index.get('files', {})
    new_files = new_index.get('files', {})

    old_file_keys = set(old_files.keys())
    new_file_keys = set(new_files.keys())

    missing = old_file_keys - new_file_keys
    extra = new_file_keys - old_file_keys
    for rel_path in sorted(missing):
        logger.error(f'compare: missing file in new: {rel_path}')
    for rel_path in sorted(extra):
        logger.error(f'compare: extra file in new: {rel_path}')

    common = old_file_keys & new_file_keys
    for rel_path in sorted(common):
        old_entry = old_files[rel_path]
        new_entry = new_files[rel_path]
        if old_entry.get('size') != new_entry.get('size'):
            logger.error(f'compare: size mismatch: {rel_path}')
        if old_entry.get('hash') != new_entry.get('hash'):
            logger.error(f'compare: hash mismatch: {rel_path}')
        else:
            if old_entry.get('mtime') != new_entry.get('mtime'):
                logger.warning(f'compare: mtime differs but hash same: {rel_path}')

    old_dirs = set(old_index.get('dirs', {}).keys())
    new_dirs = set(new_index.get('dirs', {}).keys())
    if old_dirs != new_dirs:
        logger.error(f'compare: directory mismatch old={len(old_dirs)} new={len(new_dirs)}')

    old_placeholders = set(old_index.get('placeholders', {}).keys())
    new_placeholders = set(new_index.get('placeholders', {}).keys())
    if old_placeholders != new_placeholders:
        logger.error(f'compare: placeholder mismatch old={len(old_placeholders)} new={len(new_placeholders)}')


def index_for_validation(root: Path, config: Config, logger: Logger) -> dict:
    return build_index(root, config.placeholder_suffix, config.hash_algorithm, logger)
