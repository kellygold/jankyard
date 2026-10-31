# Hosted release contract — 2026-10-31

Kelly authorized completing the remaining gates and deploying to production.
The deployment target is the existing `jankyard` Cloud Run service in project
`kellygold` (703865103732), region `us-central1`, serving `jankyard.ai` and
`www.jankyard.ai`. Other services in this shared project are out of scope.
Every cloud command explicitly selects that project, region and Kelly's personal
account; the global gcloud default points elsewhere and must not be changed.

The candidate application is `aba1c52`; `c84b92f` adds calibration tooling and
receipts without changing the application. Cloud Build receives only Dockerfile,
requirements.txt and app/, excluding local environment files and evidence.
Deployments use the resulting immutable Artifact Registry digest.

Production Neon project `wispy-lake-18998260`, branch `br-blue-glitter-aev34tad`,
was identified by matching its connection endpoint with the live Cloud Run
configuration. Staging branch `br-holy-waterfall-aejx3qsx` has a separate endpoint.
A consistent pg_dump backup and table hashes are stored privately outside git.
Restoring this actual backup into staging, followed by two additive migrations,
must preserve all four historical table hashes. Never bootstrap production.

Staging Cloud Run service `jankyard-staging` is IAM-private. Browser requests use
Google's X-Serverless-Authorization header, keeping application Authorization
available for the normal registered login. Copied historical rows must never be
published in screenshots or receipts. Synthetic test records are identified by
exact user/run IDs, and only those records are removed. The staging branch and
service are deleted after release to remove copied production records.

Runtime configuration: ENVIRONMENT=production, DEFAULT_LLM_PROVIDER=openai,
DEFAULT_MODEL=gpt-6-luna, RATE_LIMIT_ENABLED=true, SUBMISSIONS_PER_MINUTE=5,
SUBMISSIONS_PER_DAY=100 in production (20 in staging),
RECOVERED_TURNS_PER_DAY=1000 in production (40 in staging).
Production retains its existing signing secret and provider credential. Staging
uses a distinct signing secret and the authorized provider credential with the
lower application admission ceiling. These are call-admission caps, not currency
limits. Secrets are passed through private mode-0600 files, never committed.

Forwarded address trust initially remains loopback-only; attacker-supplied
forwarding headers must not change guest provisioning accounting. Actual hosted
peer behavior will be measured. Gameplay budgets use verified player IDs and an
independent shared daily cap, regardless of client IP.

The old production revision `jankyard-00011-hiw` is NOT a safe rollback target:
it contains the removed Python execution endpoint. Instead, prepare an emergency
maintenance revision using the same verified image with RECOVERED_TURNS_PER_DAY=0.
This preserves login, saved progress and historical results while blocking model
turns. Rehearse switching traffic to maintenance and forward again, confirming
410 containment, 429 model admission without new persisted turns, unchanged
historical data and run resumption. This is operational containment rollback,
not a claim that a previous application version is compatible.

After staging proof and independent review, migrate production additively and
prepare maintenance/candidate revisions with no traffic. Verify the candidate
through a temporary revision tag using synthetic players, then shift traffic.
Verify apex/www/service URLs, saved outcomes, leaderboard, configured caps and
absence of application errors. Remove temporary public revision tags after the
release, retain the maintenance revision and private backup, and publish exact
revision/digest and cleanup receipts. Never restore the pre-release backup over
new live player data as an automatic rollback.
