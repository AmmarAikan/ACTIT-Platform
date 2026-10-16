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

## Deployment result

PENDING NEW IMMUTABLE FRONTEND RELEASE.

## Post-defense removal procedure

1. Build a new immutable frontend release with committee access disabled; do not enable demo mode:

```bash
docker build --pull=false \
  --build-arg VITE_ACTIT_DEMO_MODE=false \
  --build-arg VITE_ACTIT_COMMITTEE_ACCESS=false \
  --tag cti-central-frontend:<POST_DEFENSE_TAG> \
  /opt/cti-platform/releases/<POST_DEFENSE_RELEASE>/frontend
```

2. Preserve the then-current frontend under a rollback tag, atomically switch `/opt/cti-platform/current` to the new immutable release, tag the post-defense image as `cti-central-frontend:current`, and recreate only `frontend` with the established `cti-backend-20260903-v1` Compose project, three environment files, and `--no-deps --force-recreate --no-build`.

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

4. Verify both logins return HTTP 401 using their temporary passwords.

5. Verify the public `/login` page contains neither username nor password and `/api/v1/health` remains HTTP 200. Do not remove or alter normal registration/login.

## Rollback

Rollback path: `/opt/cti-platform/releases/20261016T193810Z-final-delivery`. Final committee-access release/image identifiers and rollback commands will be added after deployment.
