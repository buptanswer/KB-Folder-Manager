import os
import tempfile
import unittest
from pathlib import Path

from kb_folder_manager.config import Config
from kb_folder_manager.operations import (
    COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
    COMPLETE_ISSUE_SYMLINK,
    DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
    DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
    DOCRES_ISSUE_DOC_NON_SPECIFIED,
    DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER,
    DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
    DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC,
    DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
    DOCRES_ISSUE_RES_SPECIFIED,
    analyze_complete_repair_operation,
    analyze_compare_operation,
    analyze_doc_res_repair_operation,
    apply_complete_fixes,
    apply_compare_fixes,
    apply_doc_res_fixes,
    list_fix_strategies,
)
from kb_folder_manager.validator import (
    COMPARE_ISSUE_CONTENT_MISMATCH,
    COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW,
    COMPARE_ISSUE_EXTRA_IN_NEW,
    COMPARE_ISSUE_MISSING_IN_NEW,
    COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW,
    COMPARE_ISSUE_MTIME_DIFF_HASH_SAME,
)


class TestCompareRepair(unittest.TestCase):
    def setUp(self) -> None:
        self.config = Config(
            specified_types={'.md'},
            placeholder_suffix='(PH)',
            hash_algorithm='sha256',
            use_7zip=False,
        )

    def test_fix_mtime_diff_hash_same(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_root = root / 'old'
            new_root = root / 'new'
            old_root.mkdir(parents=True)
            new_root.mkdir(parents=True)

            rel = Path('docs') / 'same.txt'
            (old_root / rel).parent.mkdir(parents=True, exist_ok=True)
            (new_root / rel).parent.mkdir(parents=True, exist_ok=True)
            (old_root / rel).write_text('same content', encoding='utf-8')
            (new_root / rel).write_text('same content', encoding='utf-8')

            old_mtime = 1700000000.0
            new_mtime = 1700003600.0
            os.utime(old_root / rel, (old_mtime, old_mtime))
            os.utime(new_root / rel, (new_mtime, new_mtime))

            report = analyze_compare_operation(old_root, new_root, self.config, root / 'logs_1')
            issue_types = {(issue.issue_type, issue.rel_path) for issue in report.issues}
            self.assertIn((COMPARE_ISSUE_MTIME_DIFF_HASH_SAME, rel.as_posix()), issue_types)
            mtime_issue = next(
                issue for issue in report.issues
                if issue.issue_type == COMPARE_ISSUE_MTIME_DIFF_HASH_SAME and issue.rel_path == rel.as_posix()
            )
            self.assertIn('old_mtime', mtime_issue.details)
            self.assertIn('new_mtime', mtime_issue.details)
            self.assertIn('old_hash', mtime_issue.details)
            self.assertIn('new_hash', mtime_issue.details)

            result = apply_compare_fixes(
                old_root,
                new_root,
                COMPARE_ISSUE_MTIME_DIFF_HASH_SAME,
                'sync_new_mtime_from_old',
                [rel.as_posix()],
                root / 'logs_fix_1',
            )
            self.assertEqual(result.applied, 1)
            self.assertEqual(result.failed, 0)

            report_after = analyze_compare_operation(old_root, new_root, self.config, root / 'logs_2')
            issue_types_after = {(issue.issue_type, issue.rel_path) for issue in report_after.issues}
            self.assertNotIn((COMPARE_ISSUE_MTIME_DIFF_HASH_SAME, rel.as_posix()), issue_types_after)

    def test_mtime_subsecond_difference_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_root = root / 'old'
            new_root = root / 'new'
            old_root.mkdir(parents=True)
            new_root.mkdir(parents=True)

            rel = Path('docs') / 'tiny_mtime_diff.txt'
            (old_root / rel).parent.mkdir(parents=True, exist_ok=True)
            (new_root / rel).parent.mkdir(parents=True, exist_ok=True)
            (old_root / rel).write_text('same content', encoding='utf-8')
            (new_root / rel).write_text('same content', encoding='utf-8')

            base = 1700000000.0
            os.utime(old_root / rel, (base, base))
            os.utime(new_root / rel, (base + 0.3, base + 0.3))

            report = analyze_compare_operation(old_root, new_root, self.config, root / 'logs_tiny')
            issue_types = {(issue.issue_type, issue.rel_path) for issue in report.issues}
            self.assertNotIn((COMPARE_ISSUE_MTIME_DIFF_HASH_SAME, rel.as_posix()), issue_types)

    def test_fix_hash_size_missing_and_extra(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_root = root / 'old'
            new_root = root / 'new'
            old_root.mkdir(parents=True)
            new_root.mkdir(parents=True)

            mismatch_rel = Path('nested') / 'mismatch.bin'
            only_old_rel = Path('nested') / 'only_old.txt'
            only_new_rel = Path('nested') / 'only_new.txt'

            (old_root / mismatch_rel).parent.mkdir(parents=True, exist_ok=True)
            (new_root / mismatch_rel).parent.mkdir(parents=True, exist_ok=True)

            (old_root / mismatch_rel).write_bytes(b'old-content-with-different-size')
            (new_root / mismatch_rel).write_bytes(b'new-content')

            (old_root / only_old_rel).write_text('keep from old', encoding='utf-8')
            (new_root / only_new_rel).write_text('remove from new', encoding='utf-8')

            report = analyze_compare_operation(old_root, new_root, self.config, root / 'logs_3')
            issue_types = {(issue.issue_type, issue.rel_path) for issue in report.issues}
            self.assertIn((COMPARE_ISSUE_CONTENT_MISMATCH, mismatch_rel.as_posix()), issue_types)
            self.assertIn((COMPARE_ISSUE_MISSING_IN_NEW, only_old_rel.as_posix()), issue_types)
            self.assertIn((COMPARE_ISSUE_EXTRA_IN_NEW, only_new_rel.as_posix()), issue_types)
            mismatch_issue = next(
                issue for issue in report.issues
                if issue.issue_type == COMPARE_ISSUE_CONTENT_MISMATCH and issue.rel_path == mismatch_rel.as_posix()
            )
            self.assertIn('old_size', mismatch_issue.details)
            self.assertIn('new_size', mismatch_issue.details)
            self.assertIn('old_mtime', mismatch_issue.details)
            self.assertIn('new_mtime', mismatch_issue.details)

            res1 = apply_compare_fixes(
                old_root,
                new_root,
                COMPARE_ISSUE_CONTENT_MISMATCH,
                'copy_old_to_new',
                [mismatch_rel.as_posix()],
                root / 'logs_fix_2',
            )
            self.assertEqual(res1.failed, 0)

            res2 = apply_compare_fixes(
                old_root,
                new_root,
                COMPARE_ISSUE_MISSING_IN_NEW,
                'copy_old_to_new',
                [only_old_rel.as_posix()],
                root / 'logs_fix_3',
            )
            self.assertEqual(res2.failed, 0)

            res3 = apply_compare_fixes(
                old_root,
                new_root,
                COMPARE_ISSUE_EXTRA_IN_NEW,
                'delete_new_file',
                [only_new_rel.as_posix()],
                root / 'logs_fix_4',
            )
            self.assertEqual(res3.failed, 0)

            report_after = analyze_compare_operation(old_root, new_root, self.config, root / 'logs_4')
            issue_types_after = {(issue.issue_type, issue.rel_path) for issue in report_after.issues}
            self.assertNotIn((COMPARE_ISSUE_CONTENT_MISMATCH, mismatch_rel.as_posix()), issue_types_after)
            self.assertNotIn((COMPARE_ISSUE_MISSING_IN_NEW, only_old_rel.as_posix()), issue_types_after)
            self.assertNotIn((COMPARE_ISSUE_EXTRA_IN_NEW, only_new_rel.as_posix()), issue_types_after)

    def test_fix_missing_and_extra_placeholder_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_root = root / 'old'
            new_root = root / 'new'
            old_root.mkdir(parents=True)
            new_root.mkdir(parents=True)

            missing_in_new = Path('p') / f'a{self.config.placeholder_suffix}'
            extra_in_new = Path('p') / f'b{self.config.placeholder_suffix}'
            (old_root / missing_in_new).mkdir(parents=True)
            (new_root / extra_in_new).mkdir(parents=True)

            report = analyze_compare_operation(old_root, new_root, self.config, root / 'logs_ph_1')
            issue_types = {(issue.issue_type, issue.rel_path) for issue in report.issues}
            self.assertIn((COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW, missing_in_new.as_posix()), issue_types)
            self.assertIn((COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW, extra_in_new.as_posix()), issue_types)

            r1 = apply_compare_fixes(
                old_root,
                new_root,
                COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW,
                'create_dir_in_new',
                [missing_in_new.as_posix()],
                root / 'logs_ph_fix_1',
            )
            self.assertEqual(r1.failed, 0)
            self.assertTrue((new_root / missing_in_new).is_dir())

            r2 = apply_compare_fixes(
                old_root,
                new_root,
                COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW,
                'delete_new_dir',
                [extra_in_new.as_posix()],
                root / 'logs_ph_fix_2',
            )
            self.assertEqual(r2.failed, 0)
            self.assertFalse((new_root / extra_in_new).exists())

            report_after = analyze_compare_operation(old_root, new_root, self.config, root / 'logs_ph_2')
            issue_types_after = {(issue.issue_type, issue.rel_path) for issue in report_after.issues}
            self.assertNotIn((COMPARE_ISSUE_MISSING_PLACEHOLDER_IN_NEW, missing_in_new.as_posix()), issue_types_after)
            self.assertNotIn((COMPARE_ISSUE_EXTRA_PLACEHOLDER_IN_NEW, extra_in_new.as_posix()), issue_types_after)

    def test_doc_res_missing_placeholder_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc_root = root / 'doc'
            res_root = root / 'res'
            doc_root.mkdir(parents=True)
            res_root.mkdir(parents=True)

            rel = Path('chapter') / 'note.md'
            (doc_root / rel).parent.mkdir(parents=True, exist_ok=True)
            (doc_root / rel).write_text('doc side file', encoding='utf-8')

            report = analyze_doc_res_repair_operation(doc_root, res_root, self.config, root / 'logs_docres_1')
            issue_types = {(issue.issue_type, issue.rel_path) for issue in report.issues}
            self.assertIn((DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES, rel.as_posix()), issue_types)

            fix_result = apply_doc_res_fixes(
                doc_root,
                res_root,
                self.config,
                DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
                'create_res_placeholder',
                [rel.as_posix()],
                root / 'logs_docres_fix',
            )
            self.assertEqual(fix_result.applied, 1)
            self.assertEqual(fix_result.failed, 0)
            expected_placeholder = res_root / rel.parent / f'{rel.name}{self.config.placeholder_suffix}'
            self.assertTrue(expected_placeholder.is_dir())

            report_after = analyze_doc_res_repair_operation(doc_root, res_root, self.config, root / 'logs_docres_2')
            issue_types_after = {(issue.issue_type, issue.rel_path) for issue in report_after.issues}
            self.assertNotIn((DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES, rel.as_posix()), issue_types_after)

    def test_complete_placeholder_like_name_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            complete_root = root / 'complete'
            complete_root.mkdir(parents=True)

            bad_name = f'bad{self.config.placeholder_suffix}'
            bad_path = complete_root / bad_name
            bad_path.mkdir()

            report = analyze_complete_repair_operation(complete_root, self.config, root / 'logs_complete_1')
            issue_types = {(issue.issue_type, issue.rel_path) for issue in report.issues}
            self.assertIn((COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME, bad_name), issue_types)

            fix_result = apply_complete_fixes(
                complete_root,
                self.config,
                COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
                'rename_remove_placeholder_suffix',
                [bad_name],
                root / 'logs_complete_fix',
            )
            self.assertEqual(fix_result.applied, 1)
            self.assertEqual(fix_result.failed, 0)
            self.assertTrue((complete_root / 'bad').exists())
            self.assertFalse((complete_root / bad_name).exists())

    def test_doc_missing_placeholder_can_delete_doc_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc_root = root / 'doc'
            res_root = root / 'res'
            doc_root.mkdir(parents=True)
            res_root.mkdir(parents=True)

            rel = Path('chapter') / 'note.md'
            (doc_root / rel).parent.mkdir(parents=True, exist_ok=True)
            (doc_root / rel).write_text('doc side file', encoding='utf-8')

            report = analyze_doc_res_repair_operation(doc_root, res_root, self.config, root / 'logs_docres_del_1')
            issue_types = {(issue.issue_type, issue.rel_path) for issue in report.issues}
            self.assertIn((DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES, rel.as_posix()), issue_types)

            fix_result = apply_doc_res_fixes(
                doc_root,
                res_root,
                self.config,
                DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
                'delete_doc_file',
                [rel.as_posix()],
                root / 'logs_docres_del_fix',
            )
            self.assertEqual(fix_result.applied, 1)
            self.assertFalse((doc_root / rel).exists())

            report_after = analyze_doc_res_repair_operation(doc_root, res_root, self.config, root / 'logs_docres_del_2')
            issue_types_after = {(issue.issue_type, issue.rel_path) for issue in report_after.issues}
            self.assertNotIn((DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES, rel.as_posix()), issue_types_after)

    def test_doc_res_directory_mismatch_can_be_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc_root = root / 'doc'
            res_root = root / 'res'
            doc_root.mkdir(parents=True)
            res_root.mkdir(parents=True)

            doc_only_dir = Path('dir_only_doc') / 'nested'
            res_only_dir = Path('dir_only_res') / 'nested'
            (doc_root / doc_only_dir).mkdir(parents=True, exist_ok=True)
            (res_root / res_only_dir).mkdir(parents=True, exist_ok=True)

            report = analyze_doc_res_repair_operation(doc_root, res_root, self.config, root / 'logs_docres_dir_1')
            issue_types = {(issue.issue_type, issue.rel_path) for issue in report.issues}
            self.assertIn((DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES, doc_only_dir.as_posix()), issue_types)
            self.assertIn((DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC, res_only_dir.as_posix()), issue_types)

            r1 = apply_doc_res_fixes(
                doc_root,
                res_root,
                self.config,
                DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
                'create_dir_in_new',
                [doc_only_dir.as_posix()],
                root / 'logs_docres_dir_fix_1',
            )
            self.assertEqual(r1.failed, 0)
            self.assertTrue((res_root / doc_only_dir).is_dir())

            r2 = apply_doc_res_fixes(
                doc_root,
                res_root,
                self.config,
                DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
                'create_dir_in_old',
                [res_only_dir.as_posix()],
                root / 'logs_docres_dir_fix_2',
            )
            self.assertEqual(r2.failed, 0)
            self.assertTrue((doc_root / res_only_dir).is_dir())

    def test_doc_res_directory_delete_order_handles_nested_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc_root = root / 'doc'
            res_root = root / 'res'
            doc_root.mkdir(parents=True)
            res_root.mkdir(parents=True)

            parent_rel = Path('to_remove')
            child_rel = parent_rel / 'nested'
            (doc_root / child_rel).mkdir(parents=True, exist_ok=True)

            report = analyze_doc_res_repair_operation(doc_root, res_root, self.config, root / 'logs_docres_dir_del_1')
            issue_types = {(issue.issue_type, issue.rel_path) for issue in report.issues}
            self.assertIn((DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES, parent_rel.as_posix()), issue_types)
            self.assertIn((DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES, child_rel.as_posix()), issue_types)

            result = apply_doc_res_fixes(
                doc_root,
                res_root,
                self.config,
                DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
                'delete_old_dir',
                [parent_rel.as_posix(), child_rel.as_posix()],
                root / 'logs_docres_dir_del_fix',
            )
            self.assertEqual(result.failed, 0)
            self.assertEqual(result.applied, 2)
            self.assertFalse((doc_root / parent_rel).exists())

    def test_non_compare_fixable_issue_types_have_strategies(self) -> None:
        non_compare_issue_types = {
            DOCRES_ISSUE_DOC_NON_SPECIFIED,
            DOCRES_ISSUE_RES_SPECIFIED,
            DOCRES_ISSUE_DOC_MISSING_PLACEHOLDER_IN_RES,
            DOCRES_ISSUE_RES_MISSING_PLACEHOLDER_IN_DOC,
            DOCRES_ISSUE_DOC_ORPHAN_PLACEHOLDER,
            DOCRES_ISSUE_RES_ORPHAN_PLACEHOLDER,
            DOCRES_ISSUE_DOC_DIR_MISSING_IN_RES,
            DOCRES_ISSUE_RES_DIR_MISSING_IN_DOC,
            COMPLETE_ISSUE_PLACEHOLDER_LIKE_NAME,
            COMPLETE_ISSUE_SYMLINK,
        }
        for issue_type in non_compare_issue_types:
            with self.subTest(issue_type=issue_type):
                self.assertTrue(list_fix_strategies(issue_type), f'no fix strategy for {issue_type}')


if __name__ == '__main__':
    unittest.main()
