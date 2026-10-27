# ACTIT Final Integration Verification — 2026-10-27

## Outcome

The final integration candidate is based on `origin/codex/actit-final-production`
and uses the public product title **ACTIT — Unified AI-Assisted Cyber Threat
Intelligence Platform**. The repository and local Docker Compose project share
the stable name `ACTIT-Platform` / `actit-platform`.

## Integrated changes

- Preserved the latest production-line collection/export behavior while adding
  per-source locking and separate interactive/background execution capacity.
- Fixed manual-source reactivation, safe empty external summaries, NVD
  enrichment persistence, risk recalculation checks, and the JSON collection
  diagnostic contract.
- Added the ACTIT brand assets and frontend brand components.
- Added leakage-aware DNRTI cleanup, BERT training/evaluation, finalization,
  and reproducibility utilities without changing the production model when the
  promotion gates were not met.
- Added the MIT license, third-party scope notice, editable academic-paper
  sources, and the prepared ACTIT social-media pack.
- Upgraded Vite to 8.3.5, Vitest to 4.1.12, and the React Vite plugin to 6.1.2.
- Fixed the root Compose project name as `actit-platform` so moving the checkout
  does not recreate resources under a directory-derived legacy name.
- Preserved Adminer as an opt-in `database-ui` service, bound only to
  `127.0.0.1:8080` and connected to the application database network.

## Verification evidence

The following checks were run from a clean integration worktree:

- Python repository suite after integration with `main`: 554 tests passed.
- Frontend suite after integration with `main`: 22 files and 174 tests passed.
- TypeScript type/lint check: passed.
- Frontend production build with Vite 8.3.5: passed.
- npm production and complete dependency audits: 0 vulnerabilities.
- Docker Compose default and `database-ui` profile rendering: passed.
- Python bytecode compilation: passed.
- `git diff --check`: passed.

The memory regression test was run as part of the Python suite without a
concurrent frontend build and passed. A prior parallel run exceeded its strict
test threshold because both suites competed for memory; that parallel result is
not used as the acceptance result.

## Model decision

The clean-v2 experiments did not satisfy every configured promotion gate.
Therefore the decision remains `retain_legacy_bert`, and no unsupported model
replacement is represented as production-ready.

## Client migration boundary

The intended Windows destination is:

`C:\My Projects\ACTIT-Platform`

The legacy checkout and its Docker resources must be removed only after the
authorized Windows device is online, all required untracked files have been
compared or migrated, the new checkout's Git remote is verified, and the new
Compose stack passes its checks. This report does not claim that destructive
client-side cleanup has occurred while that device is offline.
