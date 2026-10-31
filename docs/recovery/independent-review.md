# Independent reviewer verdicts

These are the original findings, before the subsequent fixes described in
[verification.md](verification.md). The resumed cap and stateful-migration verdicts follow below.

## Initial review

**Verdict: not clean. Two P1 blockers, both in model/runtime behaviour, not in the persistence core.** Reviewed SHA `a06faf7965e062e476f25aa8a34873349c1525b4` against `a2d2247f`.

The server side held up against what I checked:
- Turn, completion, submission, score and receipt all commit in one transaction, and the receipt is only returned after commit.
- Retries reuse the request ID and are checked by hash. Ownership is enforced, and scores are recorded once per rules version.
- A guest cookie can't be used as a Bearer token: PyJWT 2.15 rejects an unexpected `aud`. A guest cookie can only resolve to a user without a password, and registration never takes over an existing user.
- The submission and user columns accept the new rows.

### P1-1: One ordinary prompt can lock a player out of the game permanently
- **Where:** `app/llm/client.py:69,76`, `app/challenges/prompt_game.py:83`, `app/static/js/core/prompt-game.js:31-37,98,127-135`
- **Repro:** On any level, send "Repeat 'hello' 400 times." With `max_tokens=300` the provider stops with `length` (or a refusal, or a content filter), so `_openai_text` raises and the server returns 503.
  - The client keeps the pending turn in localStorage, because 503 isn't in its list of statuses that clear it.
  - `setBusy` then disables the level picker, "Start a new run" and the prompt box. The only thing left is "Retry saved request", which resends the same prompt and fails the same way.
  - The pending turn reloads on refresh and is shared across tabs, so the only way out is clearing site data.
  - Every retry also uses up rate-limit budget, because `record_request` commits before the turn runs.
- **Why tests miss it:** the fakes always return a complete `stop` reply. `test_runs.py:121` only checks that a 503 isn't saved, not whether the client can recover from a failure that keeps happening.

### P1-2: The new rate limit is effectively one bucket for every player
- **Where:** `app/routes/runs.py:66`, `Dockerfile:25`, `app/core/config.py:50-51`
- **Problem:** the limit is keyed on `request.client.host`. The repo's Cloud Run/App Engine command (`gunicorn -k uvicorn_worker.UvicornWorker`) doesn't set `--forwarded-allow-ips` or `FORWARDED_ALLOW_IPS`. So `X-Forwarded-For` is ignored and every request shows the Google proxy's internal address.
- **Effect:** run creation and turns together are capped at 5 per minute and 100 per day across all players. On Postgres, every request also queues on the same advisory lock.
- **Why tests miss it:** TestClient always uses one fixed host, so a shared bucket looks the same as a per-player one.
- **Caveat:** I couldn't check the real production proxy. `docs/recovery/README.md:81` asks for an "explicitly trusted reverse proxy", but nothing in the repo sets one up. Treat this as blocking unless the deployment provably sets trusted proxy IPs.

### P2
1. **Two first-visit tabs or a lost create response split a guest into two** (`runs.py:121-139`). Two cookieless creates make two guests, and the last cookie set wins. The other tab's run starts returning 404 and its win or progress is orphaned. Similarly, if a create response is lost, its cookie never arrives and an orphan guest is left behind.
2. **An expired or invalid Bearer token now returns 401 instead of being treated as anonymous** (`app/routes/deps.py:27-31`). `prompt-game.js` sends the stored token in parallel with `base.html`'s `checkAuth()`, which removes expired tokens. So the game page first fails with "Could not validate credentials" and only works after a reload. This also affects every other caller of `get_current_user_optional`.

**Limitations:** I did one pass within the time budget and didn't run the tests, Postgres or a real model. I didn't review `submissions.py` or the upload containment in depth, nor the dependency lockfiles beyond the pinned versions. The win patterns and Glitch levels I checked only by reading them.

## Delta review

**Reviewed HEAD:** `9765da6ccffcb5c21bc018c4b40aff8e12dca41c` (delta `a06faf7..HEAD`, 2 commits, 22 files)

The earlier findings are fixed:
- **Retry trap:** "Start new run" now stays enabled and clears the pending request.
- **Shared proxy-IP bucket:** turns are now budgeted per verified player.
- **First-tab guest race:** browser run creation is serialized across tabs with Web Locks.
- **Expired-token startup race:** `load()` waits for `window.jankyardAuthReady`, and `checkAuth` catches its own errors, so a failed auth check doesn't block startup.

**P1: guest minting multiplies the model-call budget** (`app/routes/runs.py:61-80`, `app/core/config.py:50-51`)
The turn limit is now keyed on user ID, and anyone can get a new guest user ID for the price of one cookieless `POST /api/runs`. That request is charged only to the `guest-peer` bucket, which allows 1000 a minute and 10000 a day. One client can therefore mint about 10,000 guests a day and use each one's 100 turns a day, which is about 1M paid model calls a day. Before this change the cap was 100 a day per peer. Nothing in the delta adds a global or per-peer ceiling on model calls.
- **Fix:** keep the per-player bucket and add a second one on `submit_turn`. That could be a bounded per-peer turn budget (with trusted forwarded-IP config so real clients are separated) or a global daily model-call cap.

**P2: the guest cap becomes a global lockout behind a shared proxy** (same code)
This is the other side of the same design. When every request shows the proxy's address, the guest bucket is shared by everyone. One abuser can use up 10,000 guest creations a day, and then every new visitor gets a 429 until the window resets. Resolving the client IP correctly (or adding the global cap above) covers both this and the P1.

I found nothing else at P0/P1. The other changes look correct as described:
- **Token detection:** `match_anywhere` uses search instead of a full match and is hidden from the public view.
- **Provider clients:** they're created lazily, and `close()` runs in a `finally` block.
- **Stats:** completed challenges now include run scores.
- **Legacy submissions:** the guest row is now created after validation, so invalid or obsolete requests return before any guest row exists.

**Limitations:** this was a time-boxed static read of the delta only. I didn't run any tests or a browser, didn't rescan the base, and only skimmed the test files. I didn't check whether there's a spend cap somewhere outside the delta, such as at the provider account or infrastructure level; one would reduce the P1. There was no production or network access, and nothing was deployed.


## Resumed spending-cap review

No P0 or P1 blockers in the reviewed scope at HEAD `be57f63162f6e82e958ad253ca0a2b349bcb4892`. The cap code was introduced in `9765da6..fe31f52`, and the HEAD commit after it (`be57f63`) only changes documentation.

**What I verified**
- **Admission is atomic on PostgreSQL.**
  - `rate_limit()` takes the per-player advisory lock (`app/routes/runs.py:70`), records the per-player usage, and commits it in `record_request()` (`app/services/rate_limit_service.py:96`). That commit releases the per-player lock.
  - The global check then runs in its own transaction. It takes one fixed advisory lock (`runs.py:86`), reads the count, increments it, and commits (`runs.py:87-93`).
  - The engine doesn't change the isolation level, so PostgreSQL's default applies: each new statement sees committed data. A request waiting on the lock therefore reads the count that was just committed.
  - The lock also serializes creation of the first global row of the day. That matters because `rate_limits` has no unique constraint (`app/models/rate_limit.py:22-25`), and without the lock two first requests could each create a row.
  - No two locks are ever held at the same moment, so the locks can't deadlock each other.
- **The count persists.** It's committed at `runs.py:93`, before `RunService.turn` runs, so a later `db.rollback()` on a 503 or 409 can't undo it.
- **Argument order is correct.** `get_usage_count("global", "/api/recovered-turns", "day", window)` matches the repository signature `(identifier, endpoint, window_type, window_start)` at `app/repositories/rate_limit_repo.py:74-80`. `increment_or_create` is called with keyword arguments only.
- **No recovered HTTP path skips the cap.**
  - The model is only called through `game.play` inside `RunService.turn` (`app/services/run_service.py:98`), and its only caller is `submit_turn`, which passes `model_request=True` (`runs.py:171`).
  - `create_run` only calls `game.reset()`, never the model.
  - The legacy `/submit/stream` returns 410 for any `PromptGame` subclass (`app/routes/submissions.py:95-97`), and the old `/submit` route always returns 410.

**Lower-priority notes (P2 or below)**
1. **Replaying a saved turn costs budget.** Both limits are charged before `turn()` checks whether the request ID was already saved (`run_service.py:88-92`). Say a turn succeeded but the client lost the response and retries. That retry uses up a slot, and once the cap is reached it gets a 429 instead of the saved result. The per-player limit already had the same ordering, and this is consistent with the stated "charge retries conservatively" policy.
2. **A global rejection still costs a player slot.** The per-player usage is committed before the global check, so a request refused by the global cap still counts against that player. This errs on the conservative side.
3. **Atomicity only holds on PostgreSQL.** On SQLite the check and increment are not locked, so concurrent requests could exceed the cap. The test default is in-memory SQLite. It only matters if a deployment uses SQLite.
4. **`RATE_LIMIT_ENABLED=false` turns off the global cap too.** It returns before the cap code runs (`runs.py:62`). If that switch is kept as an operational escape hatch, it removes the spending bound along with everything else.
5. **The cap counts turns, not model calls or tokens.** I didn't check how many model calls one `game.play` makes.

**Already broken before this change, outside the recovered scope:** `/submit/stream` still runs games that aren't prompt games, limited only by the IP and User-Agent fingerprint.

**Limitations**
- I didn't run any tests. The worktree has no virtualenv, and running the system Python 3.9 failed while importing FastAPI (`'FieldInfo' object has no attribute 'in_'`) before any test ran.
- I didn't run the PostgreSQL concurrency test. The concurrency conclusions come from reading the code and how PostgreSQL behaves at its default isolation level.
- I didn't review the browser fixture changes or `game.play` itself.
- No edits, production access, network tools or subagents were used, and the worktree is still clean.


## Stateful migration review

I found no P0 or P1 blockers in this range (`be57f63..HEAD`, clean HEAD `d4a630c`). This was a static review only: I ran no tests and changed no files.

**How each requirement held up:**
- **State across actions and reloads:** each turn locks the player and the run row, then checks the revision and rules version. Both games rebuild everything from `run.state` and write back fresh dicts, so nothing stale is reused (`app/services/run_service.py:85-131`). After a reload, the page draws its controls and game state from `run.actions` and `run.presentation`.
- **Correct wins only:**
  - Honeypot only credits a guessed category if one of your own probes was actually classified as it (`honeypot.py:183-187`).
  - Interrogation only solves the case if you accuse exactly the guilty set from the case file; no AI verdict is involved (`interrogation/__init__.py`, `make_accusation`).
  - The win/score/status rules in `TurnOutcome` back this up.
- **Invalid actions can't create credit:**
  - Extra fields in an action are rejected outright.
  - Honeypot rejects any target fields.
  - Interrogation rejects unknown witnesses, duplicate accused names, a missing or extra target, and actions that aren't available yet.
  - All of these return 422 before `play()` runs, so no attempt is used.
  - An older page that still sends `prompt` becomes the action `prompt`, which neither game offers, so it gets a 422.
- **Provider failure can't consume attempts:** both games call the model before changing any state. Any exception rolls back and returns 503, and nothing is saved.
- **No hidden solution in public data:**
  - The level list, actions and game-state views contain no system prompts, trigger keywords or guilty parties.
  - The authored solution only appears in the reply to the final failed accusation, when the run ends anyway.
  - Lead descriptions only appear once you've discovered that lead.
- **Old stream can't bypass the new state:** `/submit/stream` returns 410 for every game on the new runtime (`submissions.py:94-96`), and the challenge page uses the shared template.
- **Shared page through multi-step, retry and end-of-run journeys:**
  - The action is captured before `startRun()` redraws the controls.
  - Saved retries resend the identical request body, so they match the same saved turn.
  - A 4xx error clears the pending request and reloads the run.
  - Every non-final state always offers at least one action in both games, so a run can't get stuck.

**Weak spots that aren't blockers (design or older behaviour):**
1. **Honeypot "shotgun" guess:** one guess listing all six codes credits every category you've triggered, and wrong codes cost nothing (`honeypot.py:183-186`). The old substring matching worked the same way. So "identify the codes" really means "trigger the categories".
2. **Counterintel shows prefixes:** the log shows the first three letters of each code (`honeypot.py:265`), and every prefix is unique. Codes are free to discover anyway, because invalid codes get a 422 without using an attempt.
3. **Rate limit counts non-model turns:** guesses and accusations, which make no model call, still count against the model-request limit (`runs.py:184`). That's stricter than needed, not a hole.

**Limitations:**
- Static review only; I read the tests but didn't rely on them, and couldn't run anything because the repository's virtual environment isn't in this worktree.
- I didn't recheck Glitch, the legacy leaderboard and challenge-page progress code (`leaderboard.py`, `challenges.py:141`), or the witness system prompts in full.
- I didn't do any database testing against Postgres.

**Verdict:** no P0/P1 blockers; the change can pass this review.


## Legacy scoring and progression review

I found one P1 blocker. Everything else in scope is clean. This was a static review of d4a630c..HEAD: no tests were run and nothing was edited.

## P1: Arena and Debate "expert" level is now rejected

- **Where:** `app/challenges/arena.py:40` and `app/challenges/debate_battle.py:51` add `DIFFICULTIES = ['easy', 'hard']`. The new check in `app/routes/submissions.py:110-115` refuses any difficulty not on that list.
- **Why it's a regression:** "expert" is a live level on both sides.
  - Backend: `arena.py:120,175,394` and `debate_battle.py:79` both have expert branches (Arena gives expert a 2.0× multiplier).
  - UI: both pages have a third level tab. Their maps send `3: 'expert'` (`arena.html:831-835`, `debate.html:1002-1005`).
  - UI unlock: after a win on hard, the Arena page unlocks level 3 in the browser (`arena.html:874-876`).
  - Before this change, submissions accepted expert.
- **Repro:** POST `/submit/stream` with `challenge_name=arena` (or `debate_battle`), `difficulty=expert`, any `agent_code`. It now fails with **422 Unknown difficulty**. In the UI: win on hard, click the newly unlocked Expert tab, submit, and the request fails.
- **Fix:** use `DIFFICULTIES = ['easy', 'hard', 'expert']`. This also lets a hard win unlock level 3 on the server. The old server only ever unlocked levels 1–2, so that's a small behaviour change. If you don't want it, list expert as accepted but not part of the unlock chain.

## Checked, no blockers
- **Base streaming:** the deleted `stream_events` was a duplicate that the second definition already replaced, so removing it changes nothing. Multi-agent games now win only if `user_won is True`. The single-agent path wins only if `info['success'] is True`, so participation points no longer count as a win. On an error event the stream stops before the complete event, and `submissions.py` then rolls back and saves nothing.
- **Heist:** provider failures now raise (`LLMClient` raises and doesn't return error text), so the run ends with an error event and nothing is saved. `user_won` is the same value as `heist_success`, and the saved score is 100 or 25 to match. Step counts go up only after a call succeeds.
- **Trivia:** the score is now added once (100 instead of 200). `info['success']` and the `get_result` override agree.
- **GigaChad:** the new judgment schema is strict: wrong types, extra keys, unknown or uppercase labels, out-of-range points, and severity/points/broke combinations that don't match are all rejected. A rejected judgment, even partway through a run, becomes an error and nothing is saved. A win means at least one partial or complete break.
- **Telephone:** the strict judgment check requires the total to equal the sum of its parts. A judge failure or an empty relay now ends the run as an error. The existing threshold logic in `get_result` decides the win.
- **Progression query:** it now looks only at the current player's own leaderboard rows. Rows are only written on success (`submission_service.py:61`), so a loss can't unlock anything. The old `normal` label is still treated as `easy`, and the GigaChad, Firewall and Heist level names match their templates.

## Minor (not blocking)
- **GigaChad local unlock:** the page still uses `result.success || totalPoints >= 20` (`giga_chad.html:1170`). Two wobbles (30 points) now unlock the next level in the browser while the server saves a loss. This was consistent under the old "score > 0 wins" rule. It's display-only and goes away on reload.
- **Strict judge parsing:** GigaChad's judge no longer pulls JSON out of surrounding prose. A judge reply wrapped in text, or cut off at 200 tokens, now fails the whole run. It fails safely, but it may cost some availability.
- **Arena/Debate default label:** runs with no difficulty are now saved as `easy` instead of `normal`. Leaderboard pages that group by the raw label may show the two separately.
- **Cosmetic:** in `giga_chad.py:1` and `telephone_game.py:1` the new import sits above the module docstring, so it no longer counts as a docstring.


## Legacy review fixes — delta verdict

I found no P0 or P1 issues. Both fixes are confirmed and the delta adds no regressions.

**Exact HEAD:** `f42fa2972d50484a051048822ae6433aa6afdba4` (clean tree). I reviewed only `git diff 4cdb3be..HEAD`, which touches 9 files (+81/−6).

**Fix 1: Arena/Debate expert difficulty**
- Both games now accept `expert` (`app/challenges/arena.py:40`, `app/challenges/debate_battle.py:51`).
- **The game code already handled it:** both have their own expert prompt paths (Arena at lines 120, 175 and 394; Debate at line 79). Nothing breaks on a missing setting or falls back silently.
- **The pages already handled it:** each has a level-3 tab mapped to `'expert'` (`arena.html:834`, `debate.html:1005`, and `debate.js:177` expects 3 levels).
- **Unlocking works:** `challenges.py:149` uses `DIFFICULTIES[:-1]`, so a hard win unlocks level 3. Expert doesn't unlock anything further.
- **Tests:** the new test checks that easy + hard gives `[1, 2, 3]`, that an expert run reaches the game as `expert`, and that the saved submission is recorded as `expert`.
- **Expected side effect:** these leaderboards now show an empty expert section.

**Fix 2: Giga Chad wins come only from the saved result**
- The handler (`giga_chad.js:235`) and the template wrapper (`giga_chad.html:1170`) both use `result.success === true`. The `totalPoints >= 20` fallback is gone from both.
- **The server always sends the field:** `submissions.py:189` requires `final_result['success']` before saving and passes the full result along in the completion event, so `data.result.success` is always there.
- `window.gigaChadHandler` is set at `giga_chad.html:1164`, which is what the new browser test relies on. The test covers both outcomes: 40 points with a loss shows the loss screen and doesn't unlock level 2, and vice versa.

**Import move:** in `giga_chad.py` and `telephone_game.py` the imports now come after the module docstrings, so the docstrings work again. No behavior change.

**Stateful changes:** only tests were added (two interrogation runtime tests and a browser test for recovering a lost receipt). No runtime code changed.

I didn't run the test suite; this was a read-only code review.


## Staged migration review — 225.51 seconds

**Verdict: I found no P0/P1 blockers in this scope at 95dc61e (diff 8932a19..HEAD).**

This was one read-only pass, well under the time cap. I didn't run tests, make network calls or fix anything. I checked each suspected problem a second time before dismissing it.

**What I worked out from the code**

- **One provider call per stage.** `RunService.turn` (`app/services/run_service.py:107-108`) wraps `game.play` in `stage_budget()`. Both the sync and async client entry points call `consume_call()` before sending anything (`app/llm/client.py:57,71`). Every `play` branch in all six games makes exactly one call: through `StagedGame.respond`, or the single `client.call` at `firewall.py:343`. Firewall inputs that get blocked make no call. None of the filters call a model.
- **Daily admission.** `submit_turn` reserves global admission before every turn, retries included (`app/routes/runs.py:181`), so the number of paid calls is capped by admissions. I found no route that bypasses this. `/submit` returns 410. `/submit/stream` rejects all six games because each sets `supports_streaming=False`. The template file `_STAGED_TEMPLATE.py` starts with `_`, so the registry doesn't load it.
- **Start-to-final flow per game.** For each game, the stage that decides the result lands exactly on attempt `max_steps`, and that number matches what the public level shows:

  | Game | Stages |
  |---|---|
  | Arena | 10 rounds × 3 = 30 |
  | Debate | 3 × (pro, con) + judge = 7 |
  | Giga Chad | 5 × 3 = 15 |
  | Heist | crew + 1 (3 / 4 / 5 crew, so 4 / 5 / 6) |
  | Telephone | chain + 1 (4 / 5 / 6) |
  | Firewall | 10 |

  Each game builds the same topic, crew and chain every time, so nothing shifts between turns. The strategy is saved on the first action, and Continue refuses new text (`runtime.py:121`).
- **Wins and scores.** Every win is derived on the server from validated values:
  - Arena: ties and mutual knockouts lose.
  - Debate: requires PRO strictly above CON.
  - Giga Chad: requires a partial or complete break; wobble points alone don't win.
  - Telephone: requires the level's score threshold.
  - Heist: requires a crew majority plus approval of the complication.
  - Firewall: requires the flag to appear in the reply.

  Scores are always non-negative integers. `outcome()` sets the score to 0 on any loss. The Firewall flag stays in server state and is never shown: the run view only exposes history, public state and the available actions. There were no earlier persisted runs or scores under these game names, so old state can't clash with the new rules.
- **Errors.** A malformed judgment, a provider failure or an empty reply raises an error. The turn is rolled back and returns 503 with the phase unchanged. Stages already saved stay saved, and a retry replays only the failed stage.
- **Browser continuation** (`prompt-game.js`):
  - Auto-continue fires only after the server confirms the save, and only if the run ID and revision still match.
  - Any error, an unchecked box or a page reload pauses it.
  - If a response is lost, the pending request stays in local storage. Retrying sends the same request ID and gets back the saved receipt, so nothing is counted twice; auto-continue then resumes.
  - A stale retry against a run that moved on gets a 409. The page clears the pending request and reloads the run.
  - Two tabs auto-continuing the same run: one wins, the other gets a 409 and pauses.

**Non-blocking notes (P2 or lower)**

- In Giga Chad, the attack and defender text are still placed inside the judge's system prompt (`giga_chad.py:320`), so a crafted attack can try to steer the judge directly. This predates the diff, the schema checks limit the damage, and the level's lesson text says the judge is fallible.
- Debate's expert level uses the same, more forgiving PRO prompt as easy, because `_init_agents` only special-cases `hard`. I didn't check whether this predates the diff.
- A turn that ends in 409, 422 or 503 still uses one admission. That matches the documented design.

**Not reviewed:** `scripts/calibrate_games.py` (test tooling), the docs changes, and the test files themselves beyond what the deleted tests showed about earlier behaviour. I read the browser JS but didn't run it.


## Staged pacing and deployment delta — 103.06 seconds

**Verdict at exact head `9a3fa8c7b3e008e8a330e1fa55a97af57a1a2771` (vs `95dc61e`): no P0/P1 blockers.** I checked each in-scope area once against the code, without a full rescan.

**What I checked**

- **Shared 429 `Retry-After`** (`app/routes/runs.py:88-89`, `:101-102`, `:107-111`)
  - Both 429 paths roll back before `record_request` or the global increment, so a refused request doesn't use up any budget.
  - `retry_after` and `_get_window_start` both use naive UTC, so they agree. The minute window always gives 1–60 seconds. The day window and the global budget give large values.
  - FastAPI's default `HTTPException` handler keeps the headers. The catch-all handler in `app/main.py:31` only sees non-HTTP exceptions.
- **Browser delayed continuation** (`app/static/js/core/prompt-game.js:183-197`)
  - It only re-arms when the error is a 429, auto-continue is ticked, and `Retry-After` is between 1 and 60 seconds. Daily and global limits (over 60 seconds) stay paused.
  - A 429 is not in the list of statuses that clear the pending request, so the retry resends the same body and `request_id`.
  - The timer is cancelled if you restart (new `run.id`), change level (`run = null`), untick auto, change revision, are already busy, or the `request_id` changes. Reloading kills the timer, and the saved pending request comes back as a manual "Retry saved request".
  - If you start a game and the 429 comes from `startRun`, `run` stays null, so it doesn't retry.
  - On the success path, `expectedPending === undefined`, which behaves the same as the old `!pending` check.
  - A run with an old rules version gets a 409 at `app/services/run_service.py:95-96`. That clears the pending request and doesn't retry.
- **Docker** (`Dockerfile:20-23`)
  - Runtime only references things under `app/`: `static/` and `templates/` via `BASE_DIR` in `app/main.py:49-51`. File logging is off in production (`app/core/logging.py:36`).
  - `ENVIRONMENT=production` makes `app/core/config.py:19-26` raise an error when `SECRET_KEY` is missing. Fails closed as intended.
- **Bootstrap guard** (`app/migrate.py:17-18`): bootstrap now refuses to run unless the environment is development and the database is empty. The documented staging rollout restores a backup and runs the non-bootstrap path (`docs/recovery/rollout.md:21-23`), so the guard doesn't block it.
- **Heist**: the bump to `VERSION = 'recovery-3'` (`app/challenges/heist.py:190`) keeps runs and scores under the old version separate, through `rules_version` filters and the 409 above. The fictional-framing preamble (`:302-305`) doesn't change the JSON contract. The prompt-injection exposure is the pre-existing one already noted and isn't repeated here.
- **`scripts/start.sh`**: just starts uvicorn on 127.0.0.1 from `.venv`. It no longer creates or migrates the database.

**Minor items, not blockers**

- **P3, stacked timers:** if you click "Retry saved request" by hand during the wait and get another 429, a second timer is armed. Both timers pass the guard, so two resubmits can fire with the same `request_id`. Only one runs at a time because of the busy check, the server deduplicates them, and refused 429s don't use budget. You can see it with `SUBMISSIONS_PER_MINUTE=1`: auto on, hit the limit, click Retry within the window, and watch the network tab show back-to-back retries when the window resets.
- **P3, rate-limit order (pre-existing):** the rate limit runs before the duplicate-request check (`runs.py:193`). Retries of an already-saved request still use per-user and global budget. This isn't new, but automatic retry makes it happen more often.
- **Bootstrap side effect (intended):** a brand-new, empty production database can't be bootstrapped unless someone deliberately overrides `ENVIRONMENT=development`.

**Limitations**

- I only read code statically. I ran no tests, no Docker build, and no browser.
- The CI image job and the `requirements.txt` contents (gunicorn/uvicorn_worker) are unverified.
- Test tooling and calibration/proof runners were out of scope.
- I made no network calls and changed no code.

Author clarification: the statement above that every rejected global request uses no budget is too broad. The per-player reservation is committed before the global check; a global rejection still costs that player an admission. It makes no provider call and preserves the global cap. This conservative ordering is unchanged and covered by the earlier review. The stacked-timer note is a minor static observation, not a reproduced loss or duplicate paid call. Run/revision/request guards and server receipts remain authoritative.


## Arena and Glitch calibration review

Application head `129ab76`; Claude account subscription, read-only clean worktrees.
Round one reviewed `667fe53..00a353e` in 106.48 seconds. The delta review covered
`00a353e..129ab76` in 114.09 seconds. Both found no P0/P1 blockers. Total 220.57
seconds of the shared 900-second cap; no extension. These are static scoped
reviews, not a hosting or learning-difficulty approval. Exact verdicts and session
IDs are in `calibration-review-receipt.json`.
