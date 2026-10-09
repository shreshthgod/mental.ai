# Supabase/login continuation, 2026-10-09

ENGINEERING: partial — reproduced login defects corrected; previous routing/semantic/runtime requirements remain incomplete.

INTEGRATION: partial — development and compiled app/installed SDK pass with intercepted/in-memory responses. Live Supabase, Google consent, schema/RLS and requested account creation are BLOCKED.

RELEASE_VALIDATION: blocked — reviewed independent data/policy/semantic/licensing and genuine isolated/deployed verification remain unavailable. Synthetic checks are engineering evidence.

The user supplied project keys and requested working access plus Google login. Genuine Project URL and intended login email are still missing. Existing backend URL points to127.0.0.1 and browser configuration is absent. Opaque keys cannot identify their project. Dashboard/browser inventory was empty. Supplied keys were not written against the placeholder; no account/password/verification was fabricated, no account/email/real record/provider operation occurred. The disclosed secret should be rotated by the owner before live use; no automatic rotation occurred.

The Google button/SDK already existed. D104 repairs router destination and Remember me propagation with15-minute credential-free metadata, trusted identity adoption and once-only routing. D105 checks public provider settings before redirect, explicitly handles SDK initialization errors and bounds restoration. D106 removes token prefix/query data from QA diagnostics. D107 checkpoints development and compiled verification. No layout/styles/colors/fonts/branding/animations/navigation changes; all style hashes equal D103.

Before: actual-module Google initiation returned `/screen` instead of `/screen?source=fixture#history`, with no persistence preference for new visitors. Disabled-provider test failed Missing expected rejection. QA diagnostic disclosed a synthetic private token marker. All three required regressions exited1. After:24/24 grouped module checks pass. Initial control-character regex failed ESLint and was replaced with explicit character checks. Sandbox browser startup was blocked; approved run initially lacked a synthetic health fixture. Fixture/handler completed; development and compiled runs pass. Those failures are recorded in D104–D106, not called successes.

```text
email/password form -> API login -> Supabase GoTrue
Google button -> public provider gate -> SDK implicit callback
  -> initialize/getSession -> candidate API identity verification
  -> guarded trusted owner -> chosen mirror -> requested app route
check-in/editor -> protected bounded API -> independent raw safety
  -> guarded NLP/raw models -> fusion (semantic disabled) -> schema1.0
  -> bounded acknowledged core save -> common support/history presentation
```

Public settings request uses only publishable apikey, omitted credentials, no redirects and8s abort. Disabled/malformed/outage/timeout stays in the existing panel. SDK restoration has10s application deadline and explicit initialize.error check: installed getSession does not propagate initialization errors. Timeout does not promise SDK work is terminated. Logout/generation prevents late adoption. Pending metadata is preference only, not OAuth security state; SDK owns tokens/state. Missing expiry cannot invent a lifetime. Server-verified identity replaces SDK user id/name. Google offline/API access is not requested.

Original sentence rerun through actual API/models/browser with synthetic auth/persistence: HTTP200; raw primary Normal0.9502395987510681; urgency suicide0.7847130134418575/flagged=true/threshold0.15; safety HIGH/self/current/immediacy not_stated/degraded. Semantic disabled; other components complete. Main presentation Urgent support, with generic support and no invented access/location/time. Raw Normal remains research detail. Synthetic save/read-back/history retains authoritative snapshot. Before browser Normal; current browser Urgent support. This repeats the prior repair and does not verify real Supabase saving or every disclosure. Evidence: reports/browser-acceptance-current.json; original before artifacts preserved.

| Command | Actual result | Scope |
|---|---|---|
| env PYTHONPATH="Step 12 - Packaging/package:." python3 -m pytest tests -q |486 pass14.15s, one existing warning | Actual routes/models where specified; explicit provider/fault overrides, outside sandbox |
| npm --prefix web run qa:contract |55 checks/16 shared states, exit0 | Actual modules; SDK/fetch/storage overrides |
| npm --prefix web run qa:oauth |24 required grouped checks, exit0 | Actual auth/settings/diagnostic; SDK/fetch mocked, deadline timers accelerated |
| node scripts/oauthbrowserqa.mjs (web cwd) |13/13, zero page errors, exit0 | Actual development app/installed SDK; all provider/API intercepted |
| node scripts/oauthbrowserqa.mjs --built (web cwd) |13/13, zero page errors, exit0 | Compiled SDK-enabled app; all provider/API intercepted |
| env MENTAL_AI_ENV_FILE=/tmp/mental-ai-auth-qa-config node scripts/authflow.mjs http://127.0.0.1:5199 (web cwd) |47/47, exit0 | Existing email login/Chromium/API; synthetic GoTrue transport |
| node scripts/screenqa.mjs http://127.0.0.1:5199 (web cwd) |35/35, zero page errors, exit0 | Existing app/API/actual models; synthetic provider/storage and explicit error/contract fixtures |
| npm --prefix web run typecheck; npm --prefix web run lint | Both exit0 | Static client checks |
| npm --prefix web run build |193 modules9.13s, exit0 | SDK disabled, TypeScript included |
| env VITE_SUPABASE_URL=http://127.0.0.1:54321 VITE_SUPABASE_PUBLISHABLE_KEY=synthetic-public-key npm run build (web cwd) |193 modules8.78s, exit0 | SDK enabled with synthetic public configuration |
| python3 scripts/generate_contract_types.py --check; git diff --check | Both exit0 | Contract drift/whitespace |
| python3 scripts/verify_supabase_isolated.py --check-config | Exit2/BLOCKED; names only | No network; isolated project assertion/config/two pre-provisioned identities missing |

Both OAuth helpers stopped their owned Vite. Full launcher reached ready on8127/proxied web5199, then exited130 with backend cleanup; PID137300 was absent afterward. No task servers intentionally remain. Browser artifact scan found no configured backend private values; values not printed. Reports/browser-oauth.json and browser-oauth-built.json retain separate evidence. Counts are not added into a clinical score or load test.

Python3.12.3, Node24.21.0, installed Supabase/auth-js2.117.3, Vite6.4.3, TypeScript5.9.3, Playwright1.63.0, React18.3.1. No dependency changes. Source22b2ec3ed893c3e720805ab19b14dbb8da662e7d8bcebf5197c955736a833da7; schema1.0/policy safety-policy-2026.10.09.6 unchanged. ConfigSHA0e90561f45eb47079b53647199d5c11369d7dfb66d4d49e42654d925b8b7f64e; policy module0e9b128007102ab8d05e231ea652eb92ac505a66e438eb0feb5c86fc62a9e0b2. Complete model/source hashes in recovery-final-checkpoint.json; all artifacts equal D103. Secrets/real data excluded, docs hashed separately.

No routing/model/labels selected here. Prior D103 consumed diagnostics259/321 engine/214/321 pipeline,62/107 exact failed IDs preserved and not rerun. Familiar urgent98/98 and benign urgentFP0/73 are not independent validity. Separate temporal proposals/candidate remain historical and unvalidated; semantic stays disabled. True conversation memory unsupported. No Docker/platform/deployed/clinical review performed.

Changed source: .env.example comments; api/api.py docstring; web/package.json QA commands; web/scripts/authflow.mjs/oauthqa.mjs/oauthbrowserqa.mjs; web/src/App.tsx/pages/Start.tsx; components/entry/LoginPanel.tsx/login/LoginForm.tsx; lib/auth.ts/supabase.ts. Docs/matrix/defects/handoff/checkpoint updated under D104–D107; prior snapshots preserved. Remote shreshthgod/mental.ai; branchmain; HEAD2053855d51aaa5c9e06bd8c30f1c35d45c64716b. No stage/commit/push/deploy; identity unset/unverified, no invented attribution. Unrelated dirty work and excluded paper/research/TeX preserved.

Next input: genuine Project URL and intended login email. Then securely configure ignored environments, verify real GoTrue login/session without saving disclosures, provision only the requested new access account without overwriting existing users or sending invitation emails, and handle actual confirmation requirements honestly. Google needs separate OAuth client credentials in Supabase, authorized origins/callback/redirect URLs and user's own consent. See docs/SUPABASE.md and [official Google setup](https://supabase.com/docs/guides/auth/social-login/auth-google). Real isolation/history/schema verification still needs an explicitly isolated project/two pre-provisioned identities; access-account request does not authorize real-user data testing.
