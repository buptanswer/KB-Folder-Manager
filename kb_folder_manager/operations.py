from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .config import Config
from .indexer import build_index, write_index
from .utils import (
    FatalError,
    Logger,
    abort_if_blockers,
    copy_file,
    ensure_dir,
    is_specified_type,
    now_timestamp,
    prompt_confirm,
    resolve_worker_count,
    safe_scandir,
    write_summary,
)
from .validator import (
    _placeholder_original_path,
    compare_indexes,
    index_for_validation,
    validate_class1,
    validate_class2,
    validate_mutual,
)


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
            if completed % progress_every == 0 or completed == total_files:
                logger.info(f'{stage_name} progress: {completed}/{total_files} | current: {rel_path}')


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
        left_future = executor.submit(
            build_index, left_root, config.placeholder_suffix, config.hash_algorithm, None, per_index_workers
        )
        right_future = executor.submit(
            build_index, right_root, config.placeholder_suffix, config.hash_algorithm, None, per_index_workers
        )
        left_index = left_future.result()
        right_index = right_future.result()
    logger.info(f'{stage_name} complete: {left_label}+{right_label}')
    return left_index, right_index


def split_operation(source: Path, output_root: Path, config: Config, force: bool, auto_yes: bool) -> None:
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

    prompt_confirm('Pre-check passed. Continue split?', auto_yes)

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


def merge_operation(doc_path: Path, res_path: Path, output_root: Path, config: Config, force: bool, auto_yes: bool) -> None:
    ok, warning = _check_output_root(output_root, force)
    if not ok:
        raise FatalError(warning or 'output root check failed')
    log_dir = _make_log_dir(output_root)
    pre_log = Logger(log_dir / 'Merge_pre_check.log')
    try:
        if warning:
            pre_log.warning(warning)
        pre_log.info(f'output root ready: {output_root}')
        if doc_path.name != res_path.name:
            pre_log.fatal(f'folder name mismatch: {doc_path.name} vs {res_path.name}')
        if pre_log.result.has_blockers():
            write_summary(pre_log)
            abort_if_blockers(pre_log, 'merge pre-check')

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

    prompt_confirm('Pre-check passed. Continue merge?', auto_yes)

    exec_log = Logger(log_dir / 'Merge.log')
    try:
        folder_name = doc_path.name
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


def validate_mutual_operation(doc_path: Path, res_path: Path, config: Config, log_dir: Path) -> None:
    log = Logger(log_dir / 'Validate_mutual.log')
    try:
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


def compare_operation(old_path: Path, new_path: Path, config: Config, log_dir: Path) -> None:
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
        compare_indexes(old_index, new_index, log)
        write_summary(log)
        abort_if_blockers(log, 'compare validation')
    finally:
        log.close()
