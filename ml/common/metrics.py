from __future__ import annotations

from collections import Counter


Entity = tuple[str, int, int]


def extract_bio_entities(labels: list[str]) -> set[Entity]:
    """Convert BIO labels into a set of (entity_type, start, end) spans."""
    entities: set[Entity] = set()
    active_type: str | None = None
    start: int | None = None

    def close(end_index: int) -> None:
        nonlocal active_type, start
        if active_type is not None and start is not None:
            entities.add((active_type, start, end_index))
        active_type = None
        start = None

    for index, label in enumerate(labels + ["O"]):
        if label == "O" or not label:
            close(index - 1)
            continue

        if "-" in label:
            prefix, entity_type = label.split("-", 1)
        else:
            prefix, entity_type = "B", label

        if prefix == "B":
            close(index - 1)
            active_type = entity_type
            start = index
        elif prefix == "I":
            if active_type != entity_type:
                close(index - 1)
                active_type = entity_type
                start = index
        else:
            close(index - 1)
            active_type = entity_type
            start = index

    return entities


def entity_micro_metrics(
    true_sequences: list[list[str]],
    pred_sequences: list[list[str]],
) -> dict[str, float | int]:
    tp = 0
    fp = 0
    fn = 0

    for true_labels, pred_labels in zip(true_sequences, pred_sequences):
        true_entities = extract_bio_entities(true_labels)
        pred_entities = extract_bio_entities(pred_labels)
        tp += len(true_entities & pred_entities)
        fp += len(pred_entities - true_entities)
        fn += len(true_entities - pred_entities)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "entity_precision": precision,
        "entity_recall": recall,
        "entity_f1": f1,
        "entity_true_positives": tp,
        "entity_false_positives": fp,
        "entity_false_negatives": fn,
    }


def entity_metrics_by_type(
    true_sequences: list[list[str]],
    pred_sequences: list[list[str]],
) -> dict[str, dict[str, float | int]]:
    """Return exact-span precision, recall, and F1 for each BIO entity type."""
    counts: dict[str, dict[str, int]] = {}

    def bucket(entity_type: str) -> dict[str, int]:
        return counts.setdefault(entity_type, {"tp": 0, "fp": 0, "fn": 0})

    for true_labels, pred_labels in zip(true_sequences, pred_sequences):
        true_entities = extract_bio_entities(true_labels)
        pred_entities = extract_bio_entities(pred_labels)
        for entity_type, _, _ in true_entities & pred_entities:
            bucket(entity_type)["tp"] += 1
        for entity_type, _, _ in pred_entities - true_entities:
            bucket(entity_type)["fp"] += 1
        for entity_type, _, _ in true_entities - pred_entities:
            bucket(entity_type)["fn"] += 1

    metrics: dict[str, dict[str, float | int]] = {}
    for entity_type, values in sorted(counts.items()):
        tp, fp, fn = values["tp"], values["fp"], values["fn"]
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        metrics[entity_type] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
        }
    return metrics


def entity_macro_metrics(
    per_type: dict[str, dict[str, float | int]],
) -> dict[str, float | int]:
    """Average entity metrics across types that have ground-truth support."""
    supported = [values for values in per_type.values() if int(values.get("support", 0)) > 0]
    if not supported:
        return {
            "entity_macro_precision": 0.0,
            "entity_macro_recall": 0.0,
            "entity_macro_f1": 0.0,
            "entity_types_with_support": 0,
        }
    return {
        "entity_macro_precision": sum(float(item["precision"]) for item in supported)
        / len(supported),
        "entity_macro_recall": sum(float(item["recall"]) for item in supported)
        / len(supported),
        "entity_macro_f1": sum(float(item["f1"]) for item in supported) / len(supported),
        "entity_types_with_support": len(supported),
    }


def detailed_entity_metrics(
    true_sequences: list[list[str]],
    pred_sequences: list[list[str]],
) -> dict[str, object]:
    per_type = entity_metrics_by_type(true_sequences, pred_sequences)
    return {
        "micro": entity_micro_metrics(true_sequences, pred_sequences),
        "macro": entity_macro_metrics(per_type),
        "per_type": per_type,
        "token_accuracy": token_accuracy(true_sequences, pred_sequences),
    }


def token_accuracy(true_sequences: list[list[str]], pred_sequences: list[list[str]]) -> float:
    total = 0
    correct = 0
    for true_labels, pred_labels in zip(true_sequences, pred_sequences):
        for true_label, pred_label in zip(true_labels, pred_labels):
            total += 1
            if true_label == pred_label:
                correct += 1
    return correct / total if total else 0.0


def token_micro_metrics(
    true_sequences: list[list[str]],
    pred_sequences: list[list[str]],
    *,
    excluded_labels: set[str] | None = None,
) -> dict[str, float | int | list[str]]:
    """Return single-label token micro metrics for a declared label scope.

    When ``excluded_labels`` contains ``"O"``, an incorrect non-O label is
    both a false positive for the predicted class and a false negative for the
    true class. This is the standard micro aggregation across the retained
    one-vs-rest classes and prevents the dominant O class from inflating the
    entity-token score.
    """
    excluded = excluded_labels or set()
    tp = 0
    fp = 0
    fn = 0
    support = 0
    predicted_positive = 0
    evaluated_tokens = 0

    for true_labels, pred_labels in zip(true_sequences, pred_sequences):
        if len(true_labels) != len(pred_labels):
            raise ValueError("Token metric sequences must have matching lengths")
        for true_label, pred_label in zip(true_labels, pred_labels):
            evaluated_tokens += 1
            true_in_scope = true_label not in excluded
            pred_in_scope = pred_label not in excluded
            support += int(true_in_scope)
            predicted_positive += int(pred_in_scope)
            if true_label == pred_label and true_in_scope:
                tp += 1
            elif true_label != pred_label:
                fp += int(pred_in_scope)
                fn += int(true_in_scope)

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "token_precision": precision,
        "token_recall": recall,
        "token_f1": f1,
        "token_true_positives": tp,
        "token_false_positives": fp,
        "token_false_negatives": fn,
        "support": support,
        "predicted_positive": predicted_positive,
        "evaluated_tokens": evaluated_tokens,
        "excluded_labels": sorted(excluded),
    }


def detailed_token_metrics(
    true_sequences: list[list[str]], pred_sequences: list[list[str]]
) -> dict[str, object]:
    """Report comparable all-class and O-excluded word-token metrics."""
    return {
        "all_classes_micro": token_micro_metrics(true_sequences, pred_sequences),
        "excluding_o_micro": token_micro_metrics(
            true_sequences, pred_sequences, excluded_labels={"O"}
        ),
        "token_accuracy": token_accuracy(true_sequences, pred_sequences),
    }


def label_counter(sequences: list[list[str]]) -> dict[str, int]:
    counts = Counter(label for sentence in sequences for label in sentence)
    return dict(sorted(counts.items()))
