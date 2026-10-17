# ACTIT production processing and cross-source correlation — final evidence

Evidence timestamp: `2026-10-17T12:15:57Z` through final read-only verification on `2026-10-18`

Scope: real ACTIT production only (`http://127.0.0.1:18080` and `https://cti-gateway-vps.tailf2792f.ts.net`)
Excluded and untouched: the isolated defense-demo stack, port `19090`, demo database, demo fixtures, and demo screenshots.

## A. Baseline

- Original production release: `/opt/cti-platform/releases/20261016T224501Z-committee-access`.
- Original deployment was healthy: root HTTP 200; `/api/v1/health` HTTP 200 with `database=true`.
- Original counts: sources `32`; raw items `29,378`; threat events `21,004`; indicators `36,818`; correlations `9`; pipeline runs `68`; external ingestion operations `46`.
- Original PostgreSQL container: `29d223eb2d9501ad134a18e654855ea4a3852b3361e173a8ece7d77a0d52785c`, started `2026-09-03T14:47:56.252079658Z`.
- Rollback release remains available at `/opt/cti-platform/releases/20261016T224501Z-committee-access`.
- Retained rollback images:
  - Backend `cti-central-backend:rollback-20261016T224501Z-committee-access` → `sha256:03f0355d5e5fee47521a9477c21145ac602df18670d8fdfc534728478041e91a`.
  - Frontend `cti-central-frontend:rollback-20261016T224501Z-committee-access` → `sha256:445e9a87b38170dc504c04249d8804aebdb7099e835d993f3cee8d4332f06a6c`.
  - External Sources `cti-external-sources:rollback-20261016T224501Z-committee-access` → `sha256:4782e04e58cbca263fa5c4c667d4101234dd16b08b6e4769eeaa38503c054134`.
- Before controlled validation, counts were events `21,010`, indicators `36,828`, correlations `9`, internal events `49`, and outlier sessions `476`.
- Narrow logical safety dump: `/opt/cti-platform/backups/production-processing-correlation-20261017T121557Z/pre_controlled_validation_relevant_tables.dump`; mode `0600`; catalog verified; SHA-256 `51c995f2cb933bd396083575c2f8fa49c45fcd498c21ddce7792db88440102b7`.
- Final counts: sources `32`; raw items `29,520`; threat events `21,012`; indicators `36,832`; correlations `11`; pipeline runs `73`; external ingestion operations `49`; outlier sessions `484`; internal events `51`.

## B. Processing Center root cause and repair

The failure had three linked causes, proven from production configuration, API responses, durable-operation state, database state, and the current export contents:

1. Production Backend did not receive `EXTERNAL_FEED_PUBLISH_TOKEN`. Exact-export publication therefore raised `external_feed_publish_not_configured`, leaving durable operations `failed_retryable` at `export_ready`.
2. The frontend translated every operation HTTP 409 into the stale/consumed-preview sentence, hiding the actual ingestion failure.
3. Registered single-source export construction appended active Manual URL history to the current source job. CERT-EU had five current accepted records but exported 33; zero-result CISA and CERT-AT runs each exported 28 historical records. This violated the current-run exact-export contract.

The repair:

- Registered single-source exports now contain only records from that current command/run.
- Central rejects zero-new and incomplete source exports instead of importing historical data.
- Creating an operation returns an existing durable operation without an implicit retry; only the supported retry endpoint restarts a retryable operation.
- Processing Center distinguishes preview conflicts from ingestion failures, clears run/export/preview/operation state immediately when the input changes, prevents duplicate submission, resumes the same durable operation, and renders a truthful no-new-data completion.
- The deployment path securely loads the existing root-only Gateway publish credential into Backend without printing it.
- Correlation execution was additionally made production-safe through indexed exact matching, 256-row sparse TF-IDF batches, indexed Jaccard fallback, and a validated/audited 2–100 `event_ids` scope on the normal route. No threshold, score, or evidence was weakened or edited.

Files changed are represented by commits `6b1b10803171495dcd97ce06966f31e47037fe07`, `246dbd1000610d860e7de895e018fc36d2b98d74`, and `490409ca24c72caeda867fac9ee69ea3604098a9`.

Contaminated historical operations were preserved for audit and never retried: `9cc6e416-de78-4575-ad09-63ae7d4580f8`, `df2be6f4-8a56-4fee-9ce9-907553068b03`, and `520f1d51-d540-45aa-8781-0a6b86a30848`.

## C. Three real external sources

Deployed source truth:

- CISA: `cisa-advisories`, RSS `https://www.cisa.gov/cybersecurity-advisories/all.xml`, enabled, maximum 50, 30-day lookback, with the supported bounded official CSAF fallback.
- CERT-EU: `cert-eu-advisories`, RSS `https://cert.europa.eu/publications/security-advisories-rss`, enabled, maximum 50, 30-day lookback.
- CERT-AT: `cert-at-warnings`, RSS `https://www.cert.at/cert-at.de.warnings.rss_2.0.xml`, enabled, maximum 50, 30-day lookback.

### CISA — UNCHANGED

- Job: `job-360f65d33775fab52a246c4d`.
- Run/export: `ext-20261017T121231Z-d6879410fa1b`.
- Export digest: `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`.
- Supported official CSAF fallback was used; no unauthorized proxy or provider bypass was used.
- Counts: accepted `0`, review `0`, skipped `44`, non-retryable `csaf_mapping_invalid` rejects `6`.
- The exact current export contained zero records. No ingestion operation was created. Accepted Records remained `3`; CISA event count remained `3`.
- Classification: `UNCHANGED`. The six mapping rejects are recorded under limitations; no stale-preview or ingestion lifecycle failure occurred.

### CERT-EU — SUCCESS

- Job: `job-7555b69b160d3cef04126979`.
- Run/export: `ext-20261017T121339Z-30c6392f1138`.
- Export digest: `38b30f601a367c3685427290cd49402991bee629ffcba3974c02ddd869436f62`.
- Counts: accepted `5`, skipped `5`, errors `0`.
- Durable operation: `2bcd89d0-2ec9-42e4-a0d3-10129228f423`; pipeline run `0f88e7a4-dfbb-4103-96aa-4e97a341bca1`.
- State: completed on attempt `1`; exported/acknowledged `5`, created `2`, unchanged `3`, failed `0`.
- Accepted Records delta: `6 → 8`.
- Duplicate create, resume, and retry-after-completion returned the same operation at attempt 1; no second import occurred.
- Classification: `SUCCESS`.

### CERT-AT — UNCHANGED

- Job: `job-89c85789c3fd4c9caea25cd9`.
- Run/export: `ext-20261017T121533Z-34ace31697db`.
- Export digest: `37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570`.
- Counts: accepted/review/skipped/errors all `0`.
- The exact current export contained zero records. No ingestion operation was created. Accepted Records remained `4`; CERT-AT event count remained `4`.
- Classification: `UNCHANGED`.

These results prove the current-run export contract: both zero-new sources terminated cleanly with no old export fallback, while CERT-EU published and imported exactly its five current records.

## D. Correlation 1

- External source: BleepingComputer.
- External event: `cti-eb4822def09fab0efe9913e8`, “Ninja Forms plugin flaw exploited to hack WordPress sites”.
- External indicator: `d284f8c4-049f-44f6-b35c-f028f7c1ff05`, domain `imgcdn1.com`.
- Internal source: VPS Gateway Access (`web_access_session`, pipeline `internal`).
- Internal event: `cti-2ddd067542021f125690f660`, “Internal web access session event”.
- Internal indicator: `4a752f98-f3da-499d-aa68-b136287eba71`, domain `imgcdn1.com`.
- Internal run: `53335a4e-9754-4b7d-8ae1-83c21365bec5`; collected `16`, sessions `4`, outliers `1`, events `1`, failures `0`.
- Correlation: `46bd1006-d88c-4907-9a7b-5b16fc5bd6fa`.
- Type/method: `simple_indicator_match`; reason `same_domain`.
- Score `1.0`; score basis `exact_observable_match`; evidence status `available`; `cross_source=true`.
- Evidence factor: shared observable / domain / `imgcdn1.com`.
- Created at `2026-10-17T12:47:05.231859Z`.

## E. Correlation 2

- External source: The Hacker News.
- External event: `cti-fcaf9a4ab7b310cf83086efd`, “13 Malicious Packagist Packages Target Unpatched iPhones to Steal Crypto Wallet Seeds”.
- External indicator: `cd558901-4019-41ba-93c2-5ff73b9a055f`, domain `cloudfareintcdn.com`.
- Internal source: VPS Gateway Access (`web_access_session`, pipeline `internal`).
- Internal event: `cti-74e7f404bd9cdced6ee6913f`, “Internal web access session event”.
- Internal indicator: `fe05bde3-efae-4318-9ffc-d8e079862619`, domain `cloudfareintcdn.com`.
- Internal run: `a25452dc-25ae-4ac8-a630-77b7324ea410`; collected `13`, sessions `4`, outliers `1`, events `1`, failures `0`.
- Correlation: `796734a7-e159-41a9-a83c-30c0f0ea3cc3`.
- Type/method: `simple_indicator_match`; reason `same_domain`.
- Score `1.0`; score basis `exact_observable_match`; evidence status `available`; `cross_source=true`.
- Evidence factor: shared observable / domain / `cloudfareintcdn.com`.
- Created at `2026-10-17T12:49:29.683928Z`.

The final authenticated API returned `11` total correlations and both selected IDs with the fields above.

## F. Controlled validation provenance

Both internal observations are controlled production validation, not organically observed attacks. The path was:

`local/private HTTP observation → real VPS Gateway web-access log → normal Web Access ingestion → persisted internal ThreatEvent → normal IoC extraction → normal ACTIT correlation`.

The target domains appeared only in the logged path with `validation_origin=controlled_production_validation`. Connections used literal loopback or the private Gateway address `172.21.0.2`; no DNS resolution or connection to either external domain occurred. Temporary private-network baseline containers were removed after their Gateway records were verified. The internal records retain `source_pipeline=internal`, source `VPS Gateway Access`, and the provenance marker in raw alerts. No ThreatEvent, Indicator, or Correlation row was directly inserted or edited.

Each bounded normal correlation run considered exactly the selected external/internal event pair, generated one exact-indicator result, persisted it through the ordinary repository path, generated its evidence, and recalculated both event risks.

## G. Tests

Only actually executed results are reported. Earlier failed dependency/setup and intermediate assertions were not counted as passes.

- Focused Backend/External ingestion:
  - Command: `python3 -m pytest -q tests/test_external_ingestion_operations.py tests/external_sources/integration/test_local_collection_job.py`.
  - Result: `38 passed`, `2 subtests passed`, `1 warning`, `9.97s`.
- Processing Center frontend:
  - Command: `npm test -- --run src/test/external-import-lifecycle.integration.test.tsx src/test/i18n-processing.test.tsx` from `frontend/`.
  - Result: `2` files, `40 passed`, `12.02s`.
- Intelligence/correlation UI:
  - Command/test phase: `npm test -- --run src/test/intelligence.test.tsx` from `frontend/`.
  - Result: `1` file, `16 passed`, `6.74s`. The enclosing chained command later exited nonzero on an unrelated TypeScript unused-variable error; that compile issue was fixed, and the separate lint/build and full-suite executions below passed.
- Full frontend:
  - Command: `npm test -- --run` from `frontend/`.
  - Result: `22` files, `173 passed`, `34.35s`.
- Impacted Backend, External Sources, API, repository, auth/RBAC, Gateway retention, and internal pipeline:
  - Command: `.venv/bin/python -m pytest -q tests/external_sources tests/test_external_control_client.py tests/test_external_ingestion_operations.py tests/test_external_integration_import_boundary.py tests/test_backend_external_feed_batching.py tests/test_backend_api.py tests/test_backend_enhancements.py tests/test_accepted_records_ordering.py tests/test_auth_rate_limit.py tests/test_database_test_isolation.py tests/test_gateway_feed_retention.py tests/test_gateway_web_log_retention.py tests/test_internal_pipeline.py`.
  - Result: `435 passed`, `84 subtests passed`, `23 warnings`, `54.32s`.
- Correlation scale/service regression:
  - Command: `.venv/bin/python -m pytest -q tests/test_correlation_scaling.py`.
  - Final result: `4 passed`, `3.63s`.
  - Coverage includes 5,000 disjoint exact events, sparse batching, evidence equivalence, and targeted repository persistence.
- Frontend lint and production build:
  - Command: `npm run lint && npm run build` from `frontend/`.
  - Result: PASS; Vite build completed in `750ms`.
  - Exact candidate image command: `docker build --pull=false --build-arg VITE_MISP_DELIVERY_DISABLED=false --build-arg VITE_ACTIT_DEMO_MODE=false --build-arg VITE_ACTIT_COMMITTEE_ACCESS=true -t cti-central-frontend:20261017T005114Z-production-processing-correlation-final frontend`.
  - Candidate image build result: lint PASS, `22/22` files and `173/173` tests PASS, Vite production build PASS (`1.38s`).

The attempted combined `tests/test_correlation_scaling.py tests/test_backend_api.py` application fixture produced no completed result and is not claimed. Its required API/RBAC coverage had already passed in the 435-test impacted suite; the new scaling suite passed separately.

## H. Production deployment

- Current release: `/opt/cti-platform/releases/20261017T123914Z-production-processing-correlation-final`.
- `RELEASE_COMMIT`: `490409ca24c72caeda867fac9ee69ea3604098a9`.
- The release tree was verified byte-identical to that commit, excluding the release marker.
- Current Backend: container `76cd4ebfddabceaa7e60cd31caf45a02c73f6137102ac2908bcaa8acbcea47d9`; image `sha256:15260f50bd32d7b9168f6b0ef82e8c1d3a05c95489ad123b73ef7c09a01bb2f2`; running/healthy.
- Current Frontend: container `b269b6be1ce4091102c5907e1ef6cb3ee47df4ba5e77f15ac6dddf6e11f9f4ab`; image `sha256:69141cd7b9f4066355c8f59819afa49ac2dc161196cd542c5f630661af919637`; running/healthy.
- Current External Sources: container `d7179783a0a6db70ab5ae71f5517615423d769e9907a6e54b7a747e0e1da3313`; image `sha256:485b3bb636b1222910c7860e7ae72e1d02e061e7f49501ae7ce944962cf56f68`; running/healthy; health contract returned `service=external-sources`, `api_version=v1`.
- Unchanged PostgreSQL: container `29d223eb2d9501ad134a18e654855ea4a3852b3361e173a8ece7d77a0d52785c`; image `sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777`; running/healthy; original September start time.
- Unchanged Gateway: container `6d74144e4b24c2fa62f35d79e5a1df0de814a0d1518817ebb457e4f9e0cc39b8`; image `sha256:7ceb0a2843da895a74b3c30e02884b6116d8e3894b083afa514c227b5f72ce2f`; running/healthy; health reported feed ready and all three telemetry streams true.
- PostgreSQL, Gateway, MISP, and unrelated services were not recreated or redeployed.
- Final local root and health: HTTP 200.

Rollback procedure is to atomically restore `/opt/cti-platform/current` to `/opt/cti-platform/releases/20261016T224501Z-committee-access`, retag the three retained rollback images to their production `current` tags, and recreate only Backend, Frontend, and External Sources with the existing production compose/env files. PostgreSQL, Gateway, MISP, and volumes remain untouched. This procedure was verified logically; rollback was not executed because production is healthy.

## I. Browser, HTTPS, Funnel, and committee access

- Exact production hostname: `https://cti-gateway-vps.tailf2792f.ts.net`.
- Authenticated browser validation passed: Landing, Login, public committee card, Viewer dashboard, Viewer read-only Processing Center, Analyst dashboard, Processing & Analysis Center, External Sources, Accepted Records, Events, Correlations, Threat Storyline, MITRE ATT&CK, and System Readiness.
- Correlations displayed both selected Internal ↔ External relationships, both shared domains, source names, method/reason, evidence, and score.
- Browser console/page errors: `0` for public, Viewer, and Analyst contexts.
- Browser evidence: `browser/browser-validation.json`, `browser/correlations-cross-source.png`, `browser/processing-center.png`, `browser/landing.png`, `browser/login-committee-card.png`, and `browser/system-readiness.png` in this evidence directory.
- Committee Viewer: `demo-viewer`, role `viewer`, active; administration endpoint HTTP `403`.
- Committee Analyst: `demo-analyst`, role `analyst`, active; administration endpoint HTTP `403`.
- No Admin credential was created, used, or exposed.
- Final Tailscale version: `1.104.1`.
- Funnel status: public ACTIT on `https://cti-gateway-vps.tailf2792f.ts.net/` to local port `18080`; public MISP on `https://cti-gateway-vps.tailf2792f.ts.net:8443/` to local port `8443`.
- Final public ACTIT: HTTP `200`, TLS verification result `0`.
- Final public MISP: HTTP `200` after the expected redirect to `/users/login`, TLS verification result `0`.
- No Funnel, Serve, MagicDNS, ACL, Tailscale, or MISP setting was changed by this task's finalization phase.

## J. Git and final state

- Branch: `codex/production-processing-correlation-final-20261017`.
- Implementation commits:
  - `6b1b10803171495dcd97ce06966f31e47037fe07` — production external-ingestion lifecycle repair.
  - `246dbd1000610d860e7de895e018fc36d2b98d74` — dependency-stable production patch images.
  - `490409ca24c72caeda867fac9ee69ea3604098a9` — bounded production correlation execution and scaling repair.
- The final evidence commit is the commit containing this report and its production screenshots. At completion, `origin/codex/production-processing-correlation-final-20261017` and `origin/main` were pushed to that same commit without a plain force push; their trees were compared with `git diff --exit-code` and were identical. The literal post-commit ID is recorded in `/root/actit-processing-correlation/LATEST.md`, because a Git commit cannot contain its own hash.
- Production remains on source commit `490409ca24c72caeda867fac9ee69ea3604098a9`; synchronizing Git refs does not require or authorize a redeployment.
- Temporary task authentication/token response files were removed from `/tmp`; no production evidence or data was removed.
- Final worktree status: clean after the evidence commit.

## Remaining limitations

- CISA's supported official CSAF fallback completed, but six provider documents were non-retryably rejected as `csaf_mapping_invalid`; the run is truthfully classified `UNCHANGED`, not success and not an application lifecycle failure.
- The three pre-repair contaminated durable operations remain preserved for audit and must not be retried. They do not affect the clean post-repair operations.
- Full unscoped correlation over the entire historical corpus is expensive because common observables create millions of candidate pairs. The deployed repair provides indexed/batched algorithms plus the audited bounded event scope used for the two verified production correlations. No selected evidence, threshold, or score was manufactured.

No other open application, health, access, deployment, correlation, or public-ingress limitation was observed in final verification.
