from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.db.database import Base
from backend.app.db.models import CorrelationRecord, IndicatorRecord, Source, ThreatEvent
from backend.app.pipeline.correlation.correlator import SimpleCorrelator, SimilarityCorrelator
from backend.app.services.pipeline_service import PipelineService


def indicator(indicator_type: str, value: str):
    return SimpleNamespace(indicator_type=indicator_type, value=value)


def event(event_id: str, *indicators, text: str = ""):
    return SimpleNamespace(
        id=event_id,
        title=text or event_id,
        description=text,
        normalized_text=text,
        indicators=list(indicators),
    )


def test_indexed_exact_correlation_preserves_pair_type_and_evidence() -> None:
    events = [
        event("a", indicator("domain", "Shared.Example"), indicator("ipv4", "198.51.100.4")),
        event("b", indicator("domain", "shared.example"), indicator("ipv4", "198.51.100.4")),
        event("c", indicator("domain", "shared.example")),
    ]

    results = SimpleCorrelator().correlate(events)

    assert [(item.event_a_id, item.event_b_id, item.reason) for item in results] == [
        ("a", "b", "same_domain"),
        ("a", "b", "same_ipv4"),
        ("a", "c", "same_domain"),
        ("b", "c", "same_domain"),
    ]
    assert results[0].evidence == {"indicator_type": "domain", "values": ["shared.example"]}


def test_indexed_exact_correlation_handles_large_disjoint_population() -> None:
    events = [event(f"event-{index}", indicator("domain", f"unique-{index}.example")) for index in range(5_000)]
    events[-1].indicators.append(indicator("domain", "shared.example"))
    events[-2].indicators.append(indicator("domain", "shared.example"))

    results = SimpleCorrelator().correlate(events)

    assert len(results) == 1
    assert (results[0].event_a_id, results[0].event_b_id) == ("event-4998", "event-4999")


def test_similarity_uses_bounded_sparse_batches_and_preserves_matches(monkeypatch) -> None:
    calls: list[tuple[int, bool]] = []
    from sklearn.metrics import pairwise

    real = pairwise.cosine_similarity

    def observed(left, right, *, dense_output=True):
        calls.append((left.shape[0], dense_output))
        return real(left, right, dense_output=dense_output)

    monkeypatch.setattr(pairwise, "cosine_similarity", observed)
    events = [event(f"event-{index}", text=f"unique token{index}") for index in range(600)]
    events[0].title = events[0].normalized_text = "shared malicious package domain"
    events[599].title = events[599].normalized_text = "shared malicious package domain"

    results = SimilarityCorrelator(0.9).correlate(events)

    assert any({item.event_a_id, item.event_b_id} == {"event-0", "event-599"} for item in results)
    assert calls
    assert max(size for size, _ in calls) <= SimilarityCorrelator.TFIDF_BATCH_SIZE
    assert all(dense_output is False for _, dense_output in calls)


def test_targeted_service_run_uses_normal_correlation_repository_path() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    external_id = "cti-" + "a" * 24
    internal_id = "cti-" + "b" * 24
    unrelated_id = "cti-" + "c" * 24
    with Session(engine) as session:
        external = Source(name="External", source_type="rss", source_pipeline="external")
        internal = Source(name="Internal", source_type="web_access", source_pipeline="internal")
        session.add_all([external, internal]); session.flush()
        events = [
            ThreatEvent(id=external_id, source_id=external.id, source_record_id="external-1",
                        source_type="rss", source_pipeline="external", title="External report",
                        processing_status="transformed"),
            ThreatEvent(id=internal_id, source_id=internal.id, source_record_id="internal-1",
                        source_type="web_access_session", source_pipeline="internal", title="Internal observation",
                        processing_status="transformed"),
            ThreatEvent(id=unrelated_id, source_id=external.id, source_record_id="external-2",
                        source_type="rss", source_pipeline="external", title="Unrelated report",
                        processing_status="transformed"),
        ]
        session.add_all(events); session.flush()
        session.add_all([
            IndicatorRecord(event_id=external_id, indicator_type="domain", value="shared.example"),
            IndicatorRecord(event_id=internal_id, indicator_type="domain", value="shared.example"),
            IndicatorRecord(event_id=unrelated_id, indicator_type="domain", value="shared.example"),
        ])
        session.commit()

        result = PipelineService(session).run_correlations(
            0.35,
            event_ids=[external_id, internal_id],
        )

        rows = list(session.scalars(select(CorrelationRecord)))
        assert result["events_considered"] == 2
        assert result["simple"] == 1
        assert len(rows) == 1
        assert {rows[0].event_a_id, rows[0].event_b_id} == {external_id, internal_id}
        assert rows[0].correlation_type == "simple_indicator_match"
        assert rows[0].evidence == {"indicator_type": "domain", "values": ["shared.example"]}
        assert session.scalar(select(func.count()).select_from(CorrelationRecord)) == 1
