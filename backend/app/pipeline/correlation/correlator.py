from __future__ import annotations

import re
from dataclasses import dataclass
from itertools import combinations
from typing import Any


@dataclass(slots=True)
class CorrelationCandidate:
    event_a_id: str
    event_b_id: str
    correlation_type: str
    score: float
    reason: str
    evidence: dict[str, Any]


class SimpleCorrelator:
    """MISP-style exact-value correlation across normalized indicators."""

    def correlate(self, events) -> list[CorrelationCandidate]:
        events = list(events)
        observable_index: dict[tuple[str, str], list[int]] = {}
        for event_index, event in enumerate(events):
            for indicator_type, values in self._values(event).items():
                for value in values:
                    observable_index.setdefault((indicator_type, value), []).append(event_index)

        shared_by_pair: dict[tuple[int, int, str], set[str]] = {}
        for (indicator_type, value), event_indices in observable_index.items():
            for left, right in combinations(event_indices, 2):
                shared_by_pair.setdefault((left, right, indicator_type), set()).add(value)

        return [
            CorrelationCandidate(
                event_a_id=events[left].id,
                event_b_id=events[right].id,
                correlation_type="simple_indicator_match",
                score=1.0,
                reason=f"same_{indicator_type}",
                evidence={"indicator_type": indicator_type, "values": sorted(shared)[:20]},
            )
            for (left, right, indicator_type), shared in sorted(shared_by_pair.items())
        ]

    def _values(self, event) -> dict[str, set[str]]:
        values: dict[str, set[str]] = {}
        for indicator in event.indicators:
            values.setdefault(indicator.indicator_type, set()).add(indicator.value.strip().lower())
        return values


class SimilarityCorrelator:
    TFIDF_BATCH_SIZE = 256

    def __init__(self, threshold: float = 0.35) -> None:
        self.threshold = threshold

    def correlate(self, events) -> list[CorrelationCandidate]:
        events = list(events)
        if len(events) < 2:
            return []
        texts = [f"{event.title}\n{event.normalized_text or event.description}" for event in events]
        try:
            matches = self._tfidf_matches(texts)
            backend = "tfidf_cosine"
        except (ImportError, ValueError):
            matches = self._jaccard_matches(texts)
            backend = "token_jaccard_fallback"
        return [
            CorrelationCandidate(
                event_a_id=events[i].id,
                event_b_id=events[j].id,
                correlation_type="text_similarity",
                score=round(score, 6),
                reason="similar_text",
                evidence={"backend": backend, "threshold": self.threshold},
            )
            for i, j, score in matches
        ]

    def _tfidf_matches(self, texts: list[str]) -> list[tuple[int, int, float]]:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        matrix = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=1).fit_transform(texts)
        matches: list[tuple[int, int, float]] = []
        for start in range(0, len(texts), self.TFIDF_BATCH_SIZE):
            end = min(start + self.TFIDF_BATCH_SIZE, len(texts))
            scores = cosine_similarity(matrix[start:end], matrix, dense_output=False).tocoo()
            for row, column, value in zip(scores.row, scores.col, scores.data):
                left = start + int(row)
                right = int(column)
                score = float(value)
                if right <= left or score < self.threshold:
                    continue
                matches.append((left, right, score))
        return sorted(matches)

    def _jaccard_matches(self, texts: list[str]) -> list[tuple[int, int, float]]:
        tokens = [set(re.findall(r"[a-z0-9_.:/-]{3,}", text.lower())) for text in texts]
        if self.threshold <= 0:
            pairs = combinations(range(len(tokens)), 2)
            return [
                (left, right, self._jaccard(tokens[left], tokens[right]))
                for left, right in pairs
            ]

        token_index: dict[str, list[int]] = {}
        for event_index, values in enumerate(tokens):
            for value in values:
                token_index.setdefault(value, []).append(event_index)
        intersections: dict[tuple[int, int], int] = {}
        for event_indices in token_index.values():
            for pair in combinations(event_indices, 2):
                intersections[pair] = intersections.get(pair, 0) + 1
        matches = []
        for (left, right), intersection in intersections.items():
            union_size = len(tokens[left]) + len(tokens[right]) - intersection
            score = intersection / union_size if union_size else 0.0
            if score >= self.threshold:
                matches.append((left, right, score))
        return sorted(matches)

    @staticmethod
    def _jaccard(left: set[str], right: set[str]) -> float:
        union = left | right
        return len(left & right) / len(union) if union else 0.0
