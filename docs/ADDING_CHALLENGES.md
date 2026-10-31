# Add a prompt game with two files

The recovered runtime currently powers Glitch. New prompt games should use this
contract. Multi-agent games still use the legacy runtime and are being migrated;
do not copy their HTTP handlers, templates, or client-side progression logic.

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
being tested. `system_prompt` must actually forbid the behavior the objective asks
players to elicit. Use harmless synthetic data and explicit game roles.

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

The shared runtime owns identity, retries, transactions, results and rendering.
If a game needs a new interaction type, extend and test that shared contract first;
keep transport and storage code out of the challenge definition.
