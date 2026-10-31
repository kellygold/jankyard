# 🧟‍♂️ Jankyard.ai

**Learn prompt injection by breaking AI systems.**

[![Live Site](https://img.shields.io/badge/Play%20Now-jankyard.ai-blue?style=for-the-badge)](https://jankyard.ai)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

Jankyard is an open-source playground for learning AI security through hands-on prompt injection challenges. Inspired by [HackThisSite](https://hackthissite.org), but for AI.

**Try to:**
- 🔓 Bypass content filters to extract secrets
- 🎭 Manipulate AI agents into breaking their rules  
- 🕵️ Interrogate witnesses to solve crimes
- ⚔️ Battle AI gladiators with clever prompts
- 📞 Preserve an instruction through agents that reinterpret it

Compete on leaderboards. Learn real AI security concepts. Have fun breaking things.

---

## 🎮 Challenges

| Challenge | Difficulty | Description |
|-----------|------------|-------------|
| **Firewall** | ⭐⭐⭐ | Bypass keyword filters to extract the secret flag |
| **Giga Chad** | ⭐⭐⭐ | Break the "unbreakable" AI's defenses |
| **Glitch** | ⭐⭐ | Break a fictional role, moderation rule and token-protection rule |
| **Heist** | ⭐⭐ | Coordinate a crew to pull off a heist |
| **Interrogation** | ⭐⭐ | Question witnesses to solve a mystery |
| **Arena** | ⭐⭐ | Battle AI gladiators with strategy prompts |
| **Debate** | ⭐⭐ | Out-argue an AI lawyer |
| **Telephone** | ⭐ | Preserve an instruction through a chain of AI agents |
| **Honeypot** | ⭐⭐ | Identify traps through probes and explicit guesses |

Each challenge has multiple levels. Beat one to unlock the next. Difficulty labels
are design intent; [live calibration](docs/recovery/calibration.md) records what has
actually been demonstrated. Python uploads are disabled pending real isolation.

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/kellygold/jankyard.git
cd jankyard

# Install
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-test.txt

# Set up environment
cp .env.example .env
# Edit .env with your DATABASE_URL and OPENAI_API_KEY

# Prepare a NEW development database (existing installations: omit --bootstrap)
python -m app.migrate --bootstrap

# Run
uvicorn app.main:app --reload --port 8000

# Visit http://localhost:8000
```

---

## 🛠️ Create Your Own Challenge

Add a prompt game with **two files**: its Python definition and acceptance fixtures.
The shared runtime supplies the page, saved turns, win receipt, scoreboard, and progression.

```bash
cp app/challenges/_TEMPLATE.py app/challenges/my_game.py
# Edit the definition and add tests/runtime/fixtures/my_game.json
pytest tests/challenges/test_prompt_contract.py tests/runtime
```

See [the contribution guide](docs/ADDING_CHALLENGES.md) and
[recovery status and migration instructions](docs/recovery/README.md).

---

## 🏗️ Architecture

All nine public games use one persisted API and page. Definitions supply the
objective, actions, private state and explicit outcome. The platform owns
identity, retries, locking, counters, scoring, progression and rendering.

```text
app/challenges/
  prompt_game.py             # Declarative single-response games
  runtime.py                 # PersistedGame and multi-agent StagedGame
  registry.py                # Discovers contributed definitions
  _TEMPLATE.py               # Prompt-game starting point
  _STAGED_TEMPLATE.py        # Multi-agent starting point
app/routes/runs.py           # Shared HTTP and admission limits
app/services/run_service.py # Atomic state, outcome and retry receipt
app/models/run.py           # Runs, turns and versioned scores
app/templates/challenges/prompt_game.html
app/static/js/core/prompt-game.js
```

Multi-agent games save one provider call per stage. The common page can continue
automatically or pause. New games need a definition and fixtures/journey test;
they need no game-specific HTTP handler, template, JavaScript or database table.

The stack is FastAPI/Python, Jinja2/vanilla JavaScript and PostgreSQL. SQLite is
for local development and browser fixtures. Models use the bounded shared
provider adapter. Legacy templates and helpers remain for history and compatibility;
new contributions should follow the current templates.

| Endpoint | Purpose |
|---|---|
| `GET /challenges/{name}` | Shared player page |
| `GET /api/games/{name}` | Public levels and actions |
| `GET /api/games/{name}/progress` | Owned progress and latest run |
| `GET /api/games/{name}/leaderboard` | Versioned best scores |
| `POST /api/runs` | Create an owned run |
| `GET /api/runs/{id}` | Resume owned state |
| `POST /api/runs/{id}/turns` | Apply one action or replay a saved receipt |

`POST /submit` is disabled (410). Public games also reject the old stateless
streaming route. The old in-process Python sandbox is not a security boundary
and is not available to web submissions.

---

## 🚀 Deployment

The recovery branch requires a staging rehearsal before production. See
[rollout and rollback](docs/recovery/rollout.md) for the exact sequence.

The image sets `ENVIRONMENT=production` and refuses to start without `SECRET_KEY`.
Supply a strong secret, `OPENAI_API_KEY`, a PostgreSQL `DATABASE_URL`, and explicit
model/budget settings through the hosting secret/config mechanism. Never bake
`.env` into an image. Run `python -m app.migrate` once against the intended existing
database **before** switching workers; startup does not migrate automatically.
`--bootstrap` is only for an empty development database.


---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md).

**Ideas:**
- New challenge types
- Better mobile UX
- Technique explanations after solving
- Community leaderboards

---

## 📚 Documentation

- [Creating Challenges](docs/ADDING_CHALLENGES.md) - Full guide
- [Challenge Template](app/challenges/_TEMPLATE.py) - Copy this to start

---

## 🪦 License

MIT — keep it weird, keep it open.


## Support

If this project is useful to you, you can [support Burner Tools](https://buymeacoffee.com/burnertools)
on Buy Me a Coffee.
