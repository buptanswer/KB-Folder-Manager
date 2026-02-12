from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as _dt
from pathlib import Path

from .utils import (
    Logger,
    derive_placeholder_original,
    file_mtime,
    file_size,
    hash_file,
    iter_walk,
    rel_path_key,
    resolve_worker_count,
    write_json,
)


def _index_single_file(root: Path, fpath: Path, hash_algorithm: str) -> tuple[str, dict]:
    size = file_size(fpath)
    mtime = file_mtime(fpath)
    return rel_path_key(root, fpath), {
        'kind': 'file',
        'size': size,
        'mtime': mtime,
        'hash': hash_file(fpath, hash_algorithm),
        'hash_alg': hash_algorithm,
    }


def build_index(
    root: Path,
    placeholder_suffix: str,
    hash_algorithm: str,
    logger: Logger | None = None,
    max_workers: int | None = None,
) -> dict:
    files: dict[str, dict] = {}
    dirs: dict[str, dict] = {}
    placeholders: dict[str, dict] = {}
    dir_count = 0
    placeholder_count = 0
    file_paths: list[Path] = []

    if logger:
        logger.info(f'indexing started: {root}')

    for rel_root, current_norm, dirs_list, files_list, placeholder_dirs in iter_walk(
        root, placeholder_suffix
    ):
        if rel_root != Path('.'):
            key = rel_root.as_posix()
            dirs[key] = {'kind': 'dir'}
        for d in dirs_list:
            rel_path = (rel_root / d).as_posix()
            dirs[rel_path] = {'kind': 'dir'}
            dir_count += 1
        for d in placeholder_dirs:
            rel_path = (rel_root / d).as_posix()
            placeholders[rel_path] = {
                'kind': 'placeholder_dir',
                'placeholder_for_name': derive_placeholder_original(d, placeholder_suffix),
                'placeholder_suffix': placeholder_suffix,
            }
            placeholder_count += 1
        for fname in files_list:
            file_paths.append(current_norm / fname)

    total_files = len(file_paths)
    workers = min(resolve_worker_count(max_workers), total_files) if total_files > 0 else 1
    progress_every = max(10, total_files // 200) if total_files > 0 else 10
    if logger:
        logger.info(
            f'indexing queue prepared: files={total_files} dirs={dir_count} placeholders={placeholder_count} workers={workers}'
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(_index_single_file, root, fpath, hash_algorithm): fpath
            for fpath in file_paths
        }
        for done_count, future in enumerate(as_completed(future_map), start=1):
            fpath = future_map[future]
            try:
                rel_key, file_entry = future.result()
            except Exception as exc:
                if logger:
                    logger.error(f'failed to index file: {fpath} ({exc})')
                raise
            files[rel_key] = file_entry
            if logger and (done_count % progress_every == 0 or done_count == total_files):
                logger.info(
                    f'indexing progress: files={done_count}/{total_files} dirs={dir_count} placeholders={placeholder_count}'
                )

    files = dict(sorted(files.items()))
    dirs = dict(sorted(dirs.items()))
    placeholders = dict(sorted(placeholders.items()))

    if logger:
        logger.info(
            f'indexing complete: files={total_files} dirs={dir_count} placeholders={placeholder_count}'
        )

    return {
        'files': files,
        'dirs': dirs,
        'placeholders': placeholders,
        'metadata': {
            'root_path': str(root),
            'generated_at': _dt.datetime.now().isoformat(timespec='seconds'),
        },
    }


def write_index(path: Path, index: dict) -> None:
    write_json(path, index)
