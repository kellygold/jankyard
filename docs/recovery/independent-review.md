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
