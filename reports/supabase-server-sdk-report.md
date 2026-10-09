# Requested Node SDK and JWKS setup, D110–D112

The requested `@supabase/server` is installed at the root as exact1.9.1, with a new root lockfile. Official package metadata declares MIT, public beta and Node>=22; installed Node24.21.0 satisfies that requirement. The frontend lockfile, all styles, model artifacts, API schema and routing policy are unchanged by this batch. Thirteen packages were added/audited14, with0 reported advisories. That advisory output is not a security or clinical guarantee.

The four requested backend variable names are configured only in ignored0600 `.env`: SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY, SUPABASE_JWKS_URL. The browser still receives only its URL/publishable configuration. No credential value is included here. `npm run verify:supabase-sdk` imports the actual installed server/core exports and checks `resolveEnv` against the supplied values; it passes with fetch0. This script is the dependency's explicit local consumer. The Python API still authenticates through `auth.decode_token` -> `db.get_client().get_user`; no Node wrapper or local JWT verification was silently substituted.

The public unauthenticated JWKS GET returned HTTP200 with one ES256 public key and no private parameters. It used TLS verification, no redirects, no key/token header and a10s bound. Initial sandbox DNS failure is recorded separately from the successful network run. Public signing keys do not establish account/session authentication, RLS, schema compatibility or privileged administrative access.

| Command | Actual result | Scope |
|---|---|---|
| npm install --save-exact --ignore-scripts --no-fund @supabase/server@1.9.1 | Exit0;13 added/audited14;0 reported advisories | Requested compatible pinned dependency; existing root postinstall/vendor hooks skipped |
| npm run verify:supabase-sdk | Exit0, actual exports/all four variable comparisons/fetch0 | Real installed SDK/configuration, no network or account |
| python3 /tmp/mental-ai-jwks-probe.py | HTTP200/key_count1/ES256, exit0 after initial DNS failure | Real public metadata only |
| npm --prefix web run build |193 modules14.43s, exit0 | TypeScript/actual configured browser build; known backend-secret matches0 |
| env MENTAL_AI_ENV_FILE=/tmp/mental-ai-publication-empty.env SUPABASE_URL= SUPABASE_PUBLISHABLE_KEY= SUPABASE_SECRET_KEY= SUPABASE_JWKS_URL= PYTHONPATH='Step 12 - Packaging/package:.' python3 -m pytest tests -q |486 passed28.16s,1 existing Starlette/httpx warning | Real implementation/models/routes with explicit provider/fault stubs; live env disabled |
| npm --prefix web run qa:contract |55 checks/16 shared states, exit0 | Actual modules, mocked fetch |
| npm --prefix web run qa:oauth |24 required groups, exit0 | Actual modules; SDK/fetch/storage overrides, deadline timers accelerated |
| npm --prefix web run lint; python3 scripts/generate_contract_types.py --check; git diff --check | All exit0 | Static/drift/whitespace |

Current source fingerprint: `b52803f0293218f830f702032907db5ee7aae49239b0935f6b88896fe6facba7`. Root lock SHA256: `7878ae8270170d07028790fe0d4ab652bce1e1c0a8e9d4d5fcf298aa5c46ff47`. The fingerprint now includes the root lockfile; older fingerprints retain their original declared scope. Private env files/dependency trees/docs/reports are excluded. D109 handoff/checkpoint are preserved under `reports/*before-server-sdk*`.

ENGINEERING partial; INTEGRATION partial; RELEASE_VALIDATION blocked. Local unconfigured error is corrected and actual public settings/UI6/6 were verified at D109; private account/database integration is unverified. Google remains remotely disabled; intended account email/confirmation is missing. Independent reviewed policy/semantic/language/final data, isolated two-identity Supabase access and container/platform validation remain external blockers. Existing consumed diagnostic failures are preserved, not retuned or rerun in this batch.

Primary package/architecture references: [official package repository](https://github.com/supabase/server), [server package selection](https://supabase.com/docs/guides/auth/choosing-a-server-package), [official environment resolution](https://raw.githubusercontent.com/supabase/server/main/docs/environment-variables.md), [JWT/JWKS guidance](https://supabase.com/docs/guides/auth/jwts).
