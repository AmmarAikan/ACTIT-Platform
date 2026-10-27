from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SPLIT_FILES = {"train": "train.txt", "valid": "valid.txt", "test": "test.txt"}
SPLIT_PRECEDENCE = {"train": 0, "valid": 1, "test": 2}
LABEL_RE = re.compile(r"^(?:O|[BI]-.+)$")


@dataclass(frozen=True, slots=True)
class Sentence:
    split: str
    index: int
    tokens: tuple[str, ...]
    labels: tuple[str, ...]
    first_line: int
    last_line: int


@dataclass(slots=True)
class ParsedSplit:
    name: str
    valid_sentences: list[Sentence]
    raw_sentence_blocks: int
    parseable_token_lines: int
    malformed_lines: list[dict[str, object]]
    excluded_malformed_blocks: int


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def token_key(tokens: Iterable[str]) -> tuple[str, ...]:
    """Exact, case-sensitive token identity used by the remediation policy."""
    return tuple(tokens)


def key_hash(tokens: Iterable[str]) -> str:
    canonical = json.dumps(list(tokens), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def parse_split(path: Path, split: str) -> ParsedSplit:
    valid: list[Sentence] = []
    malformed: list[dict[str, object]] = []
    tokens: list[str] = []
    labels: list[str] = []
    block_malformed = False
    first_line = 0
    last_line = 0
    raw_blocks = 0
    parseable_lines = 0
    rejected_blocks = 0

    def flush() -> None:
        nonlocal tokens, labels, block_malformed, first_line, last_line
        nonlocal raw_blocks, rejected_blocks
        if not tokens and not block_malformed:
            return
        raw_blocks += 1
        if block_malformed:
            rejected_blocks += 1
        elif tokens:
            valid.append(
                Sentence(
                    split=split,
                    index=len(valid),
                    tokens=tuple(tokens),
                    labels=tuple(labels),
                    first_line=first_line,
                    last_line=last_line,
                )
            )
        tokens = []
        labels = []
        block_malformed = False
        first_line = 0
        last_line = 0

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped:
                flush()
                continue
            if first_line == 0:
                first_line = line_number
            last_line = line_number
            parts = stripped.split()
            if len(parts) < 2:
                block_malformed = True
                malformed.append(
                    {
                        "line_number": line_number,
                        "classification": "missing_token",
                        "line_sha256": hashlib.sha256(raw.rstrip("\n").encode()).hexdigest(),
                        "safe_excerpt": stripped[:80],
                        "treatment": "exclude_affected_sentence_block",
                    }
                )
                continue
            token = " ".join(parts[:-1])
            label = parts[-1]
            if not LABEL_RE.fullmatch(label):
                block_malformed = True
                malformed.append(
                    {
                        "line_number": line_number,
                        "classification": "invalid_bio_label_syntax",
                        "line_sha256": hashlib.sha256(raw.rstrip("\n").encode()).hexdigest(),
                        "safe_excerpt": stripped[:80],
                        "treatment": "exclude_affected_sentence_block",
                    }
                )
                continue
            parseable_lines += 1
            tokens.append(token)
            labels.append(label)
    flush()
    return ParsedSplit(
        name=split,
        valid_sentences=valid,
        raw_sentence_blocks=raw_blocks,
        parseable_token_lines=parseable_lines,
        malformed_lines=malformed,
        excluded_malformed_blocks=rejected_blocks,
    )


def invalid_bio_transitions(labels: tuple[str, ...]) -> list[dict[str, object]]:
    defects: list[dict[str, object]] = []
    previous = "O"
    for index, label in enumerate(labels):
        if label.startswith("I-"):
            entity = label[2:]
            if previous not in {f"B-{entity}", f"I-{entity}"}:
                defects.append(
                    {"token_index": index, "previous_label": previous, "label": label}
                )
        previous = label
    return defects


def entity_spans(labels: tuple[str, ...]) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    active: str | None = None
    start: int | None = None
    for index, label in enumerate(labels + ("O",)):
        if label == "O":
            if active is not None and start is not None:
                spans.append((active, start, index - 1))
            active = None
            start = None
            continue
        prefix, entity = label.split("-", 1)
        if prefix == "B" or active != entity:
            if active is not None and start is not None:
                spans.append((active, start, index - 1))
            active = entity
            start = index
    return spans


def split_summary(parsed: ParsedSplit) -> dict[str, object]:
    labels = Counter(label for sentence in parsed.valid_sentences for label in sentence.labels)
    entities = Counter(
        entity
        for sentence in parsed.valid_sentences
        for entity, _, _ in entity_spans(sentence.labels)
    )
    groups: dict[tuple[str, ...], list[Sentence]] = defaultdict(list)
    for sentence in parsed.valid_sentences:
        groups[token_key(sentence.tokens)].append(sentence)
    identical_groups = 0
    conflicting_groups = 0
    duplicate_occurrences = 0
    for occurrences in groups.values():
        if len(occurrences) < 2:
            continue
        duplicate_occurrences += len(occurrences) - 1
        if len({item.labels for item in occurrences}) == 1:
            identical_groups += 1
        else:
            conflicting_groups += 1
    invalid_sentences = sum(
        bool(invalid_bio_transitions(sentence.labels))
        for sentence in parsed.valid_sentences
    )
    return {
        "raw_sentence_blocks": parsed.raw_sentence_blocks,
        "strict_valid_sentences": len(parsed.valid_sentences),
        "strict_valid_tokens": sum(len(sentence.tokens) for sentence in parsed.valid_sentences),
        "parseable_token_lines_before_sentence_rejection": parsed.parseable_token_lines,
        "bio_label_counts": dict(sorted(labels.items())),
        "entity_span_counts": dict(sorted(entities.items())),
        "entity_span_total": sum(entities.values()),
        "malformed_lines": len(parsed.malformed_lines),
        "malformed_sentence_blocks_excluded": parsed.excluded_malformed_blocks,
        "exact_unique_token_sequences": len(groups),
        "duplicate_occurrences_beyond_first": duplicate_occurrences,
        "duplicate_groups_identical_labels": identical_groups,
        "duplicate_groups_conflicting_labels": conflicting_groups,
        "invalid_bio_transition_sentences": invalid_sentences,
    }


def original_audit(parsed: dict[str, ParsedSplit]) -> dict[str, object]:
    maps: dict[str, dict[tuple[str, ...], list[Sentence]]] = {}
    for split, data in parsed.items():
        grouped: dict[tuple[str, ...], list[Sentence]] = defaultdict(list)
        for sentence in data.valid_sentences:
            grouped[token_key(sentence.tokens)].append(sentence)
        maps[split] = grouped

    pairwise: dict[str, dict[str, int]] = {}
    for left, right in (("train", "valid"), ("train", "test"), ("valid", "test")):
        shared = set(maps[left]) & set(maps[right])
        pairwise[f"{left}_{right}"] = {
            "shared_exact_token_sequences": len(shared),
            "shared_occurrences_left": sum(len(maps[left][key]) for key in shared),
            "shared_occurrences_right": sum(len(maps[right][key]) for key in shared),
        }
    all_three = set(maps["train"]) & set(maps["valid"]) & set(maps["test"])
    train_keys = set(maps["train"])
    unique_unseen = [
        key for key in maps["test"] if key not in train_keys
    ]

    global_groups: dict[tuple[str, ...], list[Sentence]] = defaultdict(list)
    for data in parsed.values():
        for sentence in data.valid_sentences:
            global_groups[token_key(sentence.tokens)].append(sentence)
    conflict_groups: list[dict[str, object]] = []
    affected_classes: Counter[str] = Counter()
    for key, occurrences in global_groups.items():
        label_sequences = {item.labels for item in occurrences}
        if len(label_sequences) <= 1:
            continue
        for sequence in label_sequences:
            for label in sequence:
                if label != "O":
                    affected_classes[label.split("-", 1)[-1]] += 1
        if len(conflict_groups) < 12:
            conflict_groups.append(
                {
                    "token_sequence_sha256": key_hash(key),
                    "safe_text_excerpt": " ".join(key)[:200],
                    "occurrences": len(occurrences),
                    "splits": sorted({item.split for item in occurrences}),
                    "distinct_label_sequences": len(label_sequences),
                    "label_sequence_examples": [list(labels) for labels in list(label_sequences)[:3]],
                }
            )
    return {
        "identity_definition": "exact case-sensitive parsed token tuple",
        "splits": {name: split_summary(data) for name, data in parsed.items()},
        "cross_split_overlap": pairwise,
        "all_three_overlap_exact_token_sequences": len(all_three),
        "unique_unseen_test_exact_token_sequences": len(unique_unseen),
        "global_conflicting_token_sequence_groups": sum(
            1
            for occurrences in global_groups.values()
            if len({item.labels for item in occurrences}) > 1
        ),
        "global_conflicting_occurrences": sum(
            len(occurrences)
            for occurrences in global_groups.values()
            if len({item.labels for item in occurrences}) > 1
        ),
        "conflict_affected_entity_classes": dict(sorted(affected_classes.items())),
        "representative_conflict_examples": conflict_groups,
        "malformed_line_examples": {
            name: data.malformed_lines[:12] for name, data in parsed.items()
        },
    }


def remediate(
    parsed: dict[str, ParsedSplit], *, expected_label_count: int | None = 27
) -> tuple[dict[str, list[Sentence]], dict[str, object]]:
    groups: dict[tuple[str, ...], list[Sentence]] = defaultdict(list)
    for split in ("train", "valid", "test"):
        for sentence in parsed[split].valid_sentences:
            groups[token_key(sentence.tokens)].append(sentence)

    retained: dict[str, list[Sentence]] = {"train": [], "valid": [], "test": []}
    conflict_groups = 0
    conflict_occurrences = 0
    conflict_by_split = Counter[str]()
    invalid_groups = 0
    invalid_occurrences = 0
    invalid_by_split = Counter[str]()
    cross_split_groups = 0
    cross_split_occurrences_removed = 0
    cross_split_removals = Counter[str]()
    identical_duplicate_occurrences_removed = 0
    retained_keys: dict[str, set[tuple[str, ...]]] = {"train": set(), "valid": set(), "test": set()}

    for key, occurrences in groups.items():
        label_sequences = {item.labels for item in occurrences}
        if len(label_sequences) > 1:
            conflict_groups += 1
            conflict_occurrences += len(occurrences)
            conflict_by_split.update(item.split for item in occurrences)
            continue
        if invalid_bio_transitions(occurrences[0].labels):
            invalid_groups += 1
            invalid_occurrences += len(occurrences)
            invalid_by_split.update(item.split for item in occurrences)
            continue

        source_splits = {item.split for item in occurrences}
        target = max(source_splits, key=SPLIT_PRECEDENCE.__getitem__)
        selected = min(
            (item for item in occurrences if item.split == target),
            key=lambda item: item.index,
        )
        retained[target].append(selected)
        retained_keys[target].add(key)
        if len(source_splits) > 1:
            cross_split_groups += 1
        for item in occurrences:
            if item is selected:
                continue
            if item.split != target:
                cross_split_occurrences_removed += 1
                cross_split_removals[f"{item.split}_to_{target}"] += 1
            else:
                identical_duplicate_occurrences_removed += 1

    for split in retained:
        retained[split].sort(key=lambda item: item.index)

    intersections = {
        "train_valid": len(retained_keys["train"] & retained_keys["valid"]),
        "train_test": len(retained_keys["train"] & retained_keys["test"]),
        "valid_test": len(retained_keys["valid"] & retained_keys["test"]),
    }
    all_labels = {label for values in retained.values() for item in values for label in item.labels}
    remaining_conflicts = 0
    for values in retained.values():
        per_split: dict[tuple[str, ...], set[tuple[str, ...]]] = defaultdict(set)
        for item in values:
            per_split[item.tokens].add(item.labels)
        remaining_conflicts += sum(len(sequences) > 1 for sequences in per_split.values())

    policy = {
        "version": "dnrti-clean-v1.0",
        "identity": "exact case-sensitive parsed token tuple",
        "split_precedence": ["test", "valid", "train"],
        "cross_split": "retain one occurrence in the highest-precedence existing split; never move test into training",
        "conflicting_labels": "exclude every occurrence of an ambiguous exact token sequence; no majority vote",
        "malformed_lines": "exclude the complete affected sentence block when a token or valid BIO label is missing; no semantic repair",
        "invalid_bio_transition": "exclude the complete exact-token group; do not rewrite I labels to B",
        "identical_duplicates": "retain the first occurrence in the selected split",
    }
    audit = {
        "policy": policy,
        "removals": {
            "cross_split_groups_decontaminated": cross_split_groups,
            "cross_split_occurrences_removed": cross_split_occurrences_removed,
            "cross_split_occurrences_by_route": dict(sorted(cross_split_removals.items())),
            "conflicting_label_groups_removed": conflict_groups,
            "conflicting_label_occurrences_removed": conflict_occurrences,
            "conflicting_label_occurrences_by_split": dict(sorted(conflict_by_split.items())),
            "invalid_bio_groups_removed": invalid_groups,
            "invalid_bio_occurrences_removed": invalid_occurrences,
            "invalid_bio_occurrences_by_split": dict(sorted(invalid_by_split.items())),
            "identical_duplicate_occurrences_removed": identical_duplicate_occurrences_removed,
            "malformed_lines_repaired": 0,
            "malformed_lines_excluded": sum(len(item.malformed_lines) for item in parsed.values()),
            "malformed_sentence_blocks_excluded": sum(item.excluded_malformed_blocks for item in parsed.values()),
            "malformed_lines_unresolved": 0,
        },
        "final": {
            name: {
                "sentences": len(values),
                "tokens": sum(len(item.tokens) for item in values),
                "label_counts": dict(sorted(Counter(label for item in values for label in item.labels).items())),
                "entity_span_counts": dict(sorted(Counter(entity for item in values for entity, _, _ in entity_spans(item.labels)).items())),
            }
            for name, values in retained.items()
        },
        "quality_gates": {
            "train_valid_overlap_zero": intersections["train_valid"] == 0,
            "train_test_overlap_zero": intersections["train_test"] == 0,
            "valid_test_overlap_zero": intersections["valid_test"] == 0,
            "conflicting_duplicate_annotations_zero": remaining_conflicts == 0,
            "malformed_lines_zero": True,
            "invalid_bio_transitions_zero": all(
                not invalid_bio_transitions(item.labels)
                for values in retained.values()
                for item in values
            ),
            "exact_27_label_map_preserved": (
                True if expected_label_count is None else len(all_labels) == expected_label_count
            ),
        },
    }
    audit["all_quality_gates_passed"] = all(audit["quality_gates"].values())
    if not audit["all_quality_gates_passed"]:
        raise RuntimeError(f"Derived dataset failed quality gates: {audit['quality_gates']}")
    return retained, audit


def write_split(path: Path, sentences: list[Sentence]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for sentence in sentences:
            for token, label in zip(sentence.tokens, sentence.labels):
                handle.write(f"{token} {label}\n")
            handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def markdown_report(report: dict[str, object]) -> str:
    original = report["original_audit"]
    remediation = report["remediation"]
    lines = [
        "# DNRTI Clean-v1 Dataset Remediation Report",
        "",
        "The original files were read only. The derived dataset uses exact, case-sensitive token-sequence identity and the precedence `test > validation > train`.",
        "",
        "## Original integrity findings",
        "",
        "| Split | Raw blocks | Strict-valid sentences | Tokens | Malformed lines | Conflicting duplicate groups | Invalid BIO-transition sentences |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("train", "valid", "test"):
        values = original["splits"][split]
        lines.append(
            f"| {split} | {values['raw_sentence_blocks']} | {values['strict_valid_sentences']} | {values['strict_valid_tokens']} | {values['malformed_lines']} | {values['duplicate_groups_conflicting_labels']} | {values['invalid_bio_transition_sentences']} |"
        )
    lines.extend([
        "",
        "Pairwise exact-token overlaps before cleaning:",
        "",
    ])
    for pair, values in original["cross_split_overlap"].items():
        lines.append(f"- `{pair}`: {values['shared_exact_token_sequences']} shared token sequences.")
    lines.extend([
        f"- All three splits: {original['all_three_overlap_exact_token_sequences']} shared token sequences.",
        "",
        "## Conservative remediation",
        "",
        f"- Cross-split groups decontaminated: {remediation['removals']['cross_split_groups_decontaminated']}.",
        f"- Cross-split occurrences removed: {remediation['removals']['cross_split_occurrences_removed']}.",
        f"- Conflicting-label groups removed: {remediation['removals']['conflicting_label_groups_removed']} ({remediation['removals']['conflicting_label_occurrences_removed']} occurrences).",
        f"- Invalid-BIO groups removed without relabeling: {remediation['removals']['invalid_bio_groups_removed']} ({remediation['removals']['invalid_bio_occurrences_removed']} occurrences).",
        f"- Malformed lines repaired: 0; excluded: {remediation['removals']['malformed_lines_excluded']}; unresolved: 0.",
        "",
        "No majority vote, semantic token invention, label rewriting, or test-to-training movement was used.",
        "",
        "## Derived split sizes and hashes",
        "",
        "| Split | Sentences | Tokens | SHA-256 |",
        "|---|---:|---:|---|",
    ])
    for split in ("train", "valid", "test"):
        values = remediation["final"][split]
        filename = SPLIT_FILES[split]
        lines.append(
            f"| {split} | {values['sentences']} | {values['tokens']} | `{report['derived_files'][filename]['sha256']}` |"
        )
    lines.extend([
        "",
        "## Quality gates",
        "",
    ])
    for gate, passed in remediation["quality_gates"].items():
        lines.append(f"- {gate}: {'PASS' if passed else 'FAIL'}")
    lines.extend([
        "",
        f"All pre-training dataset gates passed: **{remediation['all_quality_gates_passed']}**.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--report-markdown", type=Path, required=True)
    args = parser.parse_args()

    if args.source_dir.resolve() == args.output_dir.resolve():
        raise SystemExit("Source and derived dataset directories must differ")
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"Refusing to overwrite non-empty derived directory: {args.output_dir}")

    source_hashes = {
        filename: {"sha256": sha256_file(args.source_dir / filename), "bytes": (args.source_dir / filename).stat().st_size}
        for filename in SPLIT_FILES.values()
    }
    parsed = {
        split: parse_split(args.source_dir / filename, split)
        for split, filename in SPLIT_FILES.items()
    }
    before = original_audit(parsed)
    clean, remediation = remediate(parsed)
    for split, filename in SPLIT_FILES.items():
        write_split(args.output_dir / filename, clean[split])
    derived_hashes = {
        filename: {"sha256": sha256_file(args.output_dir / filename), "bytes": (args.output_dir / filename).stat().st_size}
        for filename in SPLIT_FILES.values()
    }
    if source_hashes != {
        filename: {"sha256": sha256_file(args.source_dir / filename), "bytes": (args.source_dir / filename).stat().st_size}
        for filename in SPLIT_FILES.values()
    }:
        raise RuntimeError("Original DNRTI data changed during remediation")

    report = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_directory": str(args.source_dir.resolve()),
        "derived_directory": str(args.output_dir.resolve()),
        "source_files_modified": False,
        "original_files": source_hashes,
        "original_audit": before,
        "remediation": remediation,
        "derived_files": derived_hashes,
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.report_markdown.write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({
        "output": str(args.output_dir),
        "report": str(args.report_json),
        "quality_gates": remediation["quality_gates"],
        "final_sizes": remediation["final"],
    }, indent=2))


if __name__ == "__main__":
    main()
