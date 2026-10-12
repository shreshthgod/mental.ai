# Git reconciliation, 2026-10-09

Branch: `feat/on-device-intelligence-product-refinement`
Upstream baseline: `https://github.com/shreshthgod/mental.ai` `main` @ `78ac6da4d49ac35d65e00ca82b25245560695fa3`

## Remotes as found

`origin` was `https://github.com/PrathamKapoor/Vantage-The-Emotional-Signaler.git`
and pointed at the *older* Vantage line. The published MENTAL.AI repository named in
the brief (`shreshthgod/mental.ai`) was not configured as a remote at all, so a
plain `git fetch origin` would have kept reconciling against the wrong baseline.

Actions taken:

- Added `upstream` -> `https://github.com/shreshthgod/mental.ai`, fetched with `--prune`.
- Created `backup/pre-reconcile-62f43c6` at the pre-reconciliation `HEAD` before any
  integrating operation. No destructive reset, checkout, force push or blanket file
  replacement was used at any point.
- Left `origin` in place. Nothing was pushed to it.

## State before reconciliation

| | |
|---|---|
| branch | `main` |
| local `HEAD` | `62f43c6` "Apply 3D metallic chrome gradient and depth shadow to VANTAGE hero wordmark" |
| local `origin/main` | `62f43c6` (identical, so `origin` carried nothing newer) |
| `upstream/main` | `78ac6da` "Document verified owner publication and recovery checkpoint" |
| uncommitted changes | none (`git status --short` empty) |
| untracked, ignored only | `api/__pycache__/`, `web/dist/`, `web/node_modules/`, `web/shots/`, `web/vite.log` |

`git log --left-right --oneline upstream/main...main` returned four commits on the
left and none on the right: local `main` was a strict ancestor of `upstream/main`.

## Local-only vs remote-only vs shared

| Category | Commits |
|---|---|
| Remote-only (missing locally) | `ab22715` first commit · `2053855` Complete Mental AI project update · `ae15d97` Recover safety routing, API contracts, persistence and login integration · `78ac6da` Document verified owner publication and recovery checkpoint |
| Local-only (absent remotely) | none |
| Shared | `10b6972`, `58ec39a`, `e914b7a`, `116c945`, `a114e31`, `82fdb1e`, `62f43c6` |

There was no divergent local work to preserve: local `main` had no commits that
`upstream/main` lacked, and no uncommitted tracked edits. The only local-only state
was build and run output (`web/dist/`, `web/shots/`, `web/vite.log`,
`api/__pycache__/`), all git-ignored and all left untouched on disk.

`2053855` is the fork point in content terms: the `62f43c6` tree is the
Vantage-branded frontend, and `2053855` onward is the MENTAL.AI recovery line that
renames the brand and rebuilds auth, persistence, the entry composition and the
safety engine.

## Integration

`git merge --ff-only upstream/main` fast-forwarded `62f43c6..78ac6da` with no
conflict, because there was nothing local to conflict with. 252 files changed,
+750,408 / -1,154.

Resolutions by area:

- **Safety routing.** `Step 12 - Packaging/package/mental_health_screening/safety.py`
  (1,734 lines) plus `fusion.py` and `semantic.py` arrive from upstream. Kept as
  upstream wrote them.
- **API, auth, persistence.** `api/api.py` rewritten (729 lines changed),
  `api/auth.py`, `api/db.py`, `api/contracts.py`, `api/execution.py`,
  `api/limits.py`, `api/body_limit.py` new; `supabase/schema.sql` and
  `supabase/migrations/20261008_authoritative_analysis.sql` new.
- **Frontend entry.** `web/src/pages/Start.tsx` new, `web/src/pages/Login.tsx`
  deleted, `web/src/components/entry/*` new, `web/src/styles/entry.css` new
  (750 lines). `/` and `/login` now render the same entry composition. Upstream
  arrangement accepted unchanged.
- **Contracts and evidence.** `tests/contract/analysis-v1.json`, the safety corpora
  (`cases.json`, `expansion.json`, `holdout.json`, `holdout2.json`,
  `temporal-*.json`), the `RUN-0*` and `safety-run-*` reports, and the decision /
  flow / handoff records were all taken from upstream as the historical record.
- **Local-only build output** (`web/dist/`, `web/shots/`) is git-ignored and was
  neither deleted nor committed.

## Identity

`git config user.name` = `PrathamKapoor`, `user.email` = `prathamkapoor027@gmail.com`,
both already repository-local. Push rights on `shreshthgod/mental.ai` were verified
through the GitHub API before any commit was created: authenticated as
`PrathamKapoor`, `permissions.push = true`, `permissions.admin = false`.

Note on conflicting history: `handoff.md` section 6 records an earlier instruction
that author and committer must be `shreshthgod <shreshthnmims.it@gmail.com>`. The current instruction requires `PrathamKapoor <prathamkapoor027@gmail.com>` for feature-branch authors and committers. PR commits are normalized to that identity during this review. Existing `shreshthgod` commits keep their original
author and were not rewritten.

## Outcome

Local branch base is now byte-identical to `upstream/main` @ `78ac6da`. Nothing local
was lost, no upstream fix was silently dropped, no history was rewritten.