# Cloud Run release and maintenance rollback

The recovery is deployed at https://jankyard.ai and https://www.jankyard.ai.
Kelly authorized the production release on 2026-10-31. Deployment and cleanup
receipts are linked from [PR #4](https://github.com/kellygold/jankyard/pull/4).

## Target and release

- Google Cloud project: `kellygold` (703865103732), region `us-central1`.
- Service: `jankyard`; production revision: `jankyard-recovery-7f3512c`.
- Application commit: `7f3512c533bfb30aba75230a1b1baad6420bbdf8`.
- Immutable image: `us-central1-docker.pkg.dev/kellygold/cloud-run-source-deploy/jankyard-recovery@sha256:70bcb02b6b29caaef277da0c4a7cd75ea32bc9a78f232b58e6faf834e0917acf`.
- Production Neon project: `wispy-lake-18998260`, branch `br-blue-glitter-aev34tad`.
- Other applications share the cloud project. Always specify the project, account,
  region and exact service; never use the global gcloud default for this release.

The production database backup was restored into a separate Neon branch. Two
additive migrations preserved every historical table hash. The private Cloud Run
staging service passed real-provider guest/registered journeys, replay, reload,
ownership, scoreboard and maintenance/forward traffic-switch checks. Production
then passed its own no-traffic model/persistence check and both normal browser
journeys on the canonical domain. Historical player records are preserved.

The obsolete hidden trivia streaming writer was discovered during the hosted
review and removed. Both `/submit` and `/submit/stream` now return 410 before
parsing submissions or creating accounts. All nine public games use `/api/runs`.

## Runtime settings

`ENVIRONMENT=production`, `DEFAULT_LLM_PROVIDER=openai`,
`DEFAULT_MODEL=gpt-6-luna`, `RATE_LIMIT_ENABLED=true`,
`RECOVERED_TURNS_PER_DAY=1000`, `SUBMISSIONS_PER_MINUTE=40`,
`SUBMISSIONS_PER_DAY=100`, `GUEST_SESSIONS_PER_MINUTE=1000`,
`GUEST_SESSIONS_PER_DAY=10000`, `FORWARDED_ALLOW_IPS=127.0.0.1`.

The existing production signing secret and provider credentials are preserved.
These caps count admissions, not currency; retries conservatively consume an
admission even when a stored receipt avoids another provider call.
Cloud Run exposes the shared peer `169.254.169.126`. Forwarded client headers
are deliberately untrusted. Guest provisioning shares a site-wide peer bucket;
playing budgets use verified player IDs plus an independent global paid cap.

The minute allowance was raised from 5 to 40 after a real GigaChad run stopped
at round two. Each internal agent stage consumes one admission; GigaChad needs
15 stages and Arena can need 30, plus run creation. Daily caps remain unchanged.
Release proof must use the production minute/day settings with limiting enabled.
The browser also displays a persistent countdown for short throttles, blocks
premature retries, and reuses the same request when the window resets. Reload
preserves the cooldown but requires explicit continuation.

## Emergency maintenance rollback

The retained revision `jankyard-maintenance-7f3512c` uses the same verified image,
with `RATE_LIMIT_ENABLED=true` and `RECOVERED_TURNS_PER_DAY=0`. It preserves
login, saved progress and history while returning 429 before any model turn.
This is a containment fallback, not a rollback to old application code.

```bash
gcloud run services update-traffic jankyard \
  --project=kellygold --account=kellytgold@gmail.com --region=us-central1 \
  --to-revisions=jankyard-maintenance-7f3512c=100
```

To resume the verified release:

```bash
gcloud run services update-traffic jankyard \
  --project=kellygold --account=kellytgold@gmail.com --region=us-central1 \
  --to-revisions=jankyard-recovery-7f3512c=100
```

Never route back to `jankyard-00011-hiw`: it contains the unsafe Python submission
path. Never restore the pre-release database over newer player data as an
automatic rollback. Preserve the additive run tables. Route by explicit revision,
not `--to-latest`; deploy maintenance first and the candidate last so subsequent
configuration updates inherit the intended active settings. Remove temporary
public candidate tags before completing a release.

Private backups and configuration snapshots are outside git in Kelly's
`~/.local/share/jankyard-release-20261031/` directory. No secrets or database
archives belong in repository evidence. Staging used a separate signing secret,
a 40-admission cap, and IAM authentication; its database copy and service were
temporary. Synthetic player records are removed after verification, while shared
budget counters retain the real test usage.

## Proof limitations

Real model samples demonstrate reproducible lessons, not guaranteed win rates.
The 13 paid opt-in tests skipped in the ordinary suite are covered separately by
bounded live calibration evidence; this was not a load test. The process-only
`/health` endpoint does not establish database readiness: successful persisted
play is the readiness evidence.

The initial private-stage browser harness briefly used a context-wide Google IAM
header that may have accompanied an external image request. Delivery cannot be
established because that initial request trace was not retained. The context was
closed; subsequent tests injected IAM only for the exact staging origin and
blocked external assets. The limitation is documented in the release proof.
Production browser tests required no Google IAM header.
