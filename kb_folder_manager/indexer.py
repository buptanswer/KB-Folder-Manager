from __future__ import annotations

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
    write_json,
)


def build_index(root: Path, placeholder_suffix: str, hash_algorithm: str, logger: Logger | None = None) -> dict:
    files: dict[str, dict] = {}
    dirs: dict[str, dict] = {}
    placeholders: dict[str, dict] = {}
    progress_every = 200
    file_count = 0
    dir_count = 0
    placeholder_count = 0

    if logger:
        logger.info(f'indexing started: {root}')

    for rel_root, current_norm, dirs_list, files_list, placeholder_dirs in iter_walk(root, placeholder_suffix):
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
            fpath = current_norm / fname
            try:
                size = file_size(fpath)
                mtime = file_mtime(fpath)
                files[rel_path_key(root, fpath)] = {
                    'kind': 'file',
                    'size': size,
                    'mtime': mtime,
                    'hash': hash_file(fpath, hash_algorithm),
                    'hash_alg': hash_algorithm,
                }
                file_count += 1
                if logger and file_count % progress_every == 0:
                    logger.info(
                        f'indexing progress: files={file_count} dirs={dir_count} placeholders={placeholder_count}'
                    )
            except Exception as exc:
                if logger:
                    logger.error(f'failed to index file: {fpath} ({exc})')
                raise

    return {
        'files': files,
        'dirs': dirs,
        'placeholders': placeholders,
        'metadata': {
            'root_path': str(root),
            'generated_at': _dt.datetime.now().isoformat(timespec='seconds'),
        },
    }
    if logger:
        logger.info(
            f'indexing complete: files={file_count} dirs={dir_count} placeholders={placeholder_count}'
        )


def write_index(path: Path, index: dict) -> None:
    write_json(path, index)
