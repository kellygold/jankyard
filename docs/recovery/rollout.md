# Staging rollout and rollback

No production deployment or production database access has been performed.
Kelly does not recall an existing staging environment. The accessible cloud-project
name search found no Jankyard match, so staging is treated as unconfigured;
this does not establish that no differently named project exists. Use a dedicated
Jankyard target, never another project’s infrastructure.

The actual Linux AMD64 image now passes a local rehearsal with HTTPS,
production configuration, two Gunicorn workers, PostgreSQL, real-provider guest
and registered-player journeys, secure guest cookies, repeated migration and
container restart/resume. See `image-rehearsal-complete.json`. The isolated VM
used temporary credentials and did not start other projects' containers.
This does not validate external ingress, hosted infrastructure, production-backup
restoration or rollback on that hosting target.

These are the remaining steps for an isolated staging target and then a separately
approved release.

1. Pin the candidate commit and build its image. Runtime code is copied explicitly;
   `.env`, virtualenvs, tests and evidence are excluded. CI builds the image and
   checks production configuration. The Linux AMD64 build and production-mode
   image rehearsal passed locally at `aba1c52`. Pin that image or rebuild and
   rerun the rehearsal when the application or dependencies change.
2. Restore an authorized database backup into an isolated PostgreSQL instance.
   Record its identity and pre-migration historical row counts. Synthetic local
   PostgreSQL tests prove additive migration and rollback compatibility; they do
   not prove a real backup restores correctly.
3. Configure `ENVIRONMENT=production`, a strong random `SECRET_KEY`, the staging
   PostgreSQL `DATABASE_URL`, and a provider key with a separate account budget.
   Set `DEFAULT_LLM_PROVIDER=openai`, `DEFAULT_MODEL=gpt-6-luna`,
   `RATE_LIMIT_ENABLED=true`, `RECOVERED_TURNS_PER_DAY=1000`,
   `SUBMISSIONS_PER_MINUTE=5`, `SUBMISSIONS_PER_DAY=100` explicitly, or choose lower
   staging ceilings. The model can be changed after calibration; scores are scoped
   to its identity. These caps bound admissions, not a currency amount.
4. Run `python -m app.migrate` as a one-off job with the staging configuration.
   Run it twice to verify idempotence. Historical users, submissions and leaderboard
   entries must remain unchanged. Do not use `--bootstrap` on an existing database.
5. Deploy the pinned image to staging, using HTTPS. Configure proxy trust for the
   actual hosting ingress; do not blindly trust all forwarded client addresses.
   Confirm Secure/HttpOnly/SameSite guest cookies, registered login, and peer-based
   guest admission. `/health` is only a process check, not a database readiness check.
6. Exercise a guest and registered journey from the real deployed browser through
   provider output, persisted completion and scoreboard. Test reload, duplicate
   request, provider failure, exhausted loss, and minute/day budget rejection.
   Staged automatic play pauses at the minute limit, then retries the same request;
   long daily waits remain a manual action. Verify legacy score history separately.
7. Rehearse rollback to a **containment-preserving** application image. Retain the
   additive run tables and all recovered results. Never roll back to an image that
   reopens in-process Python submissions. Re-read historical rows and verify the
   containment routes still return 410. Resume a saved run after rolling forward.
8. Preserve target revision, synthetic run/request IDs, provider receipts, counts,
   screenshots and cleanup results. Remove only synthetic test identities/state;
   do not delete historical or recovered player data. Publish a release decision
   only after the staging proof and independent review both complete.

Required external values are not committed: real database URL, provider key,
strong secret, hosting ingress/proxy policy, backup identity and staging URL.
No claim is made that these are configured. Jankyard is unrelated to TeeFox or
Golf.AI; their environments must not be used for this rehearsal.
