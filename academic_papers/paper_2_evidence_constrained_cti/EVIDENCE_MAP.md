# Evidence Map — Paper 2

| Claim | Local evidence |
|---|---|
| Architecture and trust boundaries | `docs/architecture/cloud_distributed_architecture.md`; `infra/vps/compose.yaml`; `infra/vps/central.compose.yaml` |
| Production acceptance and rollback model | `docs/operations/vps_production_runbook.md` |
| 21 enabled of 22 registered public sources | `config/sources.json` |
| Collection, SSRF, privacy, manual JSON, review, and atomic export behavior | `backend/app/pipeline/ingestion/external/`; corresponding tests under `tests/external_sources/` |
| Pre/post CTI counts and relationship reduction | `Parts Report/CTI_Result_Quality_Audit.md` |
| Prepared 400-document human protocol | `Parts Report/CTI_Live_Evaluation_Protocol.md`; `ml/reports/cti_live_evaluation_preparation.json` |
| 291 passing external-source tests | Fresh command: `python -m unittest discover -s tests/external_sources -p 'test_*.py' -q`, run 2026-10-22 |
| Observable/Indicator and STIX semantics | OASIS STIX 2.1 and OpenCTI references in `references.bib` |
| No claim of human-measured accuracy | Annotation templates remain pending; protocol explicitly blocks fabricated metrics |

No secret, token, private source address, credential, or private collected document is included.
