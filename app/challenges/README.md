# Contributing a challenge

Use the [two-file contribution guide](../../docs/ADDING_CHALLENGES.md).

- `PromptGame`: copy `_TEMPLATE.py` and add JSON acceptance fixtures.
- `PersistedGame`: supply state, actions and outcomes plus a Python API journey test.
- `StagedGame`: copy `_STAGED_TEMPLATE.py` and add a Python journey test. One model
  call per saved stage; the common page provides start/continue and optional autoplay.

Discovery, HTTP routes, persistence, retries, scores and the player page are shared.
Do not copy the old `reset`/`step` or streaming implementations into new games.
Python submissions are disabled until they can run in a properly isolated service.
