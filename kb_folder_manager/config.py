from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import normalize_specified_types, validate_placeholder_suffix


@dataclass
class Config:
    specified_types: set[str]
    placeholder_suffix: str
    hash_algorithm: str
    use_7zip: bool


DEFAULT_CONFIG_NAME = 'config.yaml'


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception as exc:
        raise RuntimeError('PyYAML is required; install with: pip install pyyaml') from exc
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError('config root must be a mapping')
    return data


def load_config(path: Path) -> Config:
    data = _load_yaml(path)
    specified_types = normalize_specified_types(data.get('specified_types', []))
    placeholder_suffix = data.get('placeholder_suffix', '')
    validate_placeholder_suffix(placeholder_suffix)
    hash_algorithm = data.get('hash_algorithm', 'sha256')
    use_7zip = bool(data.get('use_7zip', False))
    return Config(set(specified_types), placeholder_suffix, hash_algorithm, use_7zip)
