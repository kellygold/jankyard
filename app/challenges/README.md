# 🎮 Creating a Jankyard Challenge

Want to add a new challenge? **It's easy!** Thanks to auto-discovery, you just need to create one file.

## 🚀 Quick Start (5 Minutes)

### **1. Copy the Template**
```bash
cd app/challenges
cp _TEMPLATE.py my_challenge_name.py
```

### **2. Customize Your Challenge**
Edit `my_challenge_name.py`:
- Change class name: `TemplateChallenge` → `MyChallengeChallenge`
- Set properties: `name`, `display_name`, `description`
- Implement: `reset()` and `step()` methods

### **3. That's It!**
Your challenge is **automatically discovered and registered**. No need to edit any other files!

Test it:
```bash
python3 -c "from app.challenges import CHALLENGES; print(list(CHALLENGES.keys()))"
```

Your challenge should appear in the list! 🎉

---

## 📚 Challenge Types

### **Type 1: Prompt-Based Challenge** ⭐ (Easiest)

User submits a text prompt, you evaluate it.

**Example:** User tries to trick an AI into revealing secrets.

```python
class PromptInjectionChallenge(BaseChallenge):
    @property
    def challenge_type(self):
        return "prompt"
    
    def step(self, action: str):
        # action is the user's prompt
        response = self.llm_client.call(
            system_prompt="You are a secure chatbot",
            user_message=action
        )
        
        # Check if user succeeded in injection
        success = "secret" in response.lower()
        
        return StepResult(
            observation={"bot_response": response},
            reward=100 if success else 0,
            done=success,
            info={}
        )
```

---

### **Type 2: Code-Based Challenge** ⭐⭐ (Medium)

User submits Python code that plays your game.

**Example:** Navigate a maze, solve puzzles, play a game.

```python
class MazeChallenge(BaseChallenge):
    @property
    def challenge_type(self):
        return "code"
    
    @property
    def allowed_actions(self):
        return ["UP", "DOWN", "LEFT", "RIGHT"]
    
    def reset(self):
        self.player_pos = (0, 0)
        self.goal_pos = (5, 5)
        return {"position": self.player_pos, "goal": self.goal_pos}
    
    def step(self, action: str):
        # action is return value from user's agent.act()
        x, y = self.player_pos
        
        if action == "UP": y -= 1
        elif action == "DOWN": y += 1
        elif action == "LEFT": x -= 1
        elif action == "RIGHT": x += 1
        
        self.player_pos = (x, y)
        done = self.player_pos == self.goal_pos
        
        return StepResult(
            observation={"position": self.player_pos},
            reward=100 if done else -1,
            done=done,
            info={}
        )
```

---

### **Type 3: Multi-Turn with Memory** ⭐⭐⭐ (Advanced)

Challenge remembers conversation history.

**Example:** Interrogate AI witnesses, have debates.

```python
class InterrogationChallenge(BaseChallenge):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        self.conversation = []
    
    def step(self, action: str):
        self.conversation.append({"role": "user", "content": action})
        
        # Get response with full history
        response = self.llm_client.call_with_history(
            system_prompt="You are a witness. Be evasive.",
            messages=self.conversation
        )
        
        self.conversation.append({"role": "assistant", "content": response})
        
        # Check if user got the confession
        success = "i confess" in response.lower()
        
        return StepResult(
            observation={"response": response, "turn": len(self.conversation)},
            reward=100 if success else 0,
            done=success or len(self.conversation) > 20,
            info={}
        )
```

---

## 🎯 Required Properties

Every challenge must define these:

| Property | Type | Description | Example |
|----------|------|-------------|---------|
| `name` | str | Unique ID (lowercase) | `"my_challenge"` |
| `display_name` | str | UI name with emoji | `"🎮 My Challenge"` |
| `description` | str | Short description | `"Solve puzzles with AI"` |
| `max_steps` | int | Max turns allowed | `10`, `50`, `100` |
| `challenge_type` | str | Type of challenge | `"prompt"`, `"code"` |

---

## 🎯 Required Methods

### **`reset()` → Dict**
Initialize challenge state. Return starting observation.

```python
def reset(self) -> Dict[str, Any]:
    self.score = 0
    self.attempts = 0
    return {
        "message": "Challenge started!",
        "score": 0
    }
```

### **`step(action)` → StepResult**
Process one action. This is your core game logic!

```python
def step(self, action: str) -> StepResult:
    # 1. Process the action
    # 2. Update game state
    # 3. Calculate reward
    # 4. Check if done
    
    return StepResult(
        observation={"status": "..."},  # Info for next step
        reward=10,                       # Points earned
        done=False,                      # True when complete
        info={"extra": "metadata"}       # Additional data
    )
```

---

## 🎨 Adding Custom UI (Optional)

Create a template in `app/templates/`:

```html
<!-- app/templates/my_challenge_detail.html -->
{% extends "base.html" %}

{% block content %}
<div class="page-header">
    <h1>{{ challenge.display_name }}</h1>
    <p>{{ challenge.description }}</p>
</div>

<div class="submit-section">
    <form id="submitForm" action="/submit" method="POST">
        <input type="hidden" name="challenge_name" value="{{ challenge.name }}">
        <textarea name="agent_code" required></textarea>
        <button type="submit">Submit</button>
    </form>
</div>

<div id="results"></div>
{% endblock %}
```

Then in your challenge:
```python
@property
def template_name(self):
    return "my_challenge_detail.html"
```

---

## 🎨 Adding Custom JavaScript (Optional)

Create a handler in `app/static/js/handlers/`:

```javascript
// app/static/js/handlers/my_challenge.js
class MyChallengeHandler {
    constructor(resultsDiv) {
        this.resultsDiv = document.getElementById(resultsDiv);
    }
    
    async submit(userInput) {
        const formData = new FormData();
        formData.append('challenge_name', 'my_challenge');
        formData.append('agent_code', userInput);
        
        const response = await fetch('/submit', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        this.displayResults(result);
    }
    
    displayResults(result) {
        this.resultsDiv.innerHTML = `
            <div class="result">
                Score: ${result.score}
            </div>
        `;
    }
}
```

---

## 🎯 Difficulty Levels (Optional)

Support multiple difficulty levels:

```python
class MyChallenge(BaseChallenge):
    DIFFICULTY_LEVELS = {
        "level_1": {
            "name": "Easy Mode",
            "max_hints": 5,
            "time_limit": 60
        },
        "level_2": {
            "name": "Hard Mode",
            "max_hints": 2,
            "time_limit": 30
        }
    }
    
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        difficulty = config.get('difficulty', 'level_1') if config else 'level_1'
        self.config = self.DIFFICULTY_LEVELS[difficulty]
```

---

## 📊 Scoring Guidelines

### **Base Scoring:**
- Easy challenges: 100-300 points
- Medium challenges: 300-700 points
- Hard challenges: 700-1500 points

### **Bonuses:**
```python
# Efficiency bonus (fewer steps = more points)
efficiency_bonus = max(0, (max_steps - actual_steps) * 10)

# Speed bonus (faster completion)
time_bonus = max(0, (time_limit - elapsed_time) * 5)

# Creativity bonus (novel solutions)
creativity_bonus = 50 if is_novel_approach else 0

total_score = base_score + efficiency_bonus + time_bonus + creativity_bonus
```

### **Multipliers:**
```python
# Difficulty multiplier
multipliers = {
    'level_1': 1.0,
    'level_2': 1.5,
    'level_3': 2.0
}

final_score = total_score * multipliers[difficulty]
```

---

## 🧪 Testing Your Challenge

### **1. Unit Test**
```python
# tests/test_my_challenge.py
def test_my_challenge():
    challenge = MyChallengeChallenge()
    obs = challenge.reset()
    
    result = challenge.step("some action")
    assert result.reward >= 0
    assert "observation" in result.observation
```

### **2. Manual Test**
```bash
# Test discovery
python3 -c "from app.challenges import CHALLENGES; print('my_challenge' in CHALLENGES)"

# Run challenge
curl -X POST http://localhost:8000/api/submit \
  -F "challenge_name=my_challenge" \
  -F "agent_code=test prompt"
```

---

## ✅ Checklist Before Submitting

- [ ] Challenge class inherits from `BaseChallenge`
- [ ] All required properties defined
- [ ] `reset()` method implemented
- [ ] `step()` method implemented
- [ ] Challenge name is unique
- [ ] Scoring is fair and balanced
- [ ] Works with both anonymous and authenticated users
- [ ] Tested manually
- [ ] (Optional) Custom template created
- [ ] (Optional) Custom JavaScript handler created

---

## 🎉 Examples to Learn From

Check out these existing challenges:

| Challenge | Complexity | Learn About |
|-----------|-----------|-------------|
| `jank_maze.py` | ⭐ Easy | Code-based, pathfinding |
| `debate_battle.py` | ⭐⭐ Medium | Prompt-based, LLM judging |
| `glitch.py` | ⭐⭐ Medium | Prompt-based, progressive levels |
| `arena.py` | ⭐⭐⭐ Advanced | AI vs AI, complex state |
| `interrogation.py` | ⭐⭐⭐ Advanced | Multi-turn, conversation history |

---

## 💡 Tips & Tricks

### **Use the LLM Client**
```python
# Simple call
response = self.llm_client.call(
    system_prompt="You are...",
    user_message=action
)

# With conversation history
response = self.llm_client.call_with_history(
    system_prompt="You are...",
    messages=self.conversation_history
)
```

### **Progressive Difficulty**
```python
# Unlock levels based on score
if result.score >= 100:
    self.unlock_level_2()
```

### **Stream Events (Real-time Updates)**
```python
# Emit events for UI updates
yield {"type": "progress", "message": "Processing..."}
yield {"type": "result", "score": 100}
```

### **Error Handling**
```python
try:
    response = self.llm_client.call(...)
except Exception as e:
    return StepResult(
        observation={"error": str(e)},
        reward=0,
        done=True,
        info={"error": True}
    )
```

---

## 🚀 Ready to Build?

1. Copy `_TEMPLATE.py`
2. Implement your challenge
3. Test it locally
4. Submit a PR!

**Questions?** Check existing challenges or open an issue.

**Happy building! 🎮**
