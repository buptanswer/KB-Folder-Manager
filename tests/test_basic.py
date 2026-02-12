import os
import tempfile
import unittest
from pathlib import Path

from kb_folder_manager.config import Config
from kb_folder_manager.operations import (
    compare_operation,
    merge_operation,
    split_operation,
    validate_mutual_operation,
)
from kb_folder_manager.utils import FatalError, Logger
from kb_folder_manager.validator import validate_class1


class TestSplitMerge(unittest.TestCase):
    def test_split_merge_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            complete = root / 'Complete'
            (complete / 'empty_dir').mkdir(parents=True)
            (complete / 'nested').mkdir(parents=True)
            (complete / 'nested' / 'a.md').write_text('hello', encoding='utf-8')
            (complete / 'nested' / 'b.bin').write_bytes(b'\x00\x01')

            config = Config(specified_types={'.md'}, placeholder_suffix='(PH)', hash_algorithm='sha256', use_7zip=False)

            out1 = root / 'out1'
            split_operation(complete, out1, config, force=False, auto_yes=True)

            doc = out1 / 'doc' / 'Complete'
            res = out1 / 'res' / 'Complete'

            self.assertTrue((doc / 'nested' / 'a.md').is_file())
            self.assertTrue((res / 'nested' / 'b.bin').is_file())
            self.assertTrue((doc / 'nested' / 'b.bin(PH)').is_dir())
            self.assertTrue((res / 'nested' / 'a.md(PH)').is_dir())
            self.assertTrue((doc / 'empty_dir').is_dir())
            self.assertTrue((res / 'empty_dir').is_dir())

            out2 = root / 'out2'
            merge_operation(doc, res, out2, config, force=False, auto_yes=True)

            merged = out2 / 'complete' / 'Complete'
            self.assertTrue((merged / 'nested' / 'a.md').is_file())
            self.assertTrue((merged / 'nested' / 'b.bin').is_file())
            self.assertTrue((merged / 'empty_dir').is_dir())
            self.assertFalse((merged / 'nested' / 'a.md(PH)').exists())

            compare_logs = root / 'compare_logs'
            compare_operation(complete, merged, config, compare_logs)

    def test_class1_placeholder_in_complete_is_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            complete = root / 'Complete'
            (complete / 'a(PH)').mkdir(parents=True)
            config = Config(specified_types={'.md'}, placeholder_suffix='(PH)', hash_algorithm='sha256', use_7zip=False)
            log_path = root / 'log.txt'
            logger = Logger(log_path, also_console=False)
            try:
                validate_class1(complete, config, allow_placeholders=False, logger=logger)
            finally:
                logger.close()
            self.assertGreater(logger.result.fatals, 0)

    def test_merge_allows_name_mismatch_when_confirmed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            complete = root / 'Complete'
            (complete / 'nested').mkdir(parents=True)
            (complete / 'nested' / 'a.md').write_text('hello', encoding='utf-8')
            (complete / 'nested' / 'b.bin').write_bytes(b'\x00\x01')

            config = Config(specified_types={'.md'}, placeholder_suffix='(PH)', hash_algorithm='sha256', use_7zip=False)
            out1 = root / 'out1'
            split_operation(complete, out1, config, force=False, auto_yes=True)

            doc = out1 / 'doc' / 'Complete'
            res = out1 / 'res' / 'Complete'
            renamed_res = out1 / 'res' / 'Complete_res'
            os.rename(res, renamed_res)

            out2 = root / 'out2'
            merge_operation(
                doc,
                renamed_res,
                out2,
                config,
                force=False,
                auto_yes=False,
                confirm_callback=lambda _msg: True,
            )
            merged = out2 / 'complete' / 'Complete'
            self.assertTrue((merged / 'nested' / 'a.md').is_file())
            self.assertTrue((merged / 'nested' / 'b.bin').is_file())

    def test_merge_name_mismatch_can_be_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            complete = root / 'Complete'
            (complete / 'nested').mkdir(parents=True)
            (complete / 'nested' / 'a.md').write_text('hello', encoding='utf-8')
            (complete / 'nested' / 'b.bin').write_bytes(b'\x00\x01')

            config = Config(specified_types={'.md'}, placeholder_suffix='(PH)', hash_algorithm='sha256', use_7zip=False)
            out1 = root / 'out1'
            split_operation(complete, out1, config, force=False, auto_yes=True)

            doc = out1 / 'doc' / 'Complete'
            res = out1 / 'res' / 'Complete'
            renamed_res = out1 / 'res' / 'Complete_res'
            os.rename(res, renamed_res)

            out2 = root / 'out2'
            with self.assertRaises(FatalError):
                merge_operation(
                    doc,
                    renamed_res,
                    out2,
                    config,
                    force=False,
                    auto_yes=False,
                    confirm_callback=lambda _msg: False,
                )

    def test_validate_mutual_name_mismatch_can_be_cancelled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            complete = root / 'Complete'
            (complete / 'nested').mkdir(parents=True)
            (complete / 'nested' / 'a.md').write_text('hello', encoding='utf-8')
            (complete / 'nested' / 'b.bin').write_bytes(b'\x00\x01')

            config = Config(specified_types={'.md'}, placeholder_suffix='(PH)', hash_algorithm='sha256', use_7zip=False)
            out1 = root / 'out1'
            split_operation(complete, out1, config, force=False, auto_yes=True)

            doc = out1 / 'doc' / 'Complete'
            res = out1 / 'res' / 'Complete'
            renamed_res = out1 / 'res' / 'Complete_res'
            os.rename(res, renamed_res)

            with self.assertRaises(FatalError):
                validate_mutual_operation(
                    doc,
                    renamed_res,
                    config,
                    root / 'mutual_logs_1',
                    auto_yes=False,
                    confirm_callback=lambda _msg: False,
                )

    def test_validate_mutual_name_mismatch_can_continue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            complete = root / 'Complete'
            (complete / 'nested').mkdir(parents=True)
            (complete / 'nested' / 'a.md').write_text('hello', encoding='utf-8')
            (complete / 'nested' / 'b.bin').write_bytes(b'\x00\x01')

            config = Config(specified_types={'.md'}, placeholder_suffix='(PH)', hash_algorithm='sha256', use_7zip=False)
            out1 = root / 'out1'
            split_operation(complete, out1, config, force=False, auto_yes=True)

            doc = out1 / 'doc' / 'Complete'
            res = out1 / 'res' / 'Complete'
            renamed_res = out1 / 'res' / 'Complete_res'
            os.rename(res, renamed_res)

            validate_mutual_operation(
                doc,
                renamed_res,
                config,
                root / 'mutual_logs_2',
                auto_yes=False,
                confirm_callback=lambda _msg: True,
            )


if __name__ == '__main__':
    unittest.main()
