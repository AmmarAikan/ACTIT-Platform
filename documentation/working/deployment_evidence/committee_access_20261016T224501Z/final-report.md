# ACTIT temporary production committee access evidence

- Worktree: `/opt/cti-platform/worktrees/committee-access-20261017`
- Branch: `codex/committee-access-20261017`
- Starting production release / rollback: `/opt/cti-platform/releases/20261016T193810Z-final-delivery`
- Public login: `https://cti-gateway-vps.tailf2792f.ts.net/login`

## Production accounts before this change

- `demo-viewer`: did not exist. The authenticated administration API returned no matching account.
- `demo-analyst`: did not exist. The authenticated administration API returned no matching account.

Both accounts were created through `POST /api/v1/admin/users`, which uses ACTIT's normal password hashing and audit path. No plaintext password was written directly to PostgreSQL.

## Final account and RBAC state

- `demo-viewer`: active, exact role `viewer`; production login and `/auth/me` passed. Dashboard read returned HTTP 200. An analyst-authorized write boundary returned HTTP 403, and the admin API returned HTTP 403.
- `demo-analyst`: active, exact role `analyst`; production login and `/auth/me` passed. Dashboard read returned HTTP 200. The same analyst-authorized boundary reached request validation (HTTP 422 for an intentionally empty body, with no mutation), while the admin API returned HTTP 403.

Neither account has administrator permissions.

## Frontend implementation

`VITE_ACTIT_COMMITTEE_ACCESS=true` enables a bilingual Committee Access card without enabling `VITE_ACTIT_DEMO_MODE`. Demo mode retains its distinct Demo Access title. When both flags are false, neither password is present in the compiled bundle. No auto-login or authentication behavior changed.

Changed files:

- `frontend/Dockerfile`
- `frontend/src/i18n/I18nContext.tsx`
- `frontend/src/pages/Login.tsx`
- `frontend/src/test/App.test.tsx`

## Pre-deployment tests

- Initial lint attempt in the new worktree: NOT RUN (`tsc` was unavailable before locked dependencies were installed).
- `npm ci --ignore-scripts`: completed; npm reported one pre-existing high-severity dependency advisory, with no automatic dependency mutation performed.
- Frontend lint: PASS.
- Targeted App/localization tests: `2` files, `19/19` PASS.
- Full frontend suite: `22` files, `169/169` PASS.
- Ordinary production build (`demo=false`, `committee=false`): PASS; both passwords absent.
- Demo build (`demo=true`, `committee=false`): PASS; both demo credentials present.
- Committee build (`demo=false`, `committee=true`): PASS; both committee credentials present.
- Exact candidate image build: lint PASS, `22` files / `169/169` tests PASS, production build PASS.
- Candidate bundle inspection: both requested credentials present; no `demo-admin` value.
- Candidate HTTP checks: `/` and `/healthz` HTTP 200.
- Candidate browser: English Committee Access, Arabic/RTL Committee Access, viewer login, and analyst login PASS; zero browser errors.

## Deployment result

Candidate release: `/opt/cti-platform/releases/20261016T224501Z-committee-access`.

Candidate image: `cti-central-frontend:20261016T224501Z-committee-access`, ID/digest `sha256:445e9a87b38170dc504c04249d8804aebdb7099e835d993f3cee8d4332f06a6c`.

Deployed release and current symlink target: `/opt/cti-platform/releases/20261016T224501Z-committee-access`.

Only the frontend was recreated. New frontend container: `c090cc480e0a` on `sha256:445e9a87...`. Backend `73821101f6a9` and PostgreSQL `29d223eb2d95` were not restarted or recreated.

Local production `/` and `/api/v1/health`: HTTP 200. Frontend, backend, and database are healthy.

The exact HTTPS hostname `https://cti-gateway-vps.tailf2792f.ts.net/login` returned HTTP 200. Browser verification through that hostname passed the English and Arabic/RTL Committee Access card, absence of Demo Access/admin credentials, viewer login, and analyst login with zero browser errors. `/api/v1/health` through the same hostname returned HTTP 200.

Read-only Tailscale status identifies this existing HTTPS endpoint as `tailnet only`. The VPS system resolver and an external web fetcher cannot resolve/enter it, so verification used the hostname with its recorded Tailscale address (`100.91.28.22`) while preserving TLS SNI and certificate validation. No Tailscale, Serve, or Funnel setting was changed.

## Final login and RBAC verification

- `demo-viewer`: login HTTP 200; `/auth/me` exact active viewer; analyst-authorized write boundary HTTP 403; administration HTTP 403.
- `demo-analyst`: login HTTP 200; `/auth/me` exact active analyst; analyst-authorized boundary reached request validation (HTTP 422 for intentionally empty input, no mutation); administration HTTP 403.
- Public HTTPS browser login through the exact hostname passed for both accounts.
- No administrator credential is present in the card or candidate bundle.

## Git state

Implementation commit `bcd7a23d2bc0aa9907688ed262afaef4f90d119b` was pushed to `origin/codex/committee-access-20261017`. This completed deployment report is committed and pushed as a separate evidence-only follow-up on the same branch. No force push or history rewrite was used.

## Remaining limitation

The supplied `.ts.net` endpoint is configured by the existing Tailscale state as tailnet-only rather than world-public. It works through the exact HTTPS hostname for tailnet clients and was verified as described above. Changing that ingress scope was explicitly out of scope. The frontend build also retains the existing non-failing bundle-size warning and npm reports one pre-existing high-severity dependency advisory; neither was modified in this narrowly scoped temporary-access change.

## Post-defense removal procedure

1. Build a new immutable frontend release with committee access disabled; do not enable demo mode:

```bash
docker build --pull=false \
  --build-arg VITE_ACTIT_DEMO_MODE=false \
  --build-arg VITE_ACTIT_COMMITTEE_ACCESS=false \
  --tag cti-central-frontend:<POST_DEFENSE_TAG> \
  /opt/cti-platform/releases/<POST_DEFENSE_RELEASE>/frontend
```

2. Preserve the then-current frontend under a rollback tag, atomically switch `/opt/cti-platform/current` to the new immutable release, tag the post-defense image as `cti-central-frontend:current`, and recreate only `frontend`:

```bash
POST_DEFENSE_RELEASE=/opt/cti-platform/releases/<UTC>-post-defense
POST_DEFENSE_IMAGE=cti-central-frontend:<UTC>-post-defense
CURRENT_RELEASE="$(readlink -f /opt/cti-platform/current)"

# Prepare POST_DEFENSE_RELEASE as a new immutable copy of CURRENT_RELEASE, then build it
# with the false flags shown in step 1. Never edit CURRENT_RELEASE in place.
docker image tag cti-central-frontend:current cti-central-frontend:rollback-committee-access
docker image tag "$POST_DEFENSE_IMAGE" cti-central-frontend:current
ln -s "$POST_DEFENSE_RELEASE" /opt/cti-platform/current.post-defense-next
mv -Tf /opt/cti-platform/current.post-defense-next /opt/cti-platform/current
docker compose --project-name cti-backend-20260903-v1 \
  --env-file /etc/cti-platform/central.env \
  --env-file /opt/cti-platform/clients/backend-integrations.env \
  --env-file /opt/cti-platform/clients/misp-client.env \
  --file "$POST_DEFENSE_RELEASE/compose.yaml" \
  --file "$POST_DEFENSE_RELEASE/infra/vps/central.compose.yaml" \
  up -d --no-deps --force-recreate --no-build frontend
```

3. Deactivate only the two temporary accounts through ACTIT's supported administration API:

```bash
ADMIN_TOKEN="$(docker exec cti-backend-20260903-v1-backend-1 python -c 'from sqlalchemy import select; from backend.app.db.database import SessionLocal; from backend.app.db.models import User; from backend.app.core.security import create_access_token; session=SessionLocal(); user=session.scalar(select(User).where(User.is_active.is_(True), User.role == "admin").order_by(User.created_at)); assert user is not None; print(create_access_token(str(user.id), user.role)); session.close()')"
for username in demo-viewer demo-analyst; do
  user_id="$(curl -fsS -H "Authorization: Bearer $ADMIN_TOKEN" "http://127.0.0.1:18080/api/v1/admin/users?search=$username&limit=10&offset=0" | jq -r --arg username "$username" '.items[] | select(.username == $username) | .id')"
  test -n "$user_id"
  curl -fsS -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
    -X PATCH -d '{"is_active":false}' \
    "http://127.0.0.1:18080/api/v1/admin/users/$user_id/active" >/dev/null
done
unset ADMIN_TOKEN
```

4. Verify both logins return HTTP 401 using their temporary passwords:

```bash
for credential in 'demo-viewer|ViewerDemo!2026' 'demo-analyst|AnalystDemo!2026'; do
  username="${credential%%|*}"
  password="${credential#*|}"
  body="$(jq -nc --arg username "$username" --arg password "$password" '{username:$username,password:$password}')"
  test "$(curl -sS -o /dev/null -w '%{http_code}' -H 'Content-Type: application/json' \
    -d "$body" http://127.0.0.1:18080/api/v1/auth/login)" = 401
done
```

5. Verify the public `/login` page visually contains neither username nor password, inspect the rebuilt bundle to confirm both password literals are absent, and confirm `/api/v1/health` remains HTTP 200. Do not remove or alter normal registration/login.

## Rollback

Rollback path: `/opt/cti-platform/releases/20261016T193810Z-final-delivery`. Its frontend image is preserved as `cti-central-frontend:rollback-20261016T193810Z-final-delivery` (`sha256:c88761a0734b66e4324cfc5d17d955b664f176698e195617fb344a9444a77bc0`). Exact rollback:

```bash
docker image tag cti-central-frontend:rollback-20261016T193810Z-final-delivery cti-central-frontend:current
ln -s /opt/cti-platform/releases/20261016T193810Z-final-delivery /opt/cti-platform/current.committee-rollback
mv -Tf /opt/cti-platform/current.committee-rollback /opt/cti-platform/current
docker compose --project-name cti-backend-20260903-v1 \
  --env-file /etc/cti-platform/central.env \
  --env-file /opt/cti-platform/clients/backend-integrations.env \
  --env-file /opt/cti-platform/clients/misp-client.env \
  --file /opt/cti-platform/releases/20261016T193810Z-final-delivery/compose.yaml \
  --file /opt/cti-platform/releases/20261016T193810Z-final-delivery/infra/vps/central.compose.yaml \
  up -d --no-deps --force-recreate --no-build frontend
```
