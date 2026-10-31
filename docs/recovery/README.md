# Recovery checkpoint — 2026-10-31

This branch repairs the shared foundation and moves Glitch onto it. It is not a
claim that every legacy game is repaired or that the platform is ready to deploy.
No production database changes or deployment were performed.

## Implemented

- Public in-process Python submissions return HTTP 410; the web application no
  longer imports the unsafe sandbox. Prompt submissions remain available.
- Glitch uses a shared definition, renderer and persisted run service. Objectives
  explain the exact boundary and acceptance criteria. Straight and curly
  apostrophes work; ordinary approvals and refusals do not win.
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
  configured provider/model. Historic leaderboard rows remain unchanged. Glitch's
  page shows the new scoreboard; the old leaderboard is explicitly labeled.
- There is one registry, including package discovery. New prompt games need a
  definition and positive/negative fixtures, with no custom route, UI or SQL.
- Dependencies are resolved and pinned from direct requirements. Retired OpenAI
  calls and the retired implicit Claude fallback are removed. The default is
  `gpt-6-luna`, with a 45-second request timeout and no automatic paid retries.
  Explicit Anthropic deployments must configure an available Claude model.
- Legacy submission persistence now uses the supplied SQLAlchemy transaction,
  accepts string/dictionary logs, and withholds completion until saving succeeds.
  Legacy streaming currently buffers events while the challenge runs.

## Verification

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
Guest sessions last 30 days; signing in does not merge earlier guest scores.

Rollback can run the prior app against the unchanged historical tables, but doing
so would reopen the old unsafe submission endpoint unless containment is retained.
The additive tables should remain intact; do not delete players' recovered results.

## Still open

- Migrate Honeypot and Interrogation onto persisted state. Fix Honeypot's third-turn
  reveal/hunt budget before calling that game playable.
- Replace the legacy positive-score-means-win inference; fix Heist's failure points
  and step counts, Trivia's duplicate score addition, and bounded judge results.
- Replace legacy progression's top-1000 leaderboard scan with direct owner progress.
  The recovered runtime already queries the owner's complete score set.
- Finish all-game difficulty validation, provider-error handling and shared outcomes.
- Calibrate each game/level with repeated real-model attacks and negative controls,
  including replay/resume flows. Model replacement changes difficulty even when
  API compatibility checks pass.
- Exercise production-like migration/rollback and the broader legacy browser suite
  before proposing a release. No release-readiness claim is made here.

See [the two-file contributor guide](../ADDING_CHALLENGES.md).
