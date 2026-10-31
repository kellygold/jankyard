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

## Teaching progression and ultra-hard mode

Use three passable teaching levels before an optional hardened open challenge.
Each teaching level needs a clear trust boundary and reproducible live winning
examples with controls. Label ultra-hard as experimental with no promised
solution; it should follow the teaching levels, not block them. Preserve hardened
defenses when redesigning the main lessons, and bump the rules version.

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

## Give a challenge its own atmosphere

The two files are still the challenge definition and its acceptance fixtures/test.
Presentation belongs in the definition too. A shared page does **not** require
identical game screens. Set optional `UI` metadata on your class:

```python
UI = {
    'skin': 'courtroom',       # Reuse any theme, regardless of the game's name.
    'layout': 'wide',          # wide, split, or dossier (intelligence on the left)
    'console_title': 'The hearing',
    'state_title': 'The participants',
    'player_role': 'Counsel',
    'assistant_role': 'Court record',
    'success_title': 'Case won',
    'failure_title': 'Case not proven',
    'action_labels': {'start': 'Call court to order'},
    'input_labels': {'start': 'Your argument'},
    'placeholders': {'start': 'Explain your case and anticipate the rebuttal.'},
    'levels': {'level_1': {'title': 'The first hearing', 'subtitle': 'Opening arguments'}},
}
```

Available themes: `glitch` (cyan terminal), `firewall` (green security terminal),
`giga` (blue arcade console), `arena` (red combat), `courtroom` (wood and gold),
`heist` (navy planning room), `honeypot` (amber surveillance), `interrogation`
(case desk), and `telephone` (purple relay). These names identify reusable skins,
not a routing registry. Set `composer_position: 'top'` for a relay-style screen.
Set `density: 'compact'` for short repeated-prompt consoles like Glitch and
Honeypot; it keeps the objective, target and controls close together.
Omit `UI` entirely for the default accessible console.

`public_state(state)` returns only safe display data. Use the existing components:

| Field | Shape and behavior |
| --- | --- |
| `scene` | `{icon, eyebrow, title, body}` — scenario or case-file header |
| `facts` | `[{label, value}]` — current counters and facts |
| `roster` | `[{name, icon, detail, status}]` — crew, characters, agents, or defenses |
| `roster` target | Add `target` and `action` to select an available single-target action; it uses the shared controller and locks during pending requests |
| `timeline` | `[{label, active}]` — highlights the current saved stage |
| `meters` | `[{label, value, max, loss?}]` — accessible progress/HP bars; `loss` is the last saved HP loss |
| `evidence` | `{title, value, max, items, empty}` — progress plus discovered evidence; never include undiscovered leads |
| `notice` | `{title, body, tone}` — saved filter feedback or a reveal (`warning` or `info`) |
| `notes`, `table` | Paragraph strings; `{columns, rows}` for a scrollable log |
| `input_limit` | Optional code-point budget, checked in the browser **and** `validate_action` |
| `speakers` | `[{label, kind, icon?}]` in assistant-response order; `kind` is `player`, `opponent`, `judge`, or `response` |
| `judgments` | `[{title, metrics: [{label, value, max?, suffix?}]}]` in judge-response order; values must come from validated saved rulings |

For recurring speaker sequences, set `UI.repeat_speakers = True`. Optional
`round_size` and `round_count` group assistant responses into rounds. Automatic
stage-advance controls are omitted from the dialogue, while the original player
strategy remains visible. Speaker identity comes from the game's projection,
never from model-generated markup. All content renders as text.

Actions may include `confirmation: {title, body, confirm, cancel}`. The shared
accessible dialog confirms the captured action before creating a request;
retrying an interrupted request uses the original receipt without asking twice.
Success, failure, score, rank and unlocking always come from committed runs.
Never infer a win from a theme, animation, positive message, or score alone.

Test both the public projection and the normal browser journey. Verify every
level's character cards and limits, terminal outcomes, reload, interrupted-request
locking, keyboard controls and mobile overflow. When adding display-only saved
fields, tolerate old runs without those fields: show their existing transcript
rather than fabricate missing measurements. See `tests/runtime/test_game_presentation.py`
and `tests/browser/test_game_design.py` for examples.

Add a genuinely new visual component to the shared renderer only when none of
these components fits the interaction. Keep domain choices in the challenge file;
do not introduce challenge-name conditionals into the controller or renderer.

### Keep the instructions with the input

`UI['briefing']` accepts `title` (concrete goal), `context` (target and scenario),
`task` (what the player should type) and `example` (an approach, not a promised
solution). Override only changing fields with `UI['levels'][level_id]['briefing']`.
The win condition comes from the level's public `objective`; keep it truthful to
`play()`. State optional ultra-hard/no-promised-solution status in visible context.

The shared form renders these together, above the input. `input_labels`,
`placeholders` and `action_help` use action IDs, so guidance can change from a
strategy to continuation, or from a probe to a guess. `reference_title` optionally
places the existing intelligence panel in an expandable reference inside the
briefing (for example, crew, security and complication). All copy renders as text.
Metadata is optional: contributors without it get the existing level objective,
scenario and generic input guidance. No extra template, route or contribution
file is required. Test both the goal's meaning and its proximity to the input;
a scripted win alone does not establish that a new player knows what to do.
