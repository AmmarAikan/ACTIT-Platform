from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "ml/training/bert_dnrti_clean_v1.py"
SPEC = importlib.util.spec_from_file_location("bert_dnrti_clean_v1", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AlignmentTests(unittest.TestCase):
    def test_bio_continuation_conversion(self) -> None:
        self.assertEqual(MODULE.continuation_label("B-HackOrg"), "I-HackOrg")
        self.assertEqual(MODULE.continuation_label("I-HackOrg"), "I-HackOrg")
        self.assertEqual(MODULE.continuation_label("O"), "O")

    def test_unique_unseen_uses_exact_tokens_and_deduplicates(self) -> None:
        split = MODULE.BioSplit
        source = {
            "train": split("train", [["Shared"]], [["O"]], 0, []),
            "valid": split("valid", [], [], 0, []),
            "test": split("test", [["Shared"], ["shared"], ["Novel"], ["Novel"]], [["O"], ["O"], ["B-Org"], ["B-Org"]], 0, []),
        }
        result = MODULE.unique_unseen_test(source)
        self.assertEqual(result.tokens, [["shared"], ["Novel"]])


if __name__ == "__main__":
    unittest.main()
