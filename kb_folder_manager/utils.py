from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

INVALID_NAME_CHARS = set('\\/:*?"<>|')
RESERVED_NAMES = {
    'CON', 'PRN', 'AUX', 'NUL',
    'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
    'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
}


def now_timestamp() -> str:
    return time.strftime('%Y-%m-%d_%H%M%S', time.localtime())


def is_unc_path(path: Path) -> bool:
    s = str(path)
    return s.startswith('\\\\') or s.startswith('//') or s.upper().startswith('\\\\?\\UNC\\') or s.upper().startswith('//?/UNC/')


def to_extended_path(path: Path) -> str:
    s = str(path.resolve())
    if s.startswith('\\\\?\\'):
        return s
    if s.startswith('\\\\') or s.startswith('//'):
        return s
    if re.match(r'^[A-Za-z]:\\', s):
        return '\\\\?\\' + s
    return s


def strip_extended_prefix(path_str: str) -> str:
    if path_str.startswith('\\\\?\\'):
        return path_str[4:]
    return path_str


def ensure_dir(path: Path) -> None:
    os.makedirs(to_extended_path(path), exist_ok=True)


def safe_scandir(path: Path):
    return os.scandir(to_extended_path(path))


def is_symlink(path: Path) -> bool:
    return os.path.islink(to_extended_path(path))


def file_size(path: Path) -> int:
    return os.path.getsize(to_extended_path(path))


def file_mtime(path: Path) -> float:
    return os.path.getmtime(to_extended_path(path))


def hash_file(path: Path, algorithm: str) -> str:
    h = hashlib.new(algorithm)
    with open(to_extended_path(path), 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def copy_file(src: Path, dst: Path) -> None:
    import shutil
    ensure_dir(dst.parent)
    shutil.copy2(to_extended_path(src), to_extended_path(dst))


def is_invalid_name_component(name: str) -> bool:
    if not name or name.strip() == '':
        return True
    if any(ch in INVALID_NAME_CHARS for ch in name):
        return True
    base = name.split('.')[0].upper()
    return base in RESERVED_NAMES


def path_has_invalid_components(path: Path) -> bool:
    for part in path.parts:
        if ':' in part:
            continue
        if is_invalid_name_component(part):
            return True
    return False


def iter_walk(root: Path, placeholder_suffix: str):
    root_ext = to_extended_path(root)
    for current, dirs, files in os.walk(root_ext):
        current_norm = Path(strip_extended_prefix(current))
        rel_root = current_norm.relative_to(root)

        placeholder_dirs = [d for d in dirs if d.endswith(placeholder_suffix)]
        for d in placeholder_dirs:
            dirs.remove(d)
        yield rel_root, current_norm, dirs, files, placeholder_dirs


def is_placeholder_dir_name(name: str, placeholder_suffix: str) -> bool:
    return name.endswith(placeholder_suffix)


def derive_placeholder_original(name: str, placeholder_suffix: str) -> str:
    if name.endswith(placeholder_suffix):
        return name[: -len(placeholder_suffix)]
    return name


@dataclass
class LogResult:
    errors: int = 0
    fatals: int = 0
    warnings: int = 0

    def has_blockers(self) -> bool:
        return self.errors > 0 or self.fatals > 0


class Logger:
    def __init__(self, log_path: Path, also_console: bool = True) -> None:
        self.log_path = log_path
        self.also_console = also_console
        ensure_dir(log_path.parent)
        self._fh = open(to_extended_path(log_path), 'w', encoding='utf-8')
        self.result = LogResult()

    def close(self) -> None:
        if self._fh:
            self._fh.close()
            self._fh = None

    def _write(self, level: str, message: str) -> None:
        line = f'[{level}] {message}'
        self._fh.write(line + '\n')
        self._fh.flush()
        if self.also_console:
            print(line)
        if level == 'WARNING':
            self.result.warnings += 1
        elif level == 'ERROR':
            self.result.errors += 1
        elif level == 'FATAL':
            self.result.fatals += 1

    def info(self, message: str) -> None:
        self._write('INFO', message)

    def warning(self, message: str) -> None:
        self._write('WARNING', message)

    def error(self, message: str) -> None:
        self._write('ERROR', message)

    def fatal(self, message: str) -> None:
        self._write('FATAL', message)


def write_json(path: Path, data: dict) -> None:
    ensure_dir(path.parent)
    with open(to_extended_path(path), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def rel_path_key(root: Path, path: Path) -> str:
    rel = path.relative_to(root)
    return rel.as_posix()


def normalize_specified_types(values: Iterable[str]) -> list[str]:
    cleaned: list[str] = []
    for v in values:
        if v is None:
            continue
        s = str(v).strip().lower()
        if not s:
            continue
        if not s.startswith('.'):
            s = '.' + s
        cleaned.append(s)
    seen = set()
    result: list[str] = []
    for s in cleaned:
        if s in seen:
            raise ValueError(f'duplicate specified type: {s}')
        if any(ch in INVALID_NAME_CHARS for ch in s) or s == '.':
            raise ValueError(f'invalid specified type: {s}')
        seen.add(s)
        result.append(s)
    return result


def is_specified_type(filename: str, specified_types: set[str]) -> bool:
    lower = filename.lower()
    suffix = Path(lower).suffix
    if not suffix:
        return False
    return suffix in specified_types


def validate_placeholder_suffix(suffix: str) -> None:
    if suffix is None:
        raise ValueError('placeholder_suffix is missing')
    if not isinstance(suffix, str):
        raise ValueError('placeholder_suffix must be a string')
    if suffix.strip() == '':
        raise ValueError('placeholder_suffix cannot be empty')
    if any(ch in INVALID_NAME_CHARS for ch in suffix):
        raise ValueError(f'placeholder_suffix contains invalid characters: {suffix}')


class FatalError(RuntimeError):
    pass


def abort_if_blockers(logger: Logger, action: str) -> None:
    if logger.result.has_blockers():
        raise FatalError(f'{action} blocked due to errors; see log: {logger.log_path}')


def prompt_confirm(message: str, auto_yes: bool) -> None:
    if auto_yes:
        return
    resp = input(f'{message} (y/N): ').strip().lower()
    if resp != 'y':
        raise FatalError('operation cancelled by user')


def write_summary(logger: Logger) -> None:
    logger.info(f'summary: warnings={logger.result.warnings}, errors={logger.result.errors}, fatals={logger.result.fatals}')
