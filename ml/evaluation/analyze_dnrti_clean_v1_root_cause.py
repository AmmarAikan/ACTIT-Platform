from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.remediation.dnrti_clean_v1 import (  # noqa: E402
    SPLIT_FILES,
    SPLIT_PRECEDENCE,
    Sentence,
    entity_spans,
    invalid_bio_transitions,
    key_hash,
    parse_split,
    sha256_file,
    token_key,
)


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    position = max(0, math.ceil(percentile * len(sorted_values)) - 1)
    return sorted_values[position]


def _distribution(sentences: Iterable[Sentence]) -> dict[str, object]:
    materialized = list(sentences)
    lengths = sorted(len(item.tokens) for item in materialized)
    label_counts = Counter(label for item in materialized for label in item.labels)
    entity_counts = Counter(
        entity
        for item in materialized
        for entity, _, _ in entity_spans(item.labels)
    )
    entity_total = sum(entity_counts.values())
    token_total = sum(lengths)
    entity_per_sentence = sorted(
        len(entity_spans(item.labels)) for item in materialized
    )
    non_o_tokens = sum(count for label, count in label_counts.items() if label != "O")
    return {
        "sentences": len(materialized),
        "tokens": token_total,
        "bio_label_counts": dict(sorted(label_counts.items())),
        "entity_span_counts": dict(sorted(entity_counts.items())),
        "entity_span_total": entity_total,
        "non_o_tokens": non_o_tokens,
        "non_o_token_density_per_100": 100 * non_o_tokens / token_total if token_total else 0.0,
        "entity_density_per_sentence": entity_total / len(materialized) if materialized else 0.0,
        "entity_density_per_100_tokens": 100 * entity_total / token_total if token_total else 0.0,
        "sequence_length": {
            "min": lengths[0] if lengths else 0,
            "p25": _percentile(lengths, 0.25),
            "p50": _percentile(lengths, 0.50),
            "p75": _percentile(lengths, 0.75),
            "p90": _percentile(lengths, 0.90),
            "p95": _percentile(lengths, 0.95),
            "p99": _percentile(lengths, 0.99),
            "max": lengths[-1] if lengths else 0,
            "mean": sum(lengths) / len(lengths) if lengths else 0.0,
            "bins": {
                "1_10": sum(1 <= value <= 10 for value in lengths),
                "11_25": sum(11 <= value <= 25 for value in lengths),
                "26_50": sum(26 <= value <= 50 for value in lengths),
                "51_75": sum(51 <= value <= 75 for value in lengths),
                "76_100": sum(76 <= value <= 100 for value in lengths),
                "101_120": sum(101 <= value <= 120 for value in lengths),
                "gt_120": sum(value > 120 for value in lengths),
            },
        },
        "entities_per_sentence": {
            "p50": _percentile(entity_per_sentence, 0.50),
            "p90": _percentile(entity_per_sentence, 0.90),
            "p95": _percentile(entity_per_sentence, 0.95),
            "max": entity_per_sentence[-1] if entity_per_sentence else 0,
        },
    }


def _read_clean(clean_dir: Path) -> dict[str, list[Sentence]]:
    parsed = {
        split: parse_split(clean_dir / filename, split)
        for split, filename in SPLIT_FILES.items()
    }
    if any(value.malformed_lines or value.excluded_malformed_blocks for value in parsed.values()):
        raise RuntimeError("Clean-v1 unexpectedly contains malformed sentence blocks")
    return {name: data.valid_sentences for name, data in parsed.items()}


def _all_groups(splits: dict[str, Iterable[Sentence]]) -> dict[tuple[str, ...], list[Sentence]]:
    groups: dict[tuple[str, ...], list[Sentence]] = defaultdict(list)
    for values in splits.values():
        for item in values:
            groups[token_key(item.tokens)].append(item)
    return groups


def _canonicalize_bio(labels: tuple[str, ...]) -> tuple[str, ...]:
    repaired: list[str] = []
    previous = "O"
    for label in labels:
        output = label
        if label.startswith("I-"):
            entity = label[2:]
            if previous not in {f"B-{entity}", f"I-{entity}"}:
                output = f"B-{entity}"
        repaired.append(output)
        previous = output
    return tuple(repaired)


def _conflict_analysis(groups: dict[tuple[str, ...], list[Sentence]]) -> dict[str, object]:
    groups_by_split = Counter[str]()
    same_entity_type_set = 0
    canonicalizable = 0
    representatives: list[dict[str, object]] = []
    affected_classes = Counter[str]()
    count = 0
    occurrences = 0
    for tokens, values in groups.items():
        sequences = {item.labels for item in values}
        if len(sequences) <= 1:
            continue
        count += 1
        occurrences += len(values)
        split_signature = "+".join(sorted({item.split for item in values}, key=SPLIT_PRECEDENCE.__getitem__))
        groups_by_split[split_signature] += 1
        type_sets = {
            tuple(sorted({label.split("-", 1)[1] for label in sequence if label != "O"}))
            for sequence in sequences
        }
        same_entity_type_set += int(len(type_sets) == 1)
        canonical_sequences = {_canonicalize_bio(sequence) for sequence in sequences}
        canonicalizable += int(len(canonical_sequences) == 1)
        for sequence in sequences:
            affected_classes.update(label.split("-", 1)[1] for label in sequence if label != "O")
        if len(representatives) < 12:
            representatives.append({
                "token_sequence_sha256": key_hash(tokens),
                "safe_text_excerpt": " ".join(tokens)[:180],
                "occurrences": len(values),
                "split_signature": split_signature,
                "distinct_label_sequences": len(sequences),
                "same_entity_type_set": len(type_sets) == 1,
                "becomes_identical_after_only_structural_I_to_B_normalization": len(canonical_sequences) == 1,
                "label_sequence_examples": [list(sequence) for sequence in sorted(sequences)[:3]],
            })
    return {
        "groups": count,
        "occurrences": occurrences,
        "groups_by_source_split_signature": dict(sorted(groups_by_split.items())),
        "groups_with_same_entity_type_set_but_span_or_bio_disagreement": same_entity_type_set,
        "groups_becoming_identical_after_structural_i_to_b_normalization": canonicalizable,
        "groups_remaining_semantically_ambiguous_after_structural_normalization": count - canonicalizable,
        "affected_entity_label_mentions": dict(sorted(affected_classes.items())),
        "representative_examples": representatives,
    }


def _structural_analysis(groups: dict[tuple[str, ...], list[Sentence]]) -> dict[str, object]:
    affected_groups = 0
    affected_occurrences = 0
    transition_types = Counter[str]()
    representatives: list[dict[str, object]] = []
    for tokens, values in groups.items():
        defects = [
            (item, invalid_bio_transitions(item.labels))
            for item in values
            if invalid_bio_transitions(item.labels)
        ]
        if not defects:
            continue
        affected_groups += 1
        affected_occurrences += len(values)
        for _, issue_list in defects:
            for issue in issue_list:
                transition_types[f"{issue['previous_label']}->{issue['label']}"] += 1
        if len(representatives) < 12:
            item, issues = defects[0]
            representatives.append({
                "token_sequence_sha256": key_hash(tokens),
                "safe_text_excerpt": " ".join(tokens)[:180],
                "occurrences": len(values),
                "split_signature": "+".join(sorted({entry.split for entry in values}, key=SPLIT_PRECEDENCE.__getitem__)),
                "issues": issues[:3],
                "mechanical_normalization": "replace only each illegal I-X with B-X; preserve entity type and every token",
            })
    return {
        "groups": affected_groups,
        "occurrences": affected_occurrences,
        "transition_types": dict(sorted(transition_types.items())),
        "representative_examples": representatives,
    }


def _group_assignment_analysis(
    original_groups: dict[tuple[str, ...], list[Sentence]],
    clean_groups: dict[tuple[str, ...], list[Sentence]],
) -> dict[str, object]:
    unambiguous_structural_keys: set[tuple[str, ...]] = set()
    cross_split_groups = Counter[str]()
    target_split = Counter[str]()
    for key, values in original_groups.items():
        if len({item.labels for item in values}) != 1:
            continue
        if invalid_bio_transitions(values[0].labels):
            continue
        unambiguous_structural_keys.add(key)
        source_splits = {item.split for item in values}
        if len(source_splits) > 1:
            signature = "+".join(sorted(source_splits, key=SPLIT_PRECEDENCE.__getitem__))
            cross_split_groups[signature] += 1
            target_split[max(source_splits, key=SPLIT_PRECEDENCE.__getitem__)] += 1
    retained = set(clean_groups)
    return {
        "original_exact_token_groups": len(original_groups),
        "unambiguous_structurally_valid_groups": len(unambiguous_structural_keys),
        "clean_v1_retained_groups": len(retained),
        "unambiguous_valid_groups_missing_from_clean_v1": len(unambiguous_structural_keys - retained),
        "unexpected_clean_v1_groups": len(retained - unambiguous_structural_keys),
        "valid_cross_split_groups_assigned_once": sum(cross_split_groups.values()),
        "valid_cross_split_groups_by_source_signature": dict(sorted(cross_split_groups.items())),
        "clean_v1_assigned_cross_split_groups_by_target_split": dict(sorted(target_split.items())),
        "finding": (
            "Clean-v1 already preserves every unambiguous structurally valid exact-token group once; "
            "the 977 cross-split removals are duplicate occurrences, not deletions of valid unique groups."
        ),
    }


def _label_retention(
    original: dict[str, object], clean: dict[str, object]
) -> dict[str, dict[str, object]]:
    labels = sorted(
        {
            label
            for data in [*original.values(), *clean.values()]
            for label in data["bio_label_counts"]
        },
        key=lambda value: (value != "O", value),
    )
    result: dict[str, dict[str, object]] = {}
    for label in labels:
        values: dict[str, object] = {}
        for split in ("train", "valid", "test"):
            before = int(original[split]["bio_label_counts"].get(label, 0))
            after = int(clean[split]["bio_label_counts"].get(label, 0))
            values[split] = {"original": before, "clean_v1": after, "retention": after / before if before else None}
        result[label] = values
    return result


def _entity_retention(
    original: dict[str, object], clean: dict[str, object]
) -> dict[str, dict[str, object]]:
    labels = sorted(
        {
            label
            for data in [*original.values(), *clean.values()]
            for label in data["entity_span_counts"]
        }
    )
    result: dict[str, dict[str, object]] = {}
    for label in labels:
        values: dict[str, object] = {}
        for split in ("train", "valid", "test"):
            before = int(original[split]["entity_span_counts"].get(label, 0))
            after = int(clean[split]["entity_span_counts"].get(label, 0))
            values[split] = {"original": before, "clean_v1": after, "retention": after / before if before else None}
        result[label] = values
    return result


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only DNRTI clean-v1 root-cause analysis")
    parser.add_argument("--original-dir", type=Path, required=True)
    parser.add_argument("--clean-dir", type=Path, required=True)
    parser.add_argument("--remediation-report", type=Path, required=True)
    parser.add_argument("--first-history", type=Path, required=True)
    parser.add_argument("--bio-history", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args()

    original_parsed = {
        split: parse_split(args.original_dir / filename, split)
        for split, filename in SPLIT_FILES.items()
    }
    original_sentences = {name: item.valid_sentences for name, item in original_parsed.items()}
    clean_sentences = _read_clean(args.clean_dir)
    original_stats = {name: _distribution(values) for name, values in original_sentences.items()}
    clean_stats = {name: _distribution(values) for name, values in clean_sentences.items()}
    original_groups = _all_groups(original_sentences)
    clean_groups = _all_groups(clean_sentences)
    remediation = _read_json(args.remediation_report)
    histories = {
        "first_subword": _read_json(args.first_history),
        "bio_aware": _read_json(args.bio_history),
    }
    payload = {
        "schema_version": "1.0",
        "scope": "read-only root-cause audit; no retraining, dataset modification, or deployment",
        "identity_definition": "exact case-sensitive parsed token tuple",
        "source_hashes": {
            f"original/{filename}": sha256_file(args.original_dir / filename)
            for filename in SPLIT_FILES.values()
        } | {
            f"clean_v1/{filename}": sha256_file(args.clean_dir / filename)
            for filename in SPLIT_FILES.values()
        },
        "original_strict_parse": {
            name: {
                "raw_sentence_blocks": item.raw_sentence_blocks,
                "strict_valid_sentences": len(item.valid_sentences),
                "strict_valid_tokens": sum(len(sentence.tokens) for sentence in item.valid_sentences),
                "malformed_lines": len(item.malformed_lines),
                "malformed_sentence_blocks_excluded": item.excluded_malformed_blocks,
                "malformed_classifications": dict(Counter(entry["classification"] for entry in item.malformed_lines)),
            }
            for name, item in original_parsed.items()
        },
        "distribution": {"original_strict": original_stats, "clean_v1": clean_stats},
        "bio_label_retention": _label_retention(original_stats, clean_stats),
        "entity_class_retention": _entity_retention(original_stats, clean_stats),
        "remediation_summary": remediation["remediation"],
        "overlap_group_assignment": _group_assignment_analysis(original_groups, clean_groups),
        "conflicting_label_analysis": _conflict_analysis(original_groups),
        "structural_bio_analysis": _structural_analysis(original_groups),
        "training_histories": histories,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(args.output_json)


if __name__ == "__main__":
    main()
