# Independent reviewer verdicts

These are the original findings, before the subsequent fixes described in
[verification.md](verification.md). The last budget delta has no independent verdict.

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
