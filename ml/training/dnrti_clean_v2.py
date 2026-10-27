from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ml.remediation.dnrti_clean_v1 import (  # noqa: E402
    SPLIT_FILES, ParsedSplit, Sentence, entity_spans, invalid_bio_transitions,
    key_hash, original_audit, parse_split, sha256_file, token_key, write_split,
)

SEED = 42
SOURCE_RATIO = {"train": 5251, "valid": 662, "test": 664}


def stable_hash(seed: int, purpose: str, value: str) -> str:
    return hashlib.sha256(f"dnrti-clean-v2|{seed}|{purpose}|{value}".encode()).hexdigest()


def target_counts(total: int) -> dict[str, int]:
    denominator = sum(SOURCE_RATIO.values())
    exact = {key: total * value / denominator for key, value in SOURCE_RATIO.items()}
    result = {key: int(value) for key, value in exact.items()}
    order = sorted(result, key=lambda key: (-(exact[key] - result[key]), key))
    for key in order[: total - sum(result.values())]:
        result[key] += 1
    return result


def entity_types(sentence: Sentence) -> tuple[str, ...]:
    return tuple(sorted({name for name, _, _ in entity_spans(sentence.labels)}))


def length_bin(length: int) -> str:
    return "01-16" if length <= 16 else "17-32" if length <= 32 else "33-64" if length <= 64 else "65-plus"


def canonical_groups(parsed: dict[str, ParsedSplit]) -> tuple[list[Sentence], dict[str, object]]:
    grouped: dict[tuple[str, ...], list[Sentence]] = defaultdict(list)
    for split in ("train", "valid", "test"):
        for sentence in parsed[split].valid_sentences:
            grouped[token_key(sentence.tokens)].append(sentence)
    retained: list[Sentence] = []
    conflicts: list[dict[str, object]] = []
    invalid: list[dict[str, object]] = []
    duplicate_count = 0
    for tokens, occurrences in grouped.items():
        group_id = key_hash(tokens)
        sequences = {item.labels for item in occurrences}
        if len(sequences) > 1:
            conflicts.append({"group_id": group_id, "occurrences": len(occurrences)})
            continue
        defects = invalid_bio_transitions(occurrences[0].labels)
        if defects:
            invalid.append({"group_id": group_id, "occurrences": len(occurrences), "defects": defects})
            continue
        retained.append(min(occurrences, key=lambda item: (item.split, item.index)))
        duplicate_count += len(occurrences) - 1
    retained.sort(key=lambda item: key_hash(item.tokens))
    return retained, {
        "eligible_unique_groups": len(retained),
        "conflicting_groups_quarantined": len(conflicts),
        "conflicting_occurrences_quarantined": sum(item["occurrences"] for item in conflicts),
        "invalid_bio_groups_quarantined": len(invalid),
        "invalid_bio_occurrences_quarantined": sum(item["occurrences"] for item in invalid),
        "identical_duplicate_occurrences_audit_only": duplicate_count,
        "conflict_audit": conflicts,
        "invalid_bio_audit": invalid,
    }


def allocate_groups(groups: list[Sentence], seed: int) -> tuple[dict[str, list[Sentence]], dict[str, object]]:
    splits = ("train", "valid", "test")
    targets = target_counts(len(groups))
    by_id = {key_hash(item.tokens): item for item in groups}
    entity_groups: dict[str, list[str]] = defaultdict(list)
    for group_id, sentence in by_id.items():
        for entity in entity_types(sentence):
            entity_groups[entity].append(group_id)
    assignment: dict[str, str] = {}
    reservations: list[dict[str, str]] = []
    for entity in sorted(entity_groups, key=lambda key: (len(entity_groups[key]), key)):
        candidates = sorted(entity_groups[entity], key=lambda value: stable_hash(seed, f"coverage|{entity}", value))
        if len(candidates) < 3:
            continue
        for split in splits:
            if any(assignment.get(group_id) == split for group_id in candidates):
                continue
            candidate = next((group_id for group_id in candidates if group_id not in assignment), None)
            if candidate is None:
                raise RuntimeError(f"Cannot reserve {entity} coverage for {split}")
            assignment[candidate] = split
            reservations.append({"entity_type": entity, "split": split, "group_id": candidate})
    strata: dict[tuple[tuple[str, ...], str], list[str]] = defaultdict(list)
    for group_id, sentence in by_id.items():
        if group_id not in assignment:
            strata[(entity_types(sentence), length_bin(len(sentence.tokens)))].append(group_id)
    counts = Counter(assignment.values())
    for stratum in sorted(strata, key=lambda value: (value[1], value[0])):
        members = sorted(strata[stratum], key=lambda value: stable_hash(seed, f"allocate|{stratum}", value))
        local_targets = target_counts(len(members))
        local_counts: Counter[str] = Counter()
        for group_id in members:
            choices = [split for split in splits if counts[split] < targets[split]] or list(splits)
            chosen = max(choices, key=lambda split: (
                local_targets[split] - local_counts[split],
                targets[split] - counts[split],
                stable_hash(seed, f"tie|{group_id}", split),
            ))
            assignment[group_id] = chosen
            counts[chosen] += 1
            local_counts[chosen] += 1
    if {split: counts[split] for split in splits} != targets:
        raise RuntimeError(f"Allocation missed frozen targets: {dict(counts)} != {targets}")
    allocated = {split: [] for split in splits}
    for group_id, split in assignment.items():
        source = by_id[group_id]
        allocated[split].append(Sentence(split, source.index, source.tokens, source.labels, source.first_line, source.last_line))
    for split in splits:
        allocated[split].sort(key=lambda item: key_hash(item.tokens))
    coverage = {split: sorted({entity for item in allocated[split] for entity in entity_types(item)}) for split in splits}
    all_entities = set(entity_groups)
    missing = {split: sorted(all_entities - set(values)) for split, values in coverage.items()}
    if any(missing.values()):
        raise RuntimeError(f"Entity coverage failed: {missing}")
    return allocated, {
        "seed": seed, "source_ratio": SOURCE_RATIO, "target_counts": targets,
        "actual_counts": dict(counts),
        "stratification": "entity-type presence signature plus sentence-length bin",
        "coverage_reservations": reservations, "entity_type_coverage": coverage,
        "missing_entity_types": missing,
        "assignment": [{"group_id": group_id, "split": assignment[group_id]} for group_id in sorted(assignment)],
    }


def validate(allocated: dict[str, list[Sentence]]) -> dict[str, bool]:
    keys = {split: {item.tokens for item in values} for split, values in allocated.items()}
    labels = {label for values in allocated.values() for item in values for label in item.labels}
    return {
        "train_valid_overlap_zero": not keys["train"].intersection(keys["valid"]),
        "train_test_overlap_zero": not keys["train"].intersection(keys["test"]),
        "valid_test_overlap_zero": not keys["valid"].intersection(keys["test"]),
        "conflicting_duplicate_annotations_zero": True,
        "malformed_lines_zero": True,
        "invalid_bio_transitions_zero": all(not invalid_bio_transitions(item.labels) for values in allocated.values() for item in values),
        "exact_27_label_map_preserved": len(labels) == 27,
        "all_entity_types_present_in_each_split": all(len({entity for item in values for entity in entity_types(item)}) == 13 for values in allocated.values()),
    }


def markdown(report: dict[str, object]) -> str:
    lines = [
        "# DNRTI Clean-v2 Construction Report", "",
        "The original DNRTI files were read only. No model metric influenced this split and no BIO label was rewritten.", "",
        "## Frozen policy", "", "- Exact case-sensitive token groups.",
        "- Conflicts, malformed blocks, and invalid BIO groups quarantined.",
        "- Deterministic group-aware allocation using seed `42`, entity-presence strata, and length bins.",
        "- Every entity type reserved in train, validation, and test before general allocation.", "",
        "## Derived files", "", "| Split | Sentences | Tokens | SHA-256 |", "|---|---:|---:|---|",
    ]
    for split in ("train", "valid", "test"):
        item = report["derived_files"][SPLIT_FILES[split]]
        lines.append(f"| {split} | {item['sentences']} | {item['tokens']} | `{item['sha256']}` |")
    lines.extend(["", "## Quality gates", ""])
    lines.extend(f"- {key}: {'PASS' if value else 'FAIL'}" for key, value in report["quality_gates"].items())
    lines.extend(["", f"All pre-training gates passed: **{report['all_quality_gates_passed']}**.", ""])
    return "\n".join(lines)


def build(args: argparse.Namespace) -> dict[str, object]:
    source, output = args.source_dir.resolve(), args.output_dir.resolve()
    if source == output or (output.exists() and any(output.iterdir())):
        raise SystemExit("Output must be a different, empty directory")
    source_hashes = {name: {"sha256": sha256_file(source / name), "bytes": (source / name).stat().st_size} for name in SPLIT_FILES.values()}
    parsed = {split: parse_split(source / name, split) for split, name in SPLIT_FILES.items()}
    groups, construction = canonical_groups(parsed)
    allocated, allocation = allocate_groups(groups, args.seed)
    gates = validate(allocated)
    if not all(gates.values()):
        raise RuntimeError(f"Pre-training gates failed: {gates}")
    for split, name in SPLIT_FILES.items():
        write_split(output / name, allocated[split])
    derived = {name: {"sha256": sha256_file(output / name), "bytes": (output / name).stat().st_size,
                      "sentences": len(allocated[split]), "tokens": sum(len(item.tokens) for item in allocated[split])}
               for split, name in SPLIT_FILES.items()}
    after = {name: {"sha256": sha256_file(source / name), "bytes": (source / name).stat().st_size} for name in SPLIT_FILES.values()}
    if after != source_hashes:
        raise RuntimeError("Original data changed during construction")
    report = {
        "schema_version": "2.0", "policy_version": "dnrti-clean-v2.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_directory": str(source), "derived_directory": str(output),
        "source_files_modified": False, "model_metrics_used_for_construction": False,
        "bio_normalization_applied": False, "original_files": source_hashes,
        "original_audit": original_audit(parsed), "construction": construction,
        "allocation": allocation, "derived_files": derived, "quality_gates": gates,
        "all_quality_gates_passed": all(gates.values()),
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.report_markdown.write_text(markdown(report), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--report-markdown", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SEED)
    report = build(parser.parse_args())
    print(json.dumps({"derived_files": report["derived_files"], "quality_gates": report["quality_gates"]}, indent=2))


if __name__ == "__main__":
    main()
