# Verification — 2026-10-31

Implementation branch: `recovery/shared-runtime`. Independently reviewed application checkpoint:
`f42fa29` (legacy outcomes at `4cdb3be`; stateful migration at `d4a630c`; earlier foundation at
`a06faf7`, `3d7ab5a`, `9765da6`, and `fe31f52`). No deployment or
production database access was performed during implementation.

- **435 passed, 13 skipped**: deterministic backend suite against disposable
  PostgreSQL 15, including concurrent duplicate/stale turns, transaction failure,
  ownership, model-budget rotation, simultaneous global admission at the last quota slot,
  migration preservation, stateful journeys across all six migrated levels,
  explicit legacy wins, bounded judgments, progression below rank 1000, and a new two-file
  game discovered and played through the existing page/API. Skips are opt-in paid
  model experiments.
- **10 browser checks passed**: eight actual Chrome/ASGI/database journeys covering all three Glitch
  levels, persisted reloads, lost completion recovery, safe text rendering,
  mobile layout, permanent provider failure escape, expired credentials, and two
  simultaneous first-visit tabs. Honeypot and Interrogation exercise the same action
  controls, reloads, lost accusation receipts, and exhausted actionless failures.
  The provider alone is replaced in those journeys. Two additional browser
  component checks feed saved Giga Chad loss/win outcomes into the actual page and
  verify its modal and level unlock; they do not exercise the HTTP submission flow.
- **8 real API requests**: GPT-6 Luna availability, level-one bypass, ordinary
  moderation approvals/rejections, and token-protection controls. See
  `model-smoke.json`. This is not statistical difficulty calibration.
- **8 additional real API requests**: Honeypot narration/classification and witness
  testimony in all three Interrogation cases. All completed; each case produced
  enough leads to enable accusation. See `stateful-model-smoke.json`. These ran
  directly against the game contract without database access; HTTP persistence is
  covered separately with deterministic provider fixtures.
- **42 resolved runtime dependencies, zero known advisories** from pip-audit.
- Python compilation and git whitespace checks pass. Later evidence-only changes
  refine browser assertions and update Giga Chad's displayed win description to
  match the already-reviewed rule; no scoring logic changed.

## Independent review

Claude Opus 5.5 reviewed clean worktrees, read-only, against exact committed heads.
Each scoped review has an eight-minute total budget, including any delta review.
The initial foundation review exhausted its original budget; resumed cap review
was explicitly requested by Kelly.

1. At `a06faf7`, review found a failed-prompt retry lockout and an unintended shared
   proxy-IP gameplay budget. Browser reproduction and a same-peer/different-player
   regression test confirmed the problems. Fixed at `9765da6`. It also identified
   first-visit tab identity and expired-token races; Web Locks and ordered auth
   startup now cover those paths, with browser tests.
2. Delta review at `9765da6` confirmed those fixes but found that rotating guest
   identities multiplied the model budget. Fixed at `fe31f52`: recovered turn
   admissions now also consume a separately committed, PostgreSQL-serialized,
   site-wide daily budget. A regression test proves a fresh guest cannot bypass it.
3. The initial final-cap review timed out without a verdict. At Kelly's explicit
   request to continue, a fresh narrow review of `9765da6..fe31f52` at `be57f63`
   completed in 74 seconds with **no P0/P1 blockers**. It verified PostgreSQL atomic
   admission, committed reservations surviving rollback, repository argument order,
   and containment of recovered paths. The cap counts admissions, not dollars;
   guesses, retries and errors conservatively consume slots. SQLite does not
   provide the concurrency guarantee. Our new eight-worker PostgreSQL tests prove
   first-row creation and exact admission limits of one/four, even after rollback.
4. Stateful migration `be57f63..d4a630c` received a separate 142-second static review:
   **no P0/P1 blockers**. It covered ownership, action validation, private/public
   state, wins, failure rollback, retries, terminal states and old-route containment.
   Design notes: bulk category guesses and visible prefixes simplify Honeypot;
   non-model actions still consume admission budget.
5. Legacy scoring/progression `d4a630c..4cdb3be` received a 177-second review. It
   caught one P1 regression: declaring only easy/hard rejected the existing Expert
   levels in Arena and Debate. The earlier progression fixtures had also omitted
   those levels. Confirmed against both page mappings and backend expert branches;
   fixed at `f42fa29`, with API tests for hard-to-expert unlocks and expert submission.
   It also found a browser-only Giga Chad win inferred from points. Both handler
   and template now trust the saved boolean outcome, covered by browser checks.
   A 44-second delta review of `4cdb3be..f42fa29`, within the original eight-minute
   budget, confirmed both fixes with **no P0/P1 blockers**. Strict judge parsing
   may reject model prose or truncated output; that is an explicit failed run,
   not a scored completion.

The reviewer did not run tests or access infrastructure, and did not inspect
legacy upload containment or dependency lockfiles in depth. Local executable
checks cover those changes, but this is not a comprehensive release approval.
Guest provisioning still needs hosting-specific trusted-proxy verification before
production; its peer budget is intentionally separate from gameplay and model
spending. The final daily ceiling covers Glitch, Honeypot and Interrogation, not legacy games.

## Remaining release work

See `README.md`: other games still need migration/repairs, model calibration,
staging rollout/rollback verification, and review of those future changes. The
historical browser suite has not been claimed as passing. Production is unchanged.
