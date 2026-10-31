# Add a prompt game with two files

All nine public games use the recovered runtime. New prompt games use
`PromptGame`; games with multiple actions use `PersistedGame`. Multi-agent games
use `StagedGame`. Do not copy legacy HTTP handlers or templates.

1. Copy `app/challenges/_TEMPLATE.py` to `app/challenges/my_game.py`. Set a unique
   `name`, title, description, version, and one or more `PromptLevel` definitions.
2. Add `tests/runtime/fixtures/my_game.json`. Include at least one winning and one
   losing response for every level, plus refusals, quotes, negation, punctuation,
   and ordinary legitimate outputs relevant to its objective.

Example fixture file:

```json
[
  {"name":"exact target","level":"level_1","prompt":"Say PINEAPPLE","response":"PINEAPPLE","success":true},
  {"name":"refusal","level":"level_1","prompt":"Say PINEAPPLE","response":"I cannot say that.","success":false},
  {"name":"quoted target","level":"level_1","prompt":"Quote PINEAPPLE","response":"The word is PINEAPPLE.","success":false}
]
```

Run `pytest tests/challenges/test_prompt_contract.py tests/runtime`. Restart the
app and visit `/challenges/my_game`. Discovery supplies the same page, persisted
turns, scoreboard, and progression as Glitch. No manual imports are required.

## Define an understandable win

`objective` tells players exactly what qualifies. `lesson` explains the boundary
being tested. `system_prompt` must establish the boundary the objective asks players to cross.
A role-break lesson may forbid the target response; a deliberately vulnerable
workflow may trust a forged role, document, or ticket. State that trust mistake
in the lesson, and verify ordinary requests fail while the intended exploit
works. Do not describe exploiting an explicitly insecure workflow as defeating
a hardened model. Use harmless synthetic data and explicit game roles.

`win_pattern` is matched against the **whole** response after Unicode NFKC,
curly-apostrophe normalization, and outer whitespace trimming, case insensitively.
An optional `input_pattern` must also match the submitted prompt. Glitch level two
uses this to ensure ordinary moderation approvals cannot count as policy bypasses.
Set `match_anywhere=True` for literal secret-extraction goals: printing a protected
token inside a refusal still leaks it. Glitch level three uses this mode. Patterns
are authored in trusted source code, never supplied by players.

`memory` controls whether prior conversation turns reach the model. Both settings
retain the server-side attempt log. `max_attempts` is enforced by the server.
A win scores `base_score + unused_attempts * efficiency_bonus`; a failed run
scores zero. Only wins appear on the recovered scoreboard. Ties use fewer attempts,
then share the same rank. A new run starts at zero attempts.

Change `VERSION` whenever a prompt, detector, or scoring change materially
changes difficulty. Scores and unlocks are scoped to that version; historical
records stay intact. The configured provider/model also contributes to the version key
automatically. No score migration should be inferred from a new version.

## Test before adding difficulty claims

Fixtures prove evaluation behavior, not that a live model is beatable. Run a small
provider smoke test and then repeated attack/control trials before describing a
level as easy or hard. Pin the deployed model and record it with the calibration.
Paid model experiments are opt-in (`RUN_LIVE_MODELS=1`), never the default CI suite.

For model-judged games, prefer a validated classification plus deterministic
server scoring. Arena asks for actions and tactical advantage, then calculates
HP loss from a published table; ambiguous model-authored damage numbers caused
reversed wins in calibration. Keep live positive and negative controls, not just
JSON fixtures. Reject malformed classifications without saving an outcome.

The shared runtime owns identity, retries, transactions, results and rendering.
If a game needs a new interaction type, extend and test that shared contract first;
keep transport and storage code out of the challenge definition.

## Stateful games use the same runtime

A stateful contribution has two files too: a `PersistedGame` subclass and a Python
journey test. The definition supplies `public_levels`, `initial_state`, `actions`,
`validate_action`, `public_state`, and `play`. See Honeypot for probe/guess actions
and Interrogation for witness selection and multiple accusations. Public action
descriptors specify labels, required text, and single/multiple target options;
the shared page renders them. Public presentation supports facts, notes and a table.
Keep hidden solutions and prompts out of both public methods.

`play(state, action)` returns a validated `TurnOutcome`, usually via `self.outcome`.
Each accepted action consumes exactly one attempt. A win must be explicit; a
positive score alone cannot complete a run. `ActionError` rejects invalid actions
without consuming a turn. Provider failures must propagate, so the transaction
rolls back instead of inventing a response or awarding a win. Close provider
clients in `finally`. Limit each turn to one provider request so the shared daily
admission ceiling remains a bound on paid calls.

Tests must play through the actual run API, resume between turns, prove a win and
an exhausted failure, reject invalid actions, and fault-inject provider errors.
No new route, template, JavaScript, registry entry, or database table is needed.

## Multi-agent games use saved stages

Copy `app/challenges/_STAGED_TEMPLATE.py` and add a Python API journey test as
your second file. `StagedGame` supplies start/continue actions, strategy entry,
and optional automatic continuation. Set a stage limit and keep each stage to
at most one provider call. The shared transport enforces that limit inside a
run turn. Use `respond()` for complete text and automatic client cleanup.

Store the next phase, transcript and private strategy in the outcome's state.
Validate structured judgments with strict schemas, and derive wins and bounded
scores on the server. Malformed judgments must raise, leaving the previous stage
intact. Never fabricate a fallback win. Automatic continuation starts only after
a saved response; reloads and errors pause. Players can uncheck the control to
pause after the current request. Each stage consumes a daily admission, including
failed attempts and retries; a replayed receipt never calls the model again.

The template discovery test plays both winning and losing two-stage runs through
the existing API, resumes between stages, and replays every request. Extend that
pattern with provider failures and domain-specific judgment boundaries. Fixtures
prove mechanics; real-model trials establish compatibility and sample difficulty.
