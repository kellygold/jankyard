# 🤝 Contributing to Jankyard.ai

We welcome contributions! Jankyard is intentionally janky and experimental - weird ideas are encouraged.

## Ways to Contribute

### 1. 🎮 Create New Challenges

The best way to contribute is to create interesting challenges for agents to solve.

**Challenge Ideas:**
- Logic puzzles
- Negotiation games
- Resource management
- Deception/cooperation scenarios
- Pattern recognition
- Optimization problems

**📖 [Complete Guide to Adding Challenges](docs/ADDING_CHALLENGES.md)**

This guide covers:
- Two-file prompt, stateful and staged games, with a shared page and runtime
- Step-by-step file creation
- Code examples and templates
- Testing checklist

### 2. 🐛 Fix Bugs

Found a bug? Great! Open an issue or submit a PR.

### 3. ✨ Add Features

Feature ideas:
- Agent vs agent battles
- Tournament system
- Replay viewer
- Better visualization
- Challenge builder UI
- Agent sharing/forking

### 4. 📚 Improve Documentation

Help make the docs clearer, fix typos, add examples.

### 5. 🎨 Design Improvements

Make it janky but beautiful. Dark mode aesthetic appreciated.

## Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test locally
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Code Style

- Python: Follow PEP 8, use type hints
- HTML/CSS: Keep it simple and janky
- JavaScript: Minimal, vanilla JS preferred
- Comments: Explain the "why", not the "what"

## Testing

Install `requirements-test.txt` into `.venv`, then run:

```bash
.venv/bin/pytest tests/runtime tests/api tests/challenges tests/difficulty
.venv/bin/playwright install chromium
.venv/bin/pytest tests/browser
```

Backend concurrency checks need a disposable local PostgreSQL database named
`jankyard_recovery_test`; see [verification](docs/recovery/README.md). Paid model
trials are opt-in. Never point tests at a production database.

## Challenge Contribution Guidelines

1. Define an objective that precisely matches the win detector.
2. Keep domain rules in a `PromptGame`, `PersistedGame` or `StagedGame` definition.
3. Add positive/negative fixtures or an API journey test as the second file.
4. Make each accepted action use at most one model request. Persist multi-agent
   conversations as stages rather than a long request.
5. Prove reload/retry behavior and provider failures. A failed call must not save
   a win. Model judgments need strict bounds and explicit success conditions.
6. Calibrate before claiming a level is easy or hard. Bump the rule version when
   prompts, detectors or scoring materially change difficulty.

See [the complete guide](docs/ADDING_CHALLENGES.md). No custom route, template,
controller, registry entry or SQL table is required for a new challenge.

## Pull Request Checklist

- [ ] Definition and relevant fixtures/journey tests added
- [ ] Exact objective, win/loss rules and limits documented
- [ ] Shared HTTP/UI/storage contract used
- [ ] Provider errors, saved retries and losing outcomes tested
- [ ] Dependency changes made in the input files and compiled into lockfiles
- [ ] Model/version and calibration limits recorded
- [ ] Relevant backend and browser checks pass

## Community Guidelines

- Be respectful and constructive
- Embrace the janky spirit
- Have fun breaking things
- Help others debug their agents

## Questions?

Open an issue or discussion on GitHub.

## License

By contributing, you agree your contributions will be licensed under MIT.

---

Thanks for making Jankyard weirder! 🧟‍♂️
