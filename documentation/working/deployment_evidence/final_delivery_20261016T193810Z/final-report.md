# ACTIT final delivery evidence

- Evidence timestamp: `20261016T193810Z`
- Worktree: `/opt/cti-platform/worktrees/final-delivery-20261016`
- Branch: `codex/final-delivery-20261016`
- Rollback baseline: `/opt/cti-platform/releases/20261015T182605Z-six-hour-ui-priority`

## 1. Events root cause

Authenticated `GET /api/v1/intelligence/events` returned HTTP 200 JSON with real stored ACTIT events. The first production event summary was exactly 500 Unicode code points but 504 JavaScript UTF-16 code units. The frontend's strict `requiredText(summary, 500)` check used `value.length`, rejected the valid response, and raised `invalid_response`. The bounded frontend repair uses `Array.from(value).length`; a 501-code-point response remains rejected. No backend intelligence change was required.

## 2. Threat Storyline root cause

Authenticated `GET /api/v1/intelligence/events/{event_id}/storyline` returned HTTP 200 JSON and passed `parseStoryline`. The page failed earlier while its shared event selector parsed `/api/v1/intelligence/events`; therefore it had the same Unicode code-unit mismatch as Events. The shared frontend parser repair restored event selection and real storyline evidence without weakening the storyline contract.

## 3. MITRE ATT&CK root cause

Authenticated `GET /api/v1/intelligence/events/{event_id}/attack` returned HTTP 200 JSON and passed `parseAttackMapping`. The page failed earlier while loading the shared event selector, again because of the event-summary Unicode mismatch. The shared frontend repair restored the selector, supported techniques/candidates, and valid empty states. No ATT&CK fact was synthesized.

## 4. Files changed

The implementation commit contains these 37 reviewed paths:

```text
documentation/working/deployment_evidence/final_delivery_20261016T193810Z/final-report.md
frontend/public/branding/actit-logo-with-text.webp
frontend/public/branding/actit-logo.webp
frontend/src/api/client.ts
frontend/src/brand-identity.css
frontend/src/components/BrandMark.tsx
frontend/src/components/DashboardInvestigation.tsx
frontend/src/components/Layout.tsx
frontend/src/components/PublicFrame.tsx
frontend/src/i18n/I18nContext.tsx
frontend/src/main.tsx
frontend/src/pages/AcceptedRecords.tsx
frontend/src/pages/Dashboard.tsx
frontend/src/pages/InternalSources.tsx
frontend/src/pages/Landing.tsx
frontend/src/pages/Login.tsx
frontend/src/pages/Manual.css
frontend/src/pages/Manual.tsx
frontend/src/pages/ProcessingCenter.tsx
frontend/src/pages/Reviews.tsx
frontend/src/pages/SystemReadiness.tsx
frontend/src/styles.css
frontend/src/test/App.test.tsx
frontend/src/test/admin.test.tsx
frontend/src/test/external-features-api.test.ts
frontend/src/test/external-pages.test.tsx
frontend/src/test/i18n-processing.test.tsx
frontend/src/test/intelligence.test.tsx
frontend/src/test/manual-url.test.tsx
frontend/src/test/system-readiness.test.tsx
frontend/src/test/threat-storyline.test.tsx
scripts/create_demo_dataset.py
scripts/defense_demo.sh
scripts/defense_demo_provider.py
scripts/defense_demo_smoke.py
scripts/final_delivery_visual_check.py
tests/test_demo_dataset.py
```

Relative to the deployed rollback baseline, application changes are limited to the strict parser, requested navigation/readiness/auth/landing UI, their tests, and isolated defense-demo tooling. Production carry-forward files are byte-identical to that baseline and preserve already-deployed branding and prior health/external-ingestion contract repairs.

## 5. Tests executed and results

- Frontend targeted tests: `34/34` PASS; follow-up suite `41/41` PASS.
- Final frontend lint: PASS.
- Final full frontend suite: `22` files, `168/168` PASS.
- Final production-mode Vite build: PASS, `112` modules (`641.15 kB`; size warning only).
- Production bundle inspection: PASS; GitHub URL present, both demo passwords absent.
- Backend API class in isolated backend image with networking disabled and worktree read-only: `20/20` PASS (`11.115s`).
- Demo dataset/provider tests: `7/7` PASS (`5.180s` final rerun).
- One host-side backend loader attempt did not execute because host Python lacks `stix2`; it was replaced by the successful isolated-image run above.
- Defense demo preflight: PASS.
- Defense demo prepare: PASS.
- Defense demo start: PASS after fail-closed preserved-dataset verification was added.
- Expanded defense demo smoke: PASS in both available/empty review modes; final rerun after navigation polish also PASS.
- Desktop visual capture: 14/14 English and Arabic/RTL screenshots captured; zero console/page errors.
- Exact production candidate image build: lint PASS, `22` files / `168/168` tests PASS, and Vite build PASS.
- Exact candidate image standalone HTTP gate: `/` HTTP 200 and `/healthz` HTTP 200 in the production-equivalent network topology.
- Post-deployment authenticated browser/API walkthrough: PASS for all required pages and integrations; zero browser console/page errors.
- Intermediate production-walkthrough attempts stopped only on checker compatibility/timing issues (Playwright init argument, raw-fetch auth header, asynchronous selector wait, and CSP rejection of an eval-based wait). The final locator-based checker passed; none of those attempts exposed an ACTIT application failure.

## 6. Demo user verification

`demo-viewer` authenticates as exact role `viewer` and cannot perform analyst/admin writes. `demo-analyst` authenticates as exact role `analyst`, can access analyst-authorized workflows, and cannot access admin operations. The public credential card exposes only these two accounts and is compiled only when `VITE_ACTIT_DEMO_MODE === 'true'`.

## 7. System Readiness change

The Extraction Model item, ML status request, ML loading/error aggregation, global failure influence, and ML refresh call were removed from System Readiness only. ML backend/API/artifacts and Processing & Analysis Center functionality remain intact.

## 8. Analysis Runs navigation removal

Analysis Runs was removed from sidebar navigation and dashboard/processing shortcuts. Its direct route, backend, and stored history remain available for compatibility/evidence.

## 9. GitHub link placement

The public Landing page contains one bilingual, branded `View source on GitHub` action targeting `https://github.com/AmmarAikan/CTI-Tool` with `target="_blank"`, `rel="noreferrer"`, and an accessible bilingual label.

## 10. Candidate release path

`/opt/cti-platform/releases/20261016T193810Z-final-delivery`, assembled from the immutable rollback baseline with the 37 reviewed commit paths overlaid. `RELEASE_COMMIT` is `d1d9beea53372df8d8b71cfad7c196caed332fde`. Compose configuration validation passed.

## 11. Deployed release path

`/opt/cti-platform/releases/20261016T193810Z-final-delivery` (frontend-only deployment), also the resolved target of `/opt/cti-platform/current`.

## 12. Container and image IDs changed

Before deployment, production frontend was `76e9c918546b` on image `sha256:21d9d2fc...`, backend `73821101f6a9` on `sha256:03f0355d...`, and database `29d223eb2d95` on `sha256:57c72fd2...`. After deployment, frontend is `f5bd5e6e9461` on `sha256:c88761a0734...`; backend and database IDs/images are unchanged. Only frontend was recreated.

## 13. Production health

Pre-deployment and final post-deployment production `/` and `/api/v1/health`: HTTP 200. Frontend container `f5bd5e6e9461`, backend `73821101f6a9`, and database `29d223eb2d95` are all running and healthy.

## 14. Demo health

Final demo `/` and `/api/v1/health`: HTTP 200. Demo frontend `bafda4e3cdfd`, backend `cbdd5e7961cb`, and database `32c789600c60` are healthy. Expanded bilingual smoke and visual checks passed.

## 15. Authenticated page verification

Demo Dashboard, System Readiness, Events, Event Details, Threat Storyline, and MITRE ATT&CK passed in the expanded browser smoke; English and Arabic/RTL evidence was captured.

The final authenticated production walkthrough passed Dashboard, System Readiness, Events, Event Details, Threat Storyline, MITRE ATT&CK, External Sources, Processing & Analysis Center, Accepted Records, Internal Sources, MISP, and Administration with no rendered alerts and zero console/page errors. It also proved that the production login has no demo card, Analysis Runs is absent from normal navigation, and Extraction Model is absent from System Readiness.

Safe browser-equivalent API evidence from the final run:

- `/api/v1/intelligence/events?limit=1&offset=0`: HTTP 200, `application/json`, keys `items, limit, offset, total`, one real stored event.
- `/api/v1/intelligence/events/{event_id}`: HTTP 200, `application/json`, exact event/detail key set accepted.
- `/api/v1/intelligence/events/{event_id}/storyline`: HTTP 200, `application/json`, keys include `risk_method`, `risk_factors`, `risk_context`, `evidence_counts`, `observables`, `entities`, `relationships`, `correlations`, `attack`, `milestones`, `evidence_truncated`, and `limitations`.
- `/api/v1/intelligence/events/{event_id}/attack`: HTTP 200, `application/json`, keys `source, catalog_version, official_dataset_url, event_id, techniques`. The selected event had zero techniques and rendered the supported empty state.

## 16. Rollback target

Rollback target: `/opt/cti-platform/releases/20261015T182605Z-six-hour-ui-priority`. The old frontend image is preserved as `cti-central-frontend:rollback-20261015T182605Z-six-hour-ui-priority` (`sha256:21d9d2fc...`). Exact rollback:

```bash
docker image tag cti-central-frontend:rollback-20261015T182605Z-six-hour-ui-priority cti-central-frontend:current
ln -s /opt/cti-platform/releases/20261015T182605Z-six-hour-ui-priority /opt/cti-platform/current.rollback-next
mv -Tf /opt/cti-platform/current.rollback-next /opt/cti-platform/current
docker compose --project-name cti-backend-20260903-v1 \
  --env-file /etc/cti-platform/central.env \
  --env-file /opt/cti-platform/clients/backend-integrations.env \
  --env-file /opt/cti-platform/clients/misp-client.env \
  --file /opt/cti-platform/releases/20261015T182605Z-six-hour-ui-priority/compose.yaml \
  --file /opt/cti-platform/releases/20261015T182605Z-six-hour-ui-priority/infra/vps/central.compose.yaml \
  up -d --no-deps --force-recreate --no-build frontend
```

## 17. Git branch, commit, and push state

Branch `codex/final-delivery-20261016`; implementation commit `d1d9beea53372df8d8b71cfad7c196caed332fde` was pushed to `origin/codex/final-delivery-20261016`. This completed post-deployment report is committed and pushed as a separate evidence-only follow-up on the same branch. No force push or history rewrite was used.

## 18. Remaining limitations

The frontend bundle reports a non-failing chunk-size warning (`641.15 kB` JavaScript before gzip). No functional or security failure is associated with this warning. No remaining final-delivery blocker was found.
