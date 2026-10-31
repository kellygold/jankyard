# Verification — 2026-10-31

Implementation branch: `recovery/shared-runtime`. Application code checkpoint:
`fe31f52` (following `a06faf7`, `3d7ab5a`, and `9765da6`). No deployment or
production database access was performed during implementation.

- **391 passed, 13 skipped**: deterministic backend suite against disposable
  PostgreSQL 15, including concurrent duplicate/stale turns, transaction failure,
  ownership, model-budget rotation, migration preservation, and a new two-file
  game discovered and played through the existing page/API. Skips are opt-in paid
  model experiments.
- **5 passed**: actual Chrome/ASGI/database journeys covering all three Glitch
  levels, persisted reloads, lost completion recovery, safe text rendering,
  mobile layout, permanent provider failure escape, expired credentials, and two
  simultaneous first-visit tabs. The provider alone is replaced in these tests.
- **8 real API requests**: GPT-6 Luna availability, level-one bypass, ordinary
  moderation approvals/rejections, and token-protection controls. See
  `model-smoke.json`. This is not statistical difficulty calibration.
- **42 resolved runtime dependencies, zero known advisories** from pip-audit.
- Python compilation and git whitespace checks pass.

## Independent review

Claude Opus 5.5 reviewed clean worktrees, read-only, against exact committed heads.
The shared total time budget was eight minutes, including subsequent delta review.

1. At `a06faf7`, review found a failed-prompt retry lockout and an unintended shared
   proxy-IP gameplay budget. Browser reproduction and a same-peer/different-player
   regression test confirmed the problems. Fixed at `9765da6`. It also identified
   first-visit tab identity and expired-token races; Web Locks and ordered auth
   startup now cover those paths, with browser tests.
2. Delta review at `9765da6` confirmed those fixes but found that rotating guest
   identities multiplied the model budget. Fixed at `fe31f52`: recovered turn
   admissions now also consume a separately committed, PostgreSQL-serialized,
   site-wide daily budget. A regression test proves a fresh guest cannot bypass it.
3. The final narrow review of that budget fix **timed out without a verdict**.
   Independent sign-off on the last delta is therefore **open**, not passed.

The reviewer did not run tests or access infrastructure, and did not inspect
legacy upload containment or dependency lockfiles in depth. Local executable
checks cover those changes, but this is not a comprehensive release approval.
Guest provisioning still needs hosting-specific trusted-proxy verification before
production; its peer budget is intentionally separate from gameplay and model
spending. The final daily ceiling covers recovered prompt games, not legacy games.

## Remaining release work

See `README.md`: other games still need migration/repairs, model calibration,
staging rollout/rollback verification, and completion of independent review. The
historical browser suite has not been claimed as passing. Production is unchanged.
