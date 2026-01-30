from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import DEFAULT_CONFIG_NAME, load_config
from .operations import (
    compare_operation,
    index_operation,
    merge_operation,
    split_operation,
    validate_mutual_operation,
    validate_operation,
)
from .utils import FatalError, now_timestamp


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='KB Folder Manager')
    parser.add_argument('--config', type=Path, default=Path(DEFAULT_CONFIG_NAME), help='Path to config.yaml')
    parser.add_argument('--yes', action='store_true', help='Auto-confirm prompts')
    sub = parser.add_subparsers(dest='command', required=True)

    split = sub.add_parser('split', help='Split complete folder into doc/res')
    split.add_argument('--source', type=Path, required=True, help='Complete folder path')
    split.add_argument('--output-root', type=Path, required=True, help='Output root folder')
    split.add_argument('--force', action='store_true', help='Allow non-empty output root')

    merge = sub.add_parser('merge', help='Merge doc/res into complete')
    merge.add_argument('--doc', type=Path, required=True, help='Doc folder path')
    merge.add_argument('--res', type=Path, required=True, help='Res folder path')
    merge.add_argument('--output-root', type=Path, required=True, help='Output root folder')
    merge.add_argument('--force', action='store_true', help='Allow non-empty output root')

    index = sub.add_parser('index', help='Generate index for a folder')
    index.add_argument('--target', type=Path, required=True, help='Target folder path')
    index.add_argument('--output', type=Path, required=True, help='Output index file path')
    index.add_argument('--log-dir', type=Path, required=True, help='Directory to store logs')

    validate = sub.add_parser('validate', help='Validate a folder or pair of folders')
    validate.add_argument('--mode', choices=['class1', 'class2', 'mutual', 'compare'], required=True, help='Validation mode')
    validate.add_argument('--target', type=Path, help='Target folder path (class1/class2)')
    validate.add_argument('--role', choices=['complete', 'doc', 'res'], default='complete', help='Folder role (class1/class2)')
    validate.add_argument('--doc', type=Path, help='Doc folder path (mutual)')
    validate.add_argument('--res', type=Path, help='Res folder path (mutual)')
    validate.add_argument('--old', type=Path, help='Old folder path (compare)')
    validate.add_argument('--new', type=Path, help='New folder path (compare)')
    validate.add_argument('--log-dir', type=Path, required=True, help='Directory to store logs')

    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    try:
        config = load_config(args.config)
        if args.command == 'split':
            split_operation(args.source, args.output_root, config, args.force, args.yes)
        elif args.command == 'merge':
            merge_operation(args.doc, args.res, args.output_root, config, args.force, args.yes)
        elif args.command == 'index':
            log_dir = args.log_dir / now_timestamp()
            index_operation(args.target, args.output, config, log_dir)
        elif args.command == 'validate':
            log_dir = args.log_dir / now_timestamp()
            if args.mode in ('class1', 'class2'):
                if not args.target:
                    raise FatalError('validate mode class1/class2 requires --target')
                validate_operation(args.target, args.mode, config, log_dir, args.role)
            elif args.mode == 'mutual':
                if not args.doc or not args.res:
                    raise FatalError('validate mode mutual requires --doc and --res')
                validate_mutual_operation(args.doc, args.res, config, log_dir)
            elif args.mode == 'compare':
                if not args.old or not args.new:
                    raise FatalError('validate mode compare requires --old and --new')
                compare_operation(args.old, args.new, config, log_dir)
            else:
                raise FatalError(f'unknown validate mode: {args.mode}')
        else:
            raise FatalError('unknown command')
        return 0
    except FatalError as exc:
        print(f'[FATAL] {exc}')
        return 2
    except Exception as exc:
        print(f'[ERROR] {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
