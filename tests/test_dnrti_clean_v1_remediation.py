from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "ml/remediation/dnrti_clean_v1.py"
SPEC = importlib.util.spec_from_file_location("dnrti_clean_v1", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def sentence(split: str, index: int, text: str, labels: tuple[str, ...]):
    tokens = tuple(text.split())
    return MODULE.Sentence(split, index, tokens, labels, 1, len(tokens))


def parsed(name: str, values: list[object]):
    return MODULE.ParsedSplit(name, values, len(values), sum(len(item.tokens) for item in values), [], 0)


class CleanV1RemediationTests(unittest.TestCase):
    def test_precedence_is_test_then_validation_then_train(self) -> None:
        shared = ("B-Org",)
        source = {
            "train": parsed("train", [sentence("train", 0, "shared", shared), sentence("train", 1, "train-only", shared)]),
            "valid": parsed("valid", [sentence("valid", 0, "shared", shared), sentence("valid", 1, "valid-only", shared)]),
            "test": parsed("test", [sentence("test", 0, "shared", shared), sentence("test", 1, "test-only", shared)]),
        }
        clean, audit = MODULE.remediate(source, expected_label_count=None)
        self.assertEqual([item.tokens for item in clean["test"]], [("shared",), ("test-only",)])
        self.assertEqual([item.tokens for item in clean["valid"]], [("valid-only",)])
        self.assertEqual([item.tokens for item in clean["train"]], [("train-only",)])
        self.assertEqual(audit["removals"]["cross_split_occurrences_removed"], 2)

    def test_conflicting_labels_are_excluded_without_vote(self) -> None:
        source = {
            "train": parsed("train", [sentence("train", 0, "same text", ("B-Org", "O"))]),
            "valid": parsed("valid", []),
            "test": parsed("test", [sentence("test", 0, "same text", ("B-Tool", "O"))]),
        }
        clean, audit = MODULE.remediate(source, expected_label_count=None)
        self.assertTrue(all(not values for values in clean.values()))
        self.assertEqual(audit["removals"]["conflicting_label_groups_removed"], 1)
        self.assertEqual(audit["removals"]["conflicting_label_occurrences_removed"], 2)

    def test_invalid_bio_transition_is_excluded_not_rewritten(self) -> None:
        source = {
            "train": parsed("train", [sentence("train", 0, "broken", ("I-Org",))]),
            "valid": parsed("valid", []),
            "test": parsed("test", []),
        }
        clean, audit = MODULE.remediate(source, expected_label_count=None)
        self.assertTrue(all(not values for values in clean.values()))
        self.assertEqual(audit["removals"]["invalid_bio_occurrences_removed"], 1)

    def test_parser_rejects_complete_block_with_missing_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "train.txt"
            path.write_text("Good O\nO\nTail O\n\nKept B-Org\n\n", encoding="utf-8")
            result = MODULE.parse_split(path, "train")
        self.assertEqual(result.excluded_malformed_blocks, 1)
        self.assertEqual(len(result.malformed_lines), 1)
        self.assertEqual([item.tokens for item in result.valid_sentences], [("Kept",)])


if __name__ == "__main__":
    unittest.main()
