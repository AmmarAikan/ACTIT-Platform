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

The final Git section below records the committed file list. Relative to the deployed rollback baseline, application changes are limited to the strict parser, requested navigation/readiness/auth/landing UI, their tests, and isolated defense-demo tooling. Files identified as production carry-forward are byte-identical to the rollback baseline and preserve already-deployed branding and prior contract repairs.

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

## 6. Demo user verification

`demo-viewer` authenticates as exact role `viewer` and cannot perform analyst/admin writes. `demo-analyst` authenticates as exact role `analyst`, can access analyst-authorized workflows, and cannot access admin operations. The public credential card exposes only these two accounts and is compiled only when `VITE_ACTIT_DEMO_MODE === 'true'`.

## 7. System Readiness change

The Extraction Model item, ML status request, ML loading/error aggregation, global failure influence, and ML refresh call were removed from System Readiness only. ML backend/API/artifacts and Processing & Analysis Center functionality remain intact.

## 8. Analysis Runs navigation removal

Analysis Runs was removed from sidebar navigation and dashboard/processing shortcuts. Its direct route, backend, and stored history remain available for compatibility/evidence.

## 9. GitHub link placement

The public Landing page contains one bilingual, branded `View source on GitHub` action targeting `https://github.com/AmmarAikan/CTI-Tool` with `target="_blank"`, `rel="noreferrer"`, and an accessible bilingual label.

## 10. Candidate release path

PENDING IMMUTABLE CANDIDATE BUILD.

## 11. Deployed release path

NO PRODUCTION DEPLOYMENT YET.

## 12. Container and image IDs changed

Before deployment, production frontend was `76e9c918546b`, backend `73821101f6a9`, and database `29d223eb2d95`. PENDING DEPLOYMENT RECORD.

## 13. Production health

Pre-deployment production `/` and `/api/v1/health`: HTTP 200. PENDING POST-DEPLOYMENT VERIFICATION.

## 14. Demo health

Demo `/` and `/api/v1/health`: HTTP 200. Candidate frontend/backend are healthy. Expanded bilingual smoke and visual checks passed.

## 15. Authenticated page verification

Demo Dashboard, System Readiness, Events, Event Details, Threat Storyline, and MITRE ATT&CK passed in the expanded browser smoke; English and Arabic/RTL evidence was captured. PENDING POST-DEPLOYMENT PRODUCTION WALKTHROUGH.

## 16. Rollback target

Rollback target: `/opt/cti-platform/releases/20261015T182605Z-six-hour-ui-priority`. Exact image/symlink rollback commands will be recorded before deployment and retained here.

## 17. Git branch, commit, and push state

Branch `codex/final-delivery-20261016`; commit and push pending.

## 18. Remaining limitations

The frontend bundle reports a non-failing chunk-size warning. No functional or security failure is associated with this warning. Deployment and post-deployment verification remain pending at this checkpoint.
