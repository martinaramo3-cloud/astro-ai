# Security fixes — 18 September 2026

Branch: `codex/security-review-2026-09-18`. These changes have not been deployed.

## Changes

- Check profile ownership on both chat creation and editing; scope the prompt join to the owner; clear invalid historical associations during the existing idempotent database startup migration.
- Persist rate limits in SQLite so workers/restarts share limits. Hash rate-limit identities and expire their rows. Throttle login, signup, reset, verification resend, bug reports, uploads and general account requests.
- Bound actual incoming request bytes, including bodies without Content-Length, to 256 KiB (9 MiB multipart upload envelope). Bound strings, chat messages and image lists; reject unusable dates/times and invalid email formats before saving.
- Reserve AI cost and concurrency in a SQLite transaction before provider calls. Meter the previously untracked routing/date helpers too. Keep conservative charges for failed/abandoned calls and reconcile successful calls only after usage is recorded. Require verified email for free Smart/Deep access. All AI endpoints share the provider guard.
- Make reset-token consumption conditional and atomic. Password reset, token consumption and session revocation are one transaction. Make invitation acceptance, slot checking and profile creation one transaction; validation errors and failed inserts leave the invitation usable. Direct profile creation also checks capacity while holding the write lock.
- Delete associated invites, auth tokens, bug reports, error records and usage records along with the account. Serialize deletion against uploads. Keep only anonymous AI-budget amounts so deletion cannot reset global spending. Late usage logging after deletion is anonymous.
- Escape user names and link attributes in emails.
- Forward the caller's output-token ceiling through both Claude response paths. The 4,000-token setting is now a maximum safeguard, not the default for every answer.
- Decode and verify uploaded image formats/dimensions, cap aggregate storage, and cap saved chat count. Image decoding runs off the async request thread.
- Replace vulnerable frontend/backend packages, including vulnerable transitive HTTP dependencies. Keep package-lock and Python pins updated.
- Add nonce-based script CSP and browser security headers. Documents render dynamically so each response has a fresh nonce. Service worker no longer caches private page documents. Remove persisted admin secrets; existing localStorage user bearer tokens remain for compatibility, protected by the stricter script policy. HttpOnly session migration and admin MFA remain separate improvements.
- Keep public `/health` minimal; operational diagnostics move to admin-authenticated `/admin/health`.
- Resolve frontend lint errors and browser capability/hydration issues without globally disabling rules.

## Default limits and operational settings

| Control | Default |
|---|---|
| General requests | 240/minute per ASGI peer IP |
| Authenticated requests | 120/minute per account |
| Login | 30/15 min per IP, 10/15 min per email |
| Signup | 10/hour per IP, 3/hour per email |
| Reset emails | 10/hour per IP, 1/minute per email |
| Reset attempts | 20/15 min per IP |
| Resend verification | 1/minute per account |
| Bug reports | 10/hour per IP |
| Uploads | 10/minute per account, 8 MiB/file |
| Image storage | 50 MiB/account, 400 MiB total |
| Saved chats | 100/account, 200 messages/chat |
| Provider calls | 200/day/account, including routing helpers |
| Concurrent provider calls | 1/account, 8 globally |
| Daily estimated AI budget | Free $1, Standard $5, Premium $15; $100 globally |

Set `AI_GLOBAL_DAILY_USD` to override the global estimated daily budget. `AI_USER_DAILY_USD` overrides the per-user default for all plans. Budget windows use UTC. Limits include conservative reservations for pending calls. They are application estimates, **not a guarantee of the provider invoice**; provider billing/spend limits remain the independent backstop. Usage left uncertain after a timeout stays charged to prevent repeat-call abuse. A 300-second concurrency lease recovers from crashed workers; uncertain cost is retained for its budget window.

Before production rollout, confirm Uvicorn's trusted proxy configuration accurately supplies `scope.client` on Render. Do not blindly trust X-Forwarded-For supplied by arbitrary clients. If every request is attributed to one hosting proxy, IP limits would be shared; test with two controlled clients and configure trusted proxy addresses at the server level.

Free accounts can still use Fast before verification. Smart/Deep ask them to confirm their email. Ensure Resend delivery works before release. Existing accounts marked verified remain verified. Client errors contain readable retry/verification messages.

## Migration, retention and rollback

New tables: `rate_limits`, `ai_reservations`; no external service is required. Startup also clears cross-owner or orphaned chat/profile associations. Back up the database before deploying this migration. Existing passwords and sessions remain compatible.

Account deletion removes active data. Existing backup copies are governed by the backup retention policy and are not rewritten by account deletion. Review restoration procedures to avoid reintroducing deleted accounts; externally downloaded/provider-managed backups are outside this code's control.

Rolling back application code does not require dropping the new tables. If rolling back only the frontend, note that the updated service worker intentionally removed page caches. Public health now exposes only readiness; deployment fingerprint checks must use the authenticated diagnostics route.

## Verification

See tests/test_security.py for regressions covering cross-account associations, legacy data repair, invite retries/rollback/concurrency, deleted-account leftovers and late writes, token races, reset session revocation, rate expiry/concurrency, bad input, email escaping, budget enforcement, Claude provider requests, upload validation/quotas and public diagnostics.

The original audit under docs/security-review-2026-09-18 is historical evidence. Its standalone reproduction script asserts the OLD insecure behavior and is not the regression suite.

Production build uses `npm run build -- --webpack` for local verification because this execution environment blocks Turbopack's internal subprocess port binding. No paid-model smoke test or live traffic test has been performed.

### Final checks

- 248 backend tests passed.
- TypeScript and ESLint passed.
- Production Webpack build passed.
- Local production homepage, chat and admin returned 200; every script nonce matched its CSP, nonces changed between requests, and no-store/nosniff headers were present.
- npm audit: zero reported vulnerabilities after updates.
- OSV scan of all 51 installed Python packages: zero advisory matches; pip dependency check passed.

Limits: no claim of absolute security, no paid AI generation test, and no production hosting/proxy or mail-delivery verification. All edits are local to the branch until an authorized deployment.
