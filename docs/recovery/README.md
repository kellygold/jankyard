# Recovery checkpoint — 2026-10-31

This branch repairs the shared foundation and moves all nine public games onto
it. Local mechanics and browser checks do not establish production readiness.
No production database changes or deployment were performed.

## Implemented

- Public in-process Python submissions return HTTP 410; the web application no
  longer imports the unsafe sandbox. Prompt submissions remain available.
- Glitch uses a shared definition, renderer and persisted run service. Objectives
  explain the exact boundary and acceptance criteria. Straight and curly
  apostrophes work; ordinary approvals and refusals without a token do not win.
  A refusal that prints the protected token does count as a leak.
- Honeypot and Interrogation now use that same runtime and page. Declarative
  actions cover probes, guesses, witness questions and accusations. Both games
  resume from server-owned state; their old stateless streams return 410.
  Honeypot's hardest level now permits six probes plus six guesses. Only categories
  from a player's probes count, and only the exact authored guilty set solves a case.
- The database owns identity, history, attempts, completion and progression.
  PostgreSQL locks serialize concurrent turns. Request IDs bind retries to their
  original payload. Stale tabs and finished runs reject further attempts.
- A turn, final submission, best score and retry receipt commit together. Provider
  and database failures produce no saved win or consumed attempt. Completion is
  reported only after commit; the UI recovers a lost response using the same ID.
- Guest cookies cannot claim registered accounts. Bearer tokens are sent by both
  clients; invalid tokens cannot silently become anonymous play. Conversation
  details require ownership; recent-submission listings omit prompts and logs.
- Recovered scores use new tables and include the rule version and a hash of the
  configured provider/model. Historic leaderboard rows remain unchanged. Recovered
  game pages show the new scoreboard; the old leaderboard is explicitly labeled.
- There is one registry, including package discovery. New prompt games need a
  definition and positive/negative fixtures, with no custom route, UI or SQL.
- Dependencies are resolved and pinned from direct requirements. Retired OpenAI
  calls and the retired implicit Claude fallback are removed. The default is
  [`gpt-6-luna`](https://developers.openai.com/api/docs/models/gpt-6-luna), with a 45-second request timeout and no automatic paid retries.
  Explicit Anthropic deployments must configure an available Claude model.
- Legacy submission persistence now uses the supplied SQLAlchemy transaction,
  accepts string/dictionary logs, and withholds completion until saving succeeds.
  Legacy streaming currently buffers events while the challenge runs.
- Legacy completion requires explicit wins. Heist's consolation points no longer
  unlock levels; its steps are counted. Trivia awards 100 points once. Giga Chad
  requires a partial/complete break, not wobble points. Giga Chad and Telephone
  reject malformed, out-of-range or inconsistent model judgments. Failed provider
  calls cannot become invented responses or saved results in these repaired paths.
- Legacy progress queries the player's own entries directly, including scores
  below the top 1000. Difficulty order comes from game definitions. Unknown legacy
  difficulty labels are rejected before execution; default labels are saved correctly.
  Arena and Debate retain all three levels, including Expert, with server unlocks.

- Firewall, Giga Chad, Telephone, Heist, Arena and Debate now share persisted runs,
  actions and the common page. Multi-agent games use start/continue stages with
  optional automatic continuation. Reloads and errors pause, and every successful
  stage is durable. Strict judgments fail closed. Arena damage and Debate scores
  are bounded; ties cannot award a win.
- Heist now displays the complication and exact win conditions before play. Its
  unexplained random luck roll is removed; crew majority and complication
  approval determine the outcome alongside the stated plan requirements.

## Verification

Staged migration checkpoint: **434 PostgreSQL backend checks and 15 browser
checks passed**; 13 paid-model experiments skipped. Additional transport-budget
coverage and live calibration are being verified before the next checkpoint. [Verification and independent-review status](verification.md).
The spending-cap review and stateful-game review both passed their scoped
independent checks. Legacy scoring review also passed after repairing its confirmed Expert-level
regression and browser win inference. Details are in the verification log.

Run deterministic backend checks with:

```sh
uv venv --python 3.11
uv pip sync requirements-test.txt
pytest tests/runtime tests/api tests/challenges tests/difficulty
```

PostgreSQL serialization tests require a disposable local database named
`jankyard_recovery_test`. The fixture rejects other database names and remote hosts:

```sh
JANKYARD_TEST_DATABASE_URL=postgresql+psycopg2://USER@127.0.0.1:PORT/jankyard_recovery_test \
  pytest tests/runtime tests/api tests/challenges tests/difficulty
```

Browser tests start their own local ASGI server and temporary database; only the
provider is replaced. Run `playwright install chromium`, then `pytest tests/browser`.
On macOS an installed browser can be selected with `JANKYARD_BROWSER_EXECUTABLE`.
The desktop/mobile screenshots in this folder come from these tests.

`model-smoke.json` records eight small real-provider requests using only the existing
project API key. It confirms availability, an actual level-one bypass, and negative
controls. It does **not** establish level-two/three beatability or statistical
success rates. Acceptance fixtures establish detector behavior separately.
`stateful-model-smoke.json` adds eight real requests: narration in Honeypot's first
two levels, three hard-level classifier probes, and testimony for each
Interrogation case. Every request returned a valid outcome; each witness response
met that case's lead requirement. These are compatibility samples, not difficulty
calibration or repeated win-rate estimates. Reproduce with
`RUN_LIVE_MODELS=1 python -m scripts.smoke_stateful`, supplying only the selected
provider key through the environment; the script makes exactly eight bounded calls.

The resolved runtime lock was checked with pip-audit: **zero known advisories**
on 2026-10-31. This does not establish that every application path is secure.
CI now runs backend tests against PostgreSQL, browser journeys and dependency audit.
Old browser suites still target pre-recovery Glitch selectors and are not the new
runtime gate. Paid model experiments are explicitly opt-in.

## Schema and rollout

`python -m app.migrate` adds only `challenge_runs`, `run_turns`, and `run_scores`
to an existing database in one transaction. It changes no existing tables, scores,
users or submissions. It is safe to run repeatedly. For an **empty development**
database only, use `python -m app.migrate --bootstrap`.

Before a future production rollout: take a database backup, validate this additive
migration against a restored copy, run it before switching application workers,
then verify authenticated and guest journeys on staging. PostgreSQL is required
for production concurrency guarantees; SQLite is for development/browser fixtures.
Use a strong production SECRET_KEY, HTTPS and an explicitly trusted reverse proxy.
Gameplay request budgets are per verified player, so a hosting proxy does not
combine their model budgets. Guest provisioning has a separate peer-based budget
(1000/minute and 10000/day by default), configurable with GUEST_SESSIONS_PER_MINUTE
and GUEST_SESSIONS_PER_DAY. A separate site-wide RECOVERED_TURNS_PER_DAY ceiling
(default 1000) limits recovered turn admissions, including failures and retries,
so rotating guest cookies cannot multiply the paid-call budget. All public games
now use this cap. Multi-agent games admit and save each model/judge stage separately,
and the transport rejects a second provider request within one stage. Guest sessions last 30 days; signing in does not merge earlier guest scores.

Rollback can run the prior app against the unchanged historical tables, but doing
so would reopen the old unsafe submission endpoint unless containment is retained.
The additive tables should remain intact; do not delete players' recovered results.

## Still open

- Design stronger Honeypot learning checks: bulk guesses and unique visible
  category prefixes make identification easy. Keep objectives honest about that.
- Calibrate each game/level with repeated real-model attacks and negative controls,
  including replay/resume flows. Model replacement changes difficulty even when
  API compatibility checks pass.
- Exercise production-like migration/rollback and the broader legacy browser suite
  before proposing a release. No release-readiness claim is made here.

See [the two-file contributor guide](../ADDING_CHALLENGES.md).
