from __future__ import annotations

from datetime import datetime
from typing import Any

from .operations import (
    COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
    COMPLETE_ISSUE_SYMLINK,
    DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
    DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
    DOCRES_ISSUE_DOC_NON_SPECIFIED,
    DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER,
    DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
    DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC,
    DOCRES_ISSUE_RES_SPECIFIED,
    DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
)
from .validator import (
    COMPARE_MTIME_TOLERANCE_SECONDS,
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
)

# Strategy IDs are simple strings; keeping them central avoids GUI hardcoding.
STRATEGY_SYNC_NEW_MTIME_FROM_OLD = 'sync_new_mtime_from_old'
STRATEGY_SYNC_OLD_MTIME_FROM_NEW = 'sync_old_mtime_from_new'
STRATEGY_COPY_OLD_TO_NEW = 'copy_old_to_new'
STRATEGY_COPY_NEW_TO_OLD = 'copy_new_to_old'
STRATEGY_DELETE_NEW_FILE = 'delete_new_file'
STRATEGY_CREATE_DIR_IN_NEW = 'create_dir_in_new'
STRATEGY_DELETE_NEW_DIR = 'delete_new_dir'
STRATEGY_MOVE_DOC_FILE_TO_RES = 'move_doc_file_to_res'
STRATEGY_MOVE_RES_FILE_TO_DOC = 'move_res_file_to_doc'
STRATEGY_CREATE_RES_PLACEHOLDER = 'create_res_placeholder'
STRATEGY_CREATE_DOC_PLACEHOLDER = 'create_doc_placeholder'
STRATEGY_DELETE_DOC_FILE = 'delete_doc_file'
STRATEGY_DELETE_RES_FILE = 'delete_res_file'
STRATEGY_DELETE_DOC_PLACEHOLDER = 'delete_doc_placeholder'
STRATEGY_DELETE_RES_PLACEHOLDER = 'delete_res_placeholder'
STRATEGY_RENAME_REMOVE_PLACEHOLDER_SUFFIX = 'rename_remove_placeholder_suffix'
STRATEGY_DELETE_SYMLINK = 'delete_symlink'

MANUAL_ISSUE_TYPE = 'manual_intervention_required'

ISSUE_TYPE_LABELS = {
    COMPARE_ISSUE_MTIME_DIFF_HASH_SAME: 'mtime 不同但内容相同',
    COMPARE_ISSUE_CONTENT_MISMATCH: '内容不一致(size/hash)',
    COMPARE_ISSUE_SIZE_MISMATCH: '文件大小不一致',
    COMPARE_ISSUE_HASH_MISMATCH: '文件哈希不一致',
    COMPARE_ISSUE_MISSING_IN_NEW: '文件夹2缺失文件',
    COMPARE_ISSUE_EXTRA_IN_NEW: '文件夹2多出文件',
    COMPARE_ISSUE_MISSING_DIR_IN_NEW: '文件夹2缺失目录',
    COMPARE_ISSUE_EXTRA_DIR_IN_NEW: '文件夹2多出目录',
    COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW: '文件夹2缺失占位符',
    COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW: '文件夹2多出占位符',
    DOCRES_ISSUE_DOC_NON_SPECIFIED: 'Doc 中出现资源类型文件',
    DOCRES_ISSUE_RES_SPECIFIED: 'Res 中出现文档类型文件',
    DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES: 'Doc 文件在 Res 缺失占位符',
    DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC: 'Res 文件在 Doc 缺失占位符',
    DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER: 'Doc 占位符没有对应 Res 文件',
    DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER: 'Res 占位符没有对应 Doc 文件',
    DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES: 'Doc 目录在 Res 缺失',
    DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC: 'Res 目录在 Doc 缺失',
    COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME: 'Complete 中存在占位符后缀命名',
    COMPLETE_ISSUE_SYMLINK: 'Complete 中存在符号链接',
    MANUAL_ISSUE_TYPE: '需人工处理',
}

STRATEGY_LABELS = {
    STRATEGY_SYNC_NEW_MTIME_FROM_OLD: '用文件夹1时间对齐文件夹2',
    STRATEGY_SYNC_OLD_MTIME_FROM_NEW: '用文件夹2时间对齐文件夹1',
    STRATEGY_COPY_OLD_TO_NEW: '用文件夹1覆盖文件夹2',
    STRATEGY_COPY_NEW_TO_OLD: '用文件夹2覆盖文件夹1',
    'delete_old_file': '删除文件夹1中的选中项',
    STRATEGY_DELETE_NEW_FILE: '删除文件夹2中的选中项',
    'create_dir_in_old': '在文件夹1创建对应目录',
    STRATEGY_CREATE_DIR_IN_NEW: '在文件夹2创建对应目录',
    'delete_old_dir': '删除文件夹1中的选中目录(需为空)',
    STRATEGY_DELETE_NEW_DIR: '删除文件夹2中的选中目录(需为空)',
    STRATEGY_MOVE_DOC_FILE_TO_RES: '将 Doc 侧文件移动到 Res 并补 Doc 占位符',
    STRATEGY_MOVE_RES_FILE_TO_DOC: '将 Res 侧文件移动到 Doc 并补 Res 占位符',
    STRATEGY_CREATE_RES_PLACEHOLDER: '在 Res 创建对应占位符目录',
    STRATEGY_CREATE_DOC_PLACEHOLDER: '在 Doc 创建对应占位符目录',
    STRATEGY_DELETE_DOC_FILE: '删除 Doc 侧选中文件',
    STRATEGY_DELETE_RES_FILE: '删除 Res 侧选中文件',
    STRATEGY_DELETE_DOC_PLACEHOLDER: '删除 Doc 侧占位符目录(需为空)',
    STRATEGY_DELETE_RES_PLACEHOLDER: '删除 Res 侧占位符目录(需为空)',
    STRATEGY_RENAME_REMOVE_PLACEHOLDER_SUFFIX: '去除名称中的占位符后缀(重命名)',
    STRATEGY_DELETE_SYMLINK: '删除符号链接',
}


def issue_type_label(issue_type: str) -> str:
    return ISSUE_TYPE_LABELS.get(issue_type, issue_type)


def strategy_label(strategy: str) -> str:
    return STRATEGY_LABELS.get(strategy, strategy)


def format_size(value: Any) -> str:
    if not isinstance(value, int):
        return '-'
    if value < 1024:
        return f'{value} B'
    if value < 1024 * 1024:
        return f'{value / 1024:.1f} KB'
    if value < 1024 * 1024 * 1024:
        return f'{value / (1024 * 1024):.1f} MB'
    return f'{value / (1024 * 1024 * 1024):.2f} GB'


def format_mtime(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return '-'
    try:
        return datetime.fromtimestamp(float(value)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return '-'


def format_hash_cmp(old_hash: Any, new_hash: Any) -> str:
    if not isinstance(old_hash, str) and not isinstance(new_hash, str):
        return '-'
    if not isinstance(old_hash, str):
        return 'old:-'
    if not isinstance(new_hash, str):
        return 'new:-'
    return 'same' if old_hash == new_hash else 'diff'


def format_hash_short(value: Any, max_len: int = 12) -> str:
    if not isinstance(value, str):
        return '-'
    s = value.strip()
    if not s:
        return '-'
    if len(s) <= max_len:
        return s
    return s[:max_len]


def format_side_summary(size_value: Any, mtime_value: Any) -> str:
    size_text = format_size(size_value)
    mtime_text = format_mtime(mtime_value)
    if size_text == '-' and mtime_text == '-':
        return '-'
    return f'{size_text} | {mtime_text}'


def build_issue_hint(issue: CompareIssue) -> str:
    details = issue.details or {}
    old_size = details.get('old_size')
    new_size = details.get('new_size')
    old_mtime = details.get('old_mtime')
    new_mtime = details.get('new_mtime')

    if issue.issue_type == COMPARE_ISSUE_MISSING_IN_NEW:
        return '仅文件夹1存在'
    if issue.issue_type == COMPARE_ISSUE_EXTRA_IN_NEW:
        return '仅文件夹2存在'
    if issue.issue_type == COMPARE_ISSUE_MISSING_DIR_IN_NEW:
        return '目录仅在文件夹1存在'
    if issue.issue_type == COMPARE_ISSUE_EXTRA_DIR_IN_NEW:
        return '目录仅在文件夹2存在'
    if issue.issue_type == COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW:
        return '占位符仅在文件夹1存在'
    if issue.issue_type == COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW:
        return '占位符仅在文件夹2存在'
    if issue.issue_type == DOCRES_ISSUE_DOC_NON_SPECIFIED:
        return 'Doc 中出现资源文件，建议移到 Res'
    if issue.issue_type == DOCRES_ISSUE_RES_SPECIFIED:
        return 'Res 中出现文档文件，建议移到 Doc'
    if issue.issue_type == DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES:
        return 'Res 缺少对应占位符（可补占位符或删除 Doc 文件）'
    if issue.issue_type == DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC:
        return 'Doc 缺少对应占位符（可补占位符或删除 Res 文件）'
    if issue.issue_type == DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER:
        return 'Doc 占位符无对应 Res 文件'
    if issue.issue_type == DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER:
        return 'Res 占位符无对应 Doc 文件'
    if issue.issue_type == DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES:
        return '目录仅在 Doc 存在（可在 Res 创建或删 Doc 空目录）'
    if issue.issue_type == DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC:
        return '目录仅在 Res 存在（可在 Doc 创建或删 Res 空目录）'
    if issue.issue_type == COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME:
        return '名称含占位符后缀，建议去后缀重命名'
    if issue.issue_type == COMPLETE_ISSUE_SYMLINK:
        return '符号链接不允许，建议删除'
    if issue.issue_type == MANUAL_ISSUE_TYPE:
        msg = str(details.get('message') or '').strip()
        return msg if msg else '需人工处理'

    if issue.issue_type in (COMPARE_ISSUE_CONTENT_MISMATCH, COMPARE_ISSUE_HASH_MISMATCH, COMPARE_ISSUE_SIZE_MISMATCH):
        direction_parts: list[str] = []
        if isinstance(old_size, int) and isinstance(new_size, int):
            if old_size > new_size:
                direction_parts.append('文件夹1更大')
            elif new_size > old_size:
                direction_parts.append('文件夹2更大')
        if isinstance(old_mtime, (int, float)) and isinstance(new_mtime, (int, float)):
            if (old_mtime - new_mtime) > COMPARE_MTIME_TOLERANCE_SECONDS:
                direction_parts.append('文件夹1更新')
            elif (new_mtime - old_mtime) > COMPARE_MTIME_TOLERANCE_SECONDS:
                direction_parts.append('文件夹2更新')
        if direction_parts:
            return '，'.join(direction_parts)
        return '内容不同，需人工判断覆盖方向'

    if issue.issue_type == COMPARE_ISSUE_MTIME_DIFF_HASH_SAME:
        if isinstance(old_mtime, (int, float)) and isinstance(new_mtime, (int, float)):
            delta = int(round(old_mtime - new_mtime))
            return f'仅时间戳不同（Δ={delta:+d}s，内容一致）'
        return '时间戳不同'

    return issue_type_label(issue.issue_type)


def recommended_strategy_key(issue: CompareIssue) -> str | None:
    details = issue.details or {}
    old_size = details.get('old_size')
    new_size = details.get('new_size')
    old_mtime = details.get('old_mtime')
    new_mtime = details.get('new_mtime')

    if issue.issue_type == COMPARE_ISSUE_MISSING_IN_NEW:
        return STRATEGY_COPY_OLD_TO_NEW
    if issue.issue_type == COMPARE_ISSUE_EXTRA_IN_NEW:
        return STRATEGY_DELETE_NEW_FILE
    if issue.issue_type == DOCRES_ISSUE_DOC_NON_SPECIFIED:
        return STRATEGY_MOVE_DOC_FILE_TO_RES
    if issue.issue_type == DOCRES_ISSUE_RES_SPECIFIED:
        return STRATEGY_MOVE_RES_FILE_TO_DOC
    if issue.issue_type == DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES:
        return STRATEGY_CREATE_RES_PLACEHOLDER
    if issue.issue_type == DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC:
        return STRATEGY_CREATE_DOC_PLACEHOLDER
    if issue.issue_type == DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER:
        return STRATEGY_DELETE_DOC_PLACEHOLDER
    if issue.issue_type == DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER:
        return STRATEGY_DELETE_RES_PLACEHOLDER
    if issue.issue_type == DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES:
        return STRATEGY_CREATE_DIR_IN_NEW
    if issue.issue_type == DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC:
        return 'create_dir_in_old'
    if issue.issue_type == COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME:
        return STRATEGY_RENAME_REMOVE_PLACEHOLDER_SUFFIX
    if issue.issue_type == COMPLETE_ISSUE_SYMLINK:
        return STRATEGY_DELETE_SYMLINK
    if issue.issue_type == MANUAL_ISSUE_TYPE:
        return None
    if issue.issue_type in (COMPARE_ISSUE_MISSING_DIR_IN_NEW, COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW):
        return STRATEGY_CREATE_DIR_IN_NEW
    if issue.issue_type in (COMPARE_ISSUE_EXTRA_DIR_IN_NEW, COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW):
        return STRATEGY_DELETE_NEW_DIR
    if issue.issue_type == COMPARE_ISSUE_MTIME_DIFF_HASH_SAME:
        if isinstance(old_mtime, (int, float)) and isinstance(new_mtime, (int, float)):
            if old_mtime >= new_mtime:
                return STRATEGY_SYNC_NEW_MTIME_FROM_OLD
            return STRATEGY_SYNC_OLD_MTIME_FROM_NEW
        return STRATEGY_SYNC_NEW_MTIME_FROM_OLD
    if issue.issue_type in (COMPARE_ISSUE_CONTENT_MISMATCH, COMPARE_ISSUE_HASH_MISMATCH, COMPARE_ISSUE_SIZE_MISMATCH):
        if isinstance(old_mtime, (int, float)) and isinstance(new_mtime, (int, float)):
            if (old_mtime - new_mtime) > COMPARE_MTIME_TOLERANCE_SECONDS:
                return STRATEGY_COPY_OLD_TO_NEW
            if (new_mtime - old_mtime) > COMPARE_MTIME_TOLERANCE_SECONDS:
                return STRATEGY_COPY_NEW_TO_OLD
        if isinstance(old_size, int) and isinstance(new_size, int):
            if old_size >= new_size:
                return STRATEGY_COPY_OLD_TO_NEW
            return STRATEGY_COPY_NEW_TO_OLD
    return None


def recommended_strategy_label(issue: CompareIssue) -> str:
    key = recommended_strategy_key(issue)
    if not key:
        return '根据业务规则选择策略'
    return strategy_label(key)
