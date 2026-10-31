# Recovery verification receipt

## Outcome

Local recovery candidate `9a3fa8c` has passed its executable application checks.
All public games share persisted runs and controls; deployed release validation
and complete difficulty calibration remain outstanding.

## Scope and topology

- PR: none created; isolated local branch `recovery/shared-runtime`.
- Candidate: `9a3fa8c7b3e008e8a330e1fa55a97af57a1a2771`.
- Target: owned localhost ASGI server, temporary SQLite and disposable local
  PostgreSQL 15 `127.0.0.1:55439/jankyard_recovery_test`.
- Browser, application and provider adapter all use the candidate. Real model:
  `gpt-6-luna`. Deterministic browser tests replace only provider responses.
- Excluded: production, real customer state, external staging and unrelated projects.

## Client-side proof

![Real Heist win](screenshots/live-heist.png)

Normal workflow: enter strategy, submit, automatically continue saved stages,
see the win and scoreboard, reload. Both Glitch and Heist completed with real
provider output. Run creation and saved turns returned HTTP 200. Network paths,
run IDs and final public receipts are in `live-browser-proof.json`.

## Backend assertions

```text
Glitch run: b615f8e9-89e2-4e48-a5e9-f7d0bd08a760
status: success; revision: 1; saved_turns: 1; score: 190
Heist run: 7d06f18d-daa0-4f36-b42f-8261e570d0d6
status: success; revision: 4; saved_turns: 4; score: 100
```

Direct database reads agreed with the API result. Reload preserved both runs.
PostgreSQL duplicate/stale request and last-budget-slot concurrency tests pass.
Synthetic backup/restore plus two migrations preserved historical row hashes;
`migration-rehearsal.json` has exact identifiers and hashes.

## End-to-end flow

Candidate -> Chrome form -> normal POST /api/runs -> POST /api/runs/ID/turns ->
real provider -> committed run/turn/result -> visible scoreboard -> reload.
Heist completed four paid stages under a hard 12-admission server ceiling; Glitch
used one. No mocked provider was installed in this local proof.

![Real Glitch win](screenshots/live-glitch.png)

## Negative-regression proof

Deterministic tests cover blocked Firewall inputs, non-winning replies, exhausted
losses, tie/mutual-KO losses, malformed judgments, errors at each agent/judge phase,
non-owner access, stale revisions and duplicate receipts. Failed stages create
zero saved results or score rows; prior stages remain intact. A second provider
call in one admitted stage is blocked before transport. The browser recovers lost
responses and pauses/retries a minute-limit rejection with the same request ID.

## Automated gates

- PostgreSQL backend: 437 passed, 13 opt-in paid tests skipped, 0 failed.
- Chrome/ASGI/DB fixture journeys: 16 passed, 0 failed.
- Runtime audit: 42 pinned dependencies, zero known advisories.
- Compilation and whitespace checks passed.
- Local image build: not executed; Docker daemon unavailable. CI now contains the
  image build, production configuration and missing-secret gates; CI was not run
  remotely in this session.

## Validation lanes

| Lane | Owner | Status | Receipt |
|---|---|---|---|
| Automated/static | Codex verification worker and coordinator | passed | 437 backend,16 browser; final exact-candidate rerun |
| Deployed client | Coordinator | skipped | No external staging target; two actual local real-provider browser journeys passed |
| Backend/integration | Coordinator and verification worker | passed | live-browser-proof.json; migration-rehearsal.json |
| Different-lab review | Claude subscription | passed | Initial and delta reviews: no P0/P1 blockers;328.57 seconds total within900-second cap |

The worker's earlier backend gate was at `95dc61e`; the final coordinator rerun is
at `9a3fa8c`. Migration/schema evidence is reusable because the delta only tightens
bootstrap rejection and leaves existing-database additive migration unchanged.

## Deploy-time manual steps

Set the deployment-specific database URL, provider key, strong secret, HTTPS and
trusted ingress policy. The image selects production; budgets and model selection
must be verified in the actual environment. Run the additive migration before
switching workers. See `rollout.md`. TeeFox/Golf.AI origins are unrelated and were
not used. External staging credentials/target, backup identity and actual config
parity remain unverified.

## Safety, cleanup, and release decision

- Only synthetic local identities and data were used; no messages were sent.
- Live browser server stopped and its temporary database was removed.
- Synthetic migration rehearsal left zero tables. The disposable PostgreSQL server
  was stopped after the final gate; zero test tables remained.
- The initial provider DNS outage is recorded; interrupted scenarios were rerun
  after recovery. Total calibration:303 attempts,285 complete responses,18
  connection failures. No automatic paid retries occurred.
- Unvalidated: remaining level calibration, deployed image/hosting behavior,
  actual-backup restore and deployed old-worker rollback.

**Partially validated: local recovery passes; model calibration and deployed staging remain incomplete.**
