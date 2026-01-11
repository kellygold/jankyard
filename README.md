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
- 📞 Corrupt messages through chains of AI agents

Compete on leaderboards. Learn real AI security concepts. Have fun breaking things.

---

## 🎮 Challenges

| Challenge | Difficulty | Description |
|-----------|------------|-------------|
| **Firewall** | ⭐⭐⭐ | Bypass keyword filters to extract the secret flag |
| **Giga Chad** | ⭐⭐⭐ | Break the "unbreakable" AI's defenses |
| **Glitch** | ⭐⭐ | Manipulate a chain of AI agents |
| **Heist** | ⭐⭐ | Coordinate a crew to pull off a heist |
| **Interrogation** | ⭐⭐ | Question witnesses to solve a mystery |
| **Arena** | ⭐⭐ | Battle AI gladiators with strategy prompts |
| **Debate** | ⭐⭐ | Out-argue an AI lawyer |
| **Telephone** | ⭐ | Corrupt a message through AI agents |
| **Jank Maze** | ⭐ | Write Python code to navigate a maze |

Each challenge has multiple difficulty levels. Beat one to unlock the next.

---

## 🚀 Quick Start

```bash
# Clone
git clone https://github.com/kellygold/jankyard.git
cd jankyard

# Install
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your DATABASE_URL and OPENAI_API_KEY

# Run
uvicorn app.main:app --reload --port 8000

# Visit http://localhost:8000
```

---

## 🛠️ Create Your Own Challenge

Adding a challenge is just **2 files**:

```bash
# 1. Copy the template
cp app/challenges/_TEMPLATE.py app/challenges/my_challenge.py

# 2. Implement your logic (see template for examples)

# 3. Optionally add custom UI
cp app/templates/challenges/firewall.html app/templates/challenges/my_challenge.html

# 4. Restart - it's auto-discovered!
```

**📖 Full Guide:** [docs/ADDING_CHALLENGES.md](docs/ADDING_CHALLENGES.md)

---

## 🏗️ Architecture

```
jankyard/
  app/
    main.py                     # FastAPI app entrypoint
    routes/                     # HTTP endpoints
    templates/
      challenges/               # Challenge templates (organized)
        base_challenge.html     # Base template (shared layout)
        _submission_form.html   # Reusable form component
        _level_tabs.html        # Reusable level selector
        _macros.html            # UI component macros
        glitch.html             # Individual challenge templates
        debate.html
        arena.html
        ...
      base.html                 # Site-wide base template
    static/
      js/
        core/                   # Shared JavaScript
          challenge-handler.js  # Base handler class
          utils.js              # Shared utilities
        handlers/               # Challenge-specific handlers
          glitch.js             # Refactored handlers
          ...
      css/                      # Stylesheets
    challenges/                 # ⭐ AUTO-DISCOVERED CHALLENGES
      base.py                   # BaseChallenge class
      registry.py               # Auto-discovery system
      _TEMPLATE.py              # Challenge template
      README.md                 # Contribution guide
      glitch.py                 # Just drop in a file!
      debate_battle.py          # Auto-registered!
      arena.py
      ...
    sandbox/                    # Python sandbox runner
    models/                     # Database models
    services/                   # Business logic
    repositories/               # Data access
  requirements.txt
  app.yaml                      # Google Cloud Run config
```

**Tech Stack:**
- **Backend:** FastAPI + Python
- **Frontend:** Jinja2 + Vanilla JS
- **Database:** Neon PostgreSQL  
- **LLM:** OpenAI API
- **Hosting:** Google Cloud Run

---

## 🧩 Tech Details

<details>
<summary>Challenge Auto-Discovery</summary>

Challenges are automatically discovered - just drop a file in `app/challenges/`:

```python
# app/challenges/my_challenge.py
class MyChallenge(BaseChallenge):
    @property
    def name(self) -> str:
        return "my_challenge"
    
    def step(self, action: str) -> StepResult:
        # Your logic here
        pass
```

No registration needed. Restart and it's live.
</details>

<details>
<summary>Code Sandbox (for Jank Maze)</summary>

User-submitted Python runs in a restricted environment:

**Forbidden:** `os`, `sys`, `open`, `exec`, `eval`, network access  
**Allowed:** `json`, `math`, `random`, `dataclasses`, `typing`
</details>

<details>
<summary>API Endpoints</summary>

```
GET  /                      # Homepage
GET  /challenges            # Challenge list
GET  /challenges/<name>     # Play challenge
POST /api/challenges/stream # SSE streaming endpoint
GET  /leaderboard/<name>    # Leaderboard
```
</details>

---

## 🚀 Deployment

```bash
# Google Cloud Run
gcloud run deploy jankyard --source . --region us-central1 --project YOUR_PROJECT
```

Requires `OPENAI_API_KEY` and `DATABASE_URL` as environment variables.

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

