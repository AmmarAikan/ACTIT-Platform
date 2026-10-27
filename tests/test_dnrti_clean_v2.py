from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

PATH = Path(__file__).parents[1] / "ml/training/dnrti_clean_v2.py"
SPEC = importlib.util.spec_from_file_location("dnrti_clean_v2", PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class CleanV2Tests(unittest.TestCase):
    def test_target_counts_preserve_total(self) -> None:
        targets = MODULE.target_counts(4334)
        self.assertEqual(sum(targets.values()), 4334)
        self.assertGreater(targets["train"], targets["valid"])

    def test_deterministic_disjoint_allocation(self) -> None:
        entities = ["Org", "Tool", "Malware"]
        groups = [MODULE.Sentence("train", i, (f"token-{i}",), (f"B-{entities[i % 3]}",), 1, 1) for i in range(60)]
        first, first_audit = MODULE.allocate_groups(groups, 42)
        second, second_audit = MODULE.allocate_groups(groups, 42)
        self.assertEqual(first_audit["assignment"], second_audit["assignment"])
        keys = {name: {item.tokens for item in values} for name, values in first.items()}
        self.assertFalse(keys["train"] & keys["valid"])
        self.assertFalse(keys["train"] & keys["test"])
        self.assertFalse(keys["valid"] & keys["test"])

    def test_quarantines_conflicts_and_invalid_bio(self) -> None:
        sentence = MODULE.Sentence
        parsed = {
            "train": MODULE.ParsedSplit("train", [sentence("train", 0, ("valid",), ("B-Org",), 1, 1), sentence("train", 1, ("same",), ("B-Org",), 2, 2)], 2, 2, [], 0),
            "valid": MODULE.ParsedSplit("valid", [sentence("valid", 0, ("broken",), ("I-Org",), 1, 1)], 1, 1, [], 0),
            "test": MODULE.ParsedSplit("test", [sentence("test", 0, ("same",), ("B-Tool",), 1, 1)], 1, 1, [], 0),
        }
        retained, audit = MODULE.canonical_groups(parsed)
        self.assertEqual([item.tokens for item in retained], [("valid",)])
        self.assertEqual(audit["conflicting_groups_quarantined"], 1)
        self.assertEqual(audit["invalid_bio_groups_quarantined"], 1)


if __name__ == "__main__":
    unittest.main()
