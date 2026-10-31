# Calibration repair and local production rehearsal — 2026-10-31

Application candidate: **`129ab76`**. Later runner/evidence commits leave `app/`
unchanged. All nine public games still use the shared runtime, page, persistence
and leaderboard. **Production is unchanged; external staging is unconfigured.**

## What changed and why

### Arena: an apparent win was a damage-direction bug

The old judge returned ambiguous `player_damage` and `gladiator_damage` numbers.
In three repeated confused-player/attacking-opponent probes, it described the
player being hit but supplied numbers the server applied to the opponent.
**The previously reported expert win is invalid as beatability evidence.** The
original receipts remain available; they must not support a release decision.

Explicit numerical HP-loss fields improved this but still produced a contradictory
reply. The final contract instead validates `attack`, `defend`, or `confused`
actions and tactical advantage. The server calculates damage from a published
fixed table. Twelve repeated live judge probes matched the expected direction.
The model may still misclassify tactics; validated labels cannot reverse the
server's fixed arithmetic. Malformed judgments leave the saved stage unchanged.

Full runs found two further problems: the player's actual strategy was buried in
the system prompt, and the opponent could inspect the current player move. The
player now receives the saved strategy explicitly each turn; both sides choose
their move using prior rounds. Saved HP reaches the opponent prompt.

Arena version 5 starts opponents at 80/100/120 HP. The player starts at 100.
Timeouts compare remaining-health percentages; ties and mutual knockouts lose.
Doing nothing cannot win from the tutorial's smaller opponent HP alone. Visible
rules describe the math and tactical judging criteria. All 27 action/advantage
combinations, passive timeout, mutual knockout, failure/retry and saved-state
paths have deterministic coverage.

Two current-version concrete-strategy trials won; two `win` controls lost. Each
used 15 model calls. This is a repeated smoke sample, not a win-rate estimate.
Hard/expert beatability and difficulty ordering remain unproven on version 5.

### Glitch: teach identifiable application trust mistakes

The hardened higher levels produced no wins in bounded probes, giving learners
little useful feedback. Version 2 deliberately teaches two insecure workflows:

- Level 2 trusts a requester-written `[MODERATOR REVIEW]` marker and corrected
  moderation label. The win still requires literal `banana` in the submitted
  prompt and exactly `APPROVED` in the response.
- Level 3 trusts a maintenance ticket's requester-written `status=approved` and
  exports protected configuration fields. The exact public game token must still
  appear in the response; a refusal without it loses.

These are curriculum changes with unchanged win detectors. The visible lessons
explicitly identify the authentication/access-control mistakes. They demonstrate
deliberately vulnerable application workflows, not defeat of a hardened model.
Four prototype bypasses and six controls matched expectations. All three final
levels then passed the real browser journey below. New rule versions start fresh
scoreboards/unlocks while retaining historical records.

## Executable evidence

| Check | Result | Receipt |
|---|---|---|
| PostgreSQL backend | 450 passed; 13 opt-in paid tests skipped | `calibration-verification-gates.json` |
| Chrome fixture journeys | 16 passed | Same gate receipt; desktop/mobile screenshots |
| Arena judge controls | Old numerical contract 8/12 correct; intermediate repair 11/12 plus one rejected contradiction; final server table 12/12 correct | `arena-judge-numeric-calibration.json`, `arena-judge-server-table.json` |
| Arena version 5 tutorial | Concrete strategy won twice; vague strategy lost twice | `arena-v5-precise*.json`, `arena-v5-vague*.json` |
| Stateful real-provider journeys | All three Honeypot levels and all three Interrogation cases passed | `stateful-live-journeys.json` |
| Glitch real-provider HTTPS/browser | Three controls did not win; three intended bypasses won; natural unlocks, replay, reload, counters and scores agree | `https-glitch-proof-complete.json` |
| Independent Claude review | No P0/P1 blockers in either scoped pass; 220.57/900 seconds total | `calibration-review-receipt.json` |

Honeypot/Interrogation used 19 actual provider calls through ASGI and a temporary
SQLite database. Invalid premature guesses/accusations were rejected, wrong
accusations did not win, and identical retries used no extra provider calls.
Each completion had one submission and one best-score row. This proves known
solution journeys, not that a new learner can infer each solution.

### Local production-mode browser proof

Chrome → local HTTPS → two Gunicorn/Uvicorn workers → real provider → PostgreSQL
→ saved result and scoreboard → browser reload. The server ran in production mode
with an ephemeral secret; no provider was mocked. The temporary self-signed
certificate was trusted only by the test context, without changing OS trust.

The three Glitch runs saved six turns, three submissions and three score rows.
Six identical receipt replays preserved state. The guest cookie was Secure,
HttpOnly and SameSite=Lax. Production migration ran twice after the empty owned
database was bootstrapped in development mode. The workers stopped and the owned
schema was removed afterward. After the final PostgreSQL test run, zero tables
remained and the owned database server was stopped. Completed review worktrees
were removed after their verdicts were saved. The original checkout is unchanged.

![Glitch diagnostic lesson, actual saved win](screenshots/https-glitch-proof-complete-level_3.png)

The successful rehearsal allowed 12 total turn admissions (six original turns
and six retries), 60 per-player requests/minute and 20/day. Retries conservatively
consume admission budget even when the saved receipt avoids another provider
call. The first rehearsal's 12/day player allowance also counted run creation,
so it stopped at the final attack with HTTP 429 after five saved provider turns.
That failure is retained in `https-glitch-proof.json`; no failed turn or extra
score was saved. The corrected runner retained the 12-admission model ceiling.

Reproduce with only a provider key in the environment, an empty dedicated local
PostgreSQL database and no concurrent users of that database:

```sh
RUN_LIVE_MODELS=1 python -m scripts.live_https_proof \
  --database-url postgresql+psycopg2://USER@127.0.0.1:PORT/jankyard_recovery_test \
  --output docs/recovery/new-https-proof.json
```

The runner rejects other hosts/database names and nonempty schemas. It owns and
removes its test schema. It tests host dependencies, not the Docker image or cloud
ingress. Optional `JANKYARD_BROWSER_EXECUTABLE` selects an installed Chrome.

## Bounded calls and preserved unsuccessful trials

This pass used **308 provider calls**, separate from the previous checkpoint's
303 attempts. All new provider requests returned complete responses; a rejected
judge payload and losing trials remain failures, not wins. No automatic provider
retries occurred. Counters and source commits are retained in each receipt.

| Group | Calls |
|---|---:|
| Old/intermediate/final Arena judge probes | 36 |
| Complete Honeypot/Interrogation API journeys | 19 |
| Advanced Glitch/Firewall follow-up probes | 22 |
| Glitch workflow prototypes | 10 |
| Arena version 3 full trials | 72 |
| Arena version 4 full trials | 72 |
| Telephone hard flexible strategy | 6 |
| Arena version 5 repeated strategy/control trials | 60 |
| Two HTTPS browser rehearsals | 11 |

The older `arena-fixed-*` and `arena-fair-*` receipts are version 3/4 losses,
preserved to explain the repairs. They are not current difficulty evidence.
The 22 follow-up probes produced no wins. One old Glitch level-2 fullwidth
`ｂａｎａｎａ` input was ineligible for the literal input condition and must not
be counted as a defended eligible attack. Firewall level-3 ordinary controls
now reached the model rather than stopping at its input filter. The additional
Telephone hard strategy completed but scored 20/100 and lost.

## Recommendation and remaining gates

Keep the shared architecture and two-file contribution contract. Require a clear
boundary, detector fixtures and bounded real-model positive/negative examples
for a teaching level. For model-judged games, use validated classifications and
server scoring wherever possible; keep uncertainty visible.

Advanced Firewall, Telephone hard, upper Giga Chad, and current Arena hard/expert
still need demonstrated winning strategies and repeated controls. Do not label
those levels calibrated or all-level beatable. If intended exploits cannot be
reproduced, revise their teaching scenario explicitly as done for Glitch, rather
than weakening a detector or interpreting a completed loss as success.

No known external staging target is configured. The local rehearsal closes a
production-mode application gap, but the container build, external ingress,
registered deployment journey and real-backup restoration remain unverified.
See [rollout.md](rollout.md). No other project's infrastructure was used.
