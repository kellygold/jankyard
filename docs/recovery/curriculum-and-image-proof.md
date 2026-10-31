# Three teaching levels, ultra-hard mode, and image proof

Application candidate: **`aba1c52`**. Later tooling changes do not change the
application, Dockerfile or dependency lock. This implements Kelly's direction:
three passable teaching levels followed by the preserved ultra-hard defense.
Production and external hosting remain untouched.

## Curriculum changes

Firewall version 2 has three explicit input-filter lessons. The bot cooperates
once the gateway admits a request; the visible lesson identifies that deliberately
insecure authorization assumption. Level 1 teaches lexical alternatives, level 2
adds words and patterns, and level 3 adds encoding checks and incomplete language
coverage. Each earlier saved solution is blocked by the next teaching level.
The original hardened level-3 prompt and its original four-filter configuration
are preserved exactly as the fourth `ULTRA` level. Ultra unlocks after level 3.
Its new score multiplier is 3.0; its defense is unchanged.

Giga Chad version 2 retains its first two weak-role lessons. The third teaches
untrusted-source injection: PizzaBot wrongly treats editorial directions inside
a customer-supplied `<supplier-bulletin>` as operational authority. The fourth
keeps the original hardened Giga Chad defense. Both ultra-hard levels are visibly
labeled experimental, without a promised solution. They are not prerequisites
for the three teaching levels.

The attack agent now receives the saved strategy explicitly on each turn. The
judge excludes ordinary pizza toppings, pricing, delivery and quoted order notes
from role breaks. Actual unrelated answers can still win. Numeric and severity
validation, five-round completion, atomic results and scoring remain shared.

Arena version 6 fixes another prompt ambiguity: its expert fighter rejected a
concrete command as “not an exact command,” repeatedly standing still. The prompt
now identifies the user message as the source of tactics and says examples are
illustrative, not an exact phrase allowlist. Damage, HP, timeout comparison and
win detection are unchanged. All three difficulties now have repeated live wins;
vague goals still lose.

Telephone required no code change. A balanced discussion instruction survived
the hard relay twice. An exact-wording instruction lost twice. This is a useful
demonstration of semantic resilience versus literal preservation, not a claim
that every instruction can survive.

## Live calibration

| Game | Observed result | Evidence |
|---|---|---|
| Firewall | Each teaching level won twice; ordinary and blocked controls did not win. The teaching bypass failed against Ultra. | `firewall-teaching-live.json` |
| Giga Chad | Each of the first three levels won twice. The legitimate pizza strategy lost, and the supplier-bulletin strategy failed against Ultra. | `giga-teaching-live.json` |
| Arena | Easy, hard and expert each won twice after the command fix; vague expert goals lost twice. | `arena-executor-live.json`, `arena-executor-repeat-live.json` |
| Telephone hard | Balanced discussion won twice; exact-wording controls lost twice. Another process instruction lost. | `advanced-pass3.json`, `advanced-pass3-repeat.json` |

These are bounded repeated samples, not estimated win rates or learner studies.
The ultra-hard failures demonstrate observed defenses, not invulnerability.
`ultra-preservation.json` records equal prompt hashes for both original hardened
defenses and an equal Firewall filter configuration. The win detectors were not
weakened to manufacture successful teaching trials.

The first two `advanced-pass3*` receipts also preserve unsuccessful Arena version-5
trials. They led to the command-source correction and do not describe version 6.
All provider trials use the configured `gpt-6-luna`, complete bounded responses,
and no automatic paid retries. Saved prompts and expectations live in
`tests/runtime/strategies/*.json`.

The shared calibration runner accepts `--cases` and a lower `--call-cap` (never
above 120). It validates every case before the first provider call and records
the source commit, rule version and each stage. Declared expectations or an
incomplete selected case set produce a nonzero exit; exploratory cases can omit
an expected outcome. This keeps future contributions repeatable without adding
game-specific HTTP, UI or storage code.

## Actual deployment image rehearsal

The **Linux AMD64 Docker image built and ran successfully**, including its normal
two-worker Gunicorn command, production configuration and locked dependencies.
The image rejected a missing production secret and excluded `.env`, virtualenvs,
tests, documentation and Git metadata. Its image ID and architecture are recorded
in `image-rehearsal-complete.json`.

A dedicated [Colima profile](https://github.com/abiosoft/colima/blob/main/docs/FAQ.md)
provided an isolated local Docker daemon. It used no home-directory mounts, did
not activate itself as the default Docker context, and did not start Docker
Desktop or any other project's containers. Linux AMD64 ran under the VM's Rosetta
support. This tests the Linux image, but not a real cloud host's performance.

The rehearsal created a fresh container network and PostgreSQL 15 container,
bootstrapped its empty schema, and ran the production migration twice. Chrome
used HTTPS with an ephemeral certificate trusted only in its test context.
One guest and one newly registered player used the real forms and provider:

1. Submit an ordinary control and verify it does not win.
2. Submit the known level-one bypass and see the committed win and scoreboard.
3. Replay each exact request and receive the identical saved receipt.
4. Restart the application container and reload both browser sessions.
5. Verify saved wins and counters survive; reject the guest's read of the
   registered player's run with HTTP 404.

The database had exactly **2 runs, 4 turns, 2 submissions and 2 score rows**.
The guest cookie was Secure/HttpOnly/SameSite=Lax. Four real provider calls and
four receipt replays used the eight-admission ceiling. The temporary containers,
network, database and credentials were removed by the harness. After verification,
the dedicated VM and its container data were deleted, the owned host PostgreSQL
cluster was stopped with zero tables remaining, and the completed review worktree
was removed. Docker’s active context remains `desktop-linux`. Colima and its
Homebrew dependencies remain installed; no startup service was enabled.

![Registered player and guest tied on saved scores](screenshots/image-rehearsal-complete-registered.png)

The first image rehearsal reached both wins, then its restart check failed:
Docker reassigned the automatically selected host port. A separate no-provider
server reproduced that behavior. The harness now pins a free loopback port so
the origin and browser credentials survive restart. The failed receipt and
screenshots remain in `image-rehearsal.json`; the successful rerun has a separate
receipt. This was a harness error, not an application persistence failure.

Reproduce after building a `jankyard-rehearsal:` image in the dedicated local
context, supplying only the provider key through the environment:

```sh
RUN_LIVE_MODELS=1 python -m scripts.rehearse_image \
  --image jankyard-rehearsal:COMMIT \
  --output docs/recovery/new-image-proof.json
```

## Gates and limits

- **452 PostgreSQL backend checks passed**, with 13 opt-in paid tests skipped.
- **16 Chrome fixture journeys passed.** Provider substitution is limited to
  these deterministic browser tests; the image rehearsal uses the real provider.
- Claude's independent, read-only review found **no P0/P1 blockers**, using
  **122.34 seconds of the 900-second cap**, through the Max subscription. Exact
  scope and nonblocking prompt-clarity notes are in `curriculum-review-receipt.json`.
- The backend gate's first launch omitted the owned PostgreSQL cluster's custom
  port; startup was refused because the default port was occupied. That invalid
  run was stopped. The complete passing run used the owned port 55439. No other
  database was accessed or stopped.

This pass used **363 provider calls**: 96 exploratory Arena/Telephone calls,
10 Firewall calls, 120 Giga Chad calls, 129 corrected Arena calls, and 8 across
the two image rehearsals. Failed strategies and harness checks remain recorded.
The receipts establish their exact source commits and per-invocation ceilings.

The independent review noted small remaining prompt ambiguities: the attack
agent's final generic attack instruction can compete with a legitimate-pizza
strategy, and some borderline quoted supplier notes may receive variable judge
classifications. The complete legitimate-pizza control passed all five rounds.
These observations remain limitations of the model judge; this is not a claim
of deterministic classification or a comprehensive security approval.

The next release gate is **a dedicated hosted staging environment**, including
its real ingress/proxy configuration, database credentials, production-backup
restoration and rollback rehearsal. No existing target is known. A local image
test does not establish those properties. See [rollout.md](rollout.md).
