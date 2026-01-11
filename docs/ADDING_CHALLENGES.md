# 🎮 Adding a New Challenge to Jankyard

Complete guide for creating a new challenge from scratch.

## Quick Start: Only 2 Files Needed!

Thanks to auto-discovery, adding a challenge is simple:

```
1. Backend Challenge Class (app/challenges/your_challenge.py)
   → Your game logic, scoring, and rules
   
2. HTML Template (app/templates/challenges/your_challenge.html)
   → Your UI (optional - can use generic template)
```

**That's it!** No manual registration, no route editing, no streaming config.

---

## Step 1: Copy the Template

```bash
cd app/challenges
cp _TEMPLATE.py my_challenge.py
```

---

## Step 2: Create Backend Challenge Class

**File**: `app/challenges/your_challenge.py`

**What it does**: Defines the game rules, scoring logic, and state management for your challenge.

**When it runs**: Every time a user plays your challenge, the backend creates an instance and calls:
1. `__init__()` - Set up the challenge
2. `reset()` - Initialize the game state
3. `step(action)` - Process each player action (called repeatedly)
4. `get_result()` - Return final score when game ends

```python
from typing import Dict, Any, Optional
from app.sandbox.base_challenge import BaseChallenge, ChallengeResult

class YourChallenge(BaseChallenge):
    """
    Brief description of what this challenge does.
    """
    
    def __init__(self, difficulty: str = "normal"):
        """
        CALLED: Once when challenge is created
        PURPOSE: Set up configuration and initial values
        """
        super().__init__()
        self.difficulty = difficulty
        self.challenge_type = "your_challenge"  # IMPORTANT: Must match your challenge name!
        self.max_steps = 10  # Maximum number of actions allowed
        
        # Challenge-specific config (customize these!)
        self.target_score = 100
        
    def reset(self) -> Dict[str, Any]:
        """
        CALLED: Once at the start of the game
        PURPOSE: Reset all state variables and return initial game state
        RETURNS: Dict with starting info shown to player
        """
        self.current_step = 0
        self.score = 0
        
        # Return what the player sees at start
        return {
            "observation": "Starting state description",
            "difficulty": self.difficulty,
            "instructions": "What the player should do",
            "allowed_actions": ["action1", "action2"]
        }
    
    def step(self, action: str) -> tuple[Dict[str, Any], bool]:
        """
        CALLED: Every time the player submits an action
        PURPOSE: Process the action, update game state, check if game is over
        
        Args:
            action: The user's action/input (string from text box)
            
        Returns:
            observation: Dict with updated state info to show player
            done: True if game is over, False to continue
        """
        self.current_step += 1
        
        # Your game logic here
        result = self._process_action(action)
        self.score += result['points']
        
        # Check if done
        done = (
            self.current_step >= self.max_steps or 
            self.score >= self.target_score
        )
        
        observation = {
            "message": result['message'],
            "score": self.score,
            "step": self.current_step,
            "done": done
        }
        
        return observation, done
    
    def _process_action(self, action: str) -> Dict[str, Any]:
        """
        CALLED: By step() to evaluate the player's action
        PURPOSE: Your custom game logic - this is where the fun happens!
        
        Example: Check if answer is correct, calculate damage, etc.
        """
        # Example: check action validity, update state
        if "correct" in action.lower():
            return {"points": 10, "message": "Good job!"}
        else:
            return {"points": 0, "message": "Try again"}
    
    def get_result(self) -> ChallengeResult:
        """
        CALLED: Once at the end of the game
        PURPOSE: Calculate final score and success/failure
        RETURNS: ChallengeResult object (saved to database)
        """
        success = self.score >= self.target_score
        
        return ChallengeResult(
            success=success,
            score=self.score,
            steps=self.current_step,
            message=f"Final score: {self.score}"
        )
    
    @property
    def allowed_actions(self) -> list[str]:
        """
        CALLED: When frontend needs to know valid actions
        PURPOSE: Define what actions the player can take
        NOTE: Optional - only needed if you want to restrict actions
        """
        return ["submit_answer", "get_hint"]
```

**Auto-Discovery**: Your challenge is automatically registered! No need to edit any other files.

Test it:
```bash
python3 -c "from app.challenges import CHALLENGES; print('my_challenge' in CHALLENGES)"
```

---

## Step 3: Create HTML Template (Optional)

**File**: `app/templates/challenges/your_challenge.html`

**What it does**: The UI players see - game board, input fields, score display, etc.

**Structure**:
- `{% block challenge_info %}` - Description and rules
- `{% block submit_section %}` - Game UI (this is where the action happens!)
- `{% block challenge_css %}` - Your custom styling
- `{% block challenge_js %}` - Initialize handler and button click events

```html
{% extends "challenges/_base_challenge.html" %}

{% block challenge_info %}
<div class="giga-header">
    <h1>🎮 Your Challenge Name</h1>
    <p>Brief description of what players need to do</p>
</div>

<div class="challenge-info">
    <div class="info-box">
        <h3>📋 Rules</h3>
        <ul>
            <li>Rule 1</li>
            <li>Rule 2</li>
            <li>Rule 3</li>
        </ul>
    </div>
    
    <div class="info-box">
        <h3>🎯 Objective</h3>
        <p>Score {{ target_score }} points to win!</p>
    </div>
</div>
{% endblock %}

{% block submit_section %}
<!-- Username Field (for leaderboard) -->
<div class="username-section">
    <label for="username">
        👤 Username {% if current_user %}(logged in){% else %}(optional){% endif %}
    </label>
    <input 
        type="text" 
        id="username" 
        name="username"
        value="{% if current_user %}{{ current_user.username }}{% endif %}"
        {% if current_user %}readonly{% endif %}
        placeholder="{% if not current_user %}Enter your username{% endif %}"
    />
</div>

<!-- Game UI -->
<div class="game-container">
    <div class="stats-bar">
        <span>Score: <strong id="score">0</strong></span>
        <span>Step: <strong id="step">0</strong>/10</span>
    </div>
    
    <div class="messages" id="gameMessages">
        <div class="system-message">
            Ready to play! Submit your action below.
        </div>
    </div>
    
    <div class="input-container">
        <textarea 
            id="userAction" 
            placeholder="Enter your action..."
            rows="4"
        ></textarea>
        <button id="submitBtn" class="btn-primary">
            🚀 Submit Action
        </button>
    </div>
</div>

<!-- Completion Modal -->
<div id="completionModal" class="modal" style="display: none;">
    <div class="modal-content">
        <h2 id="modalTitle">Challenge Complete!</h2>
        <p id="modalMessage"></p>
        <div class="modal-stats">
            <div>Score: <span id="finalScore"></span></div>
            <div>Steps: <span id="finalSteps"></span></div>
        </div>
        <button onclick="closeModal()" class="btn-primary">Close</button>
    </div>
</div>
{% endblock %}

{% block challenge_css %}
<style>
/* Your custom styling */
.game-container {
    background: #1a1a2e;
    border: 2px solid #3b82f6;
    border-radius: 12px;
    padding: 1.5rem;
}

.stats-bar {
    display: flex;
    justify-content: space-between;
    padding: 1rem;
    background: rgba(59, 130, 246, 0.1);
    border-radius: 8px;
    margin-bottom: 1rem;
}

.messages {
    min-height: 300px;
    max-height: 500px;
    overflow-y: auto;
    padding: 1rem;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    margin-bottom: 1rem;
}

.system-message, .update-message {
    margin-bottom: 1rem;
    padding: 0.75rem;
    background: rgba(96, 165, 250, 0.1);
    border-left: 3px solid #60a5fa;
    border-radius: 4px;
}

/* Add more styles... */
</style>
{% endblock %}

{% block challenge_js %}
<script src="/static/js/core/challenge-handler.js"></script>
<script src="/static/js/handlers/your_challenge.js"></script>
<script>
(function() {
    // Initialize handler
    const handler = new YourChallengeHandler('gameMessages');
    
    // Submit button
    const submitBtn = document.getElementById('submitBtn');
    const userAction = document.getElementById('userAction');
    
    submitBtn.addEventListener('click', async () => {
        const action = userAction.value.trim();
        if (!action) {
            alert('Please enter an action!');
            return;
        }
        
        // Disable during processing
        submitBtn.disabled = true;
        userAction.disabled = true;
        
        try {
            // Stream the action
            await handler.stream(action, '{{ difficulty }}');
        } catch (error) {
            console.error('Error:', error);
            alert('Something went wrong!');
        } finally {
            submitBtn.disabled = false;
            userAction.disabled = false;
            userAction.value = '';
        }
    });
})();

// Modal functions
function showCompletionModal(result) {
    document.getElementById('modalTitle').textContent = 
        result.success ? '🎉 You Won!' : '😔 Challenge Failed';
    document.getElementById('modalMessage').textContent = result.message;
    document.getElementById('finalScore').textContent = result.score;
    document.getElementById('finalSteps').textContent = result.steps;
    document.getElementById('completionModal').style.display = 'flex';
}

function closeModal() {
    document.getElementById('completionModal').style.display = 'none';
}
</script>
{% endblock %}
```

---

## Step 4: Add Difficulty Levels (Optional)

For multi-level challenges, define levels in your class:

```python
class MyChallenge(BaseChallenge):
    DIFFICULTY_LEVELS = {
        "level_1": {"name": "Easy", "max_attempts": 10},
        "level_2": {"name": "Hard", "max_attempts": 5},
        "level_3": {"name": "Expert", "max_attempts": 3},
    }
    
    def __init__(self, config=None):
        super().__init__(config)
        difficulty = config.get('difficulty', 'level_1') if config else 'level_1'
        self.config = self.DIFFICULTY_LEVELS[difficulty]
```

---

## Testing Checklist

- [ ] Challenge class initializes correctly
- [ ] `reset()` returns valid initial state  
- [ ] `step()` processes actions properly
- [ ] `get_result()` returns correct final state
- [ ] Auto-discovery works: `python3 -c "from app.challenges import CHALLENGES; print('my_challenge' in CHALLENGES)"`
- [ ] Template loads at `/challenges/my_challenge`
- [ ] Scoring works correctly
- [ ] Completion modal shows

---

## Deployment

Once your challenge works locally:

1. **Commit changes**:
```bash
git add .
git commit -m "feat: Add YourChallenge"
git push origin main
```

2. **Deploy to Cloud Run**:
```bash
gcloud run deploy jankyard --source . --region us-central1
```

---

## Example Challenges to Study

- **Simple**: `app/challenges/firewall.py` - Basic keyword filtering
- **Medium**: `app/challenges/arena.py` - Turn-based combat
- **Complex**: `app/challenges/giga_chad.py` - Multi-round AI battles
- **Progressive**: `app/challenges/glitch.py` - Level unlocking

---

## Tips

1. **Start simple** - Get basic functionality working first
2. **Use existing patterns** - Copy from similar challenges
3. **Test incrementally** - Don't write everything at once
4. **Debug with console.log** - Check browser console for events
5. **Check SSE events** - Network tab shows streaming data
6. **Style last** - Get logic working before making it pretty

---

## Common Issues

**Events not showing?**
- Check handler is registered: `this.on('event_type', handler)`
- Verify event type matches backend: `{'type': 'update'}`

**UI not updating?**
- Check element IDs match: `getElementById('score')`
- Verify DOM elements exist before updating

**Score not saving?**
- Ensure username field exists with `id="username"`
- Check `ChallengeHandler` is submitting properly

---

## Need Help?

- Study existing challenges in `app/challenges/`
- Check handlers in `app/static/js/handlers/`
- Look at templates in `app/templates/challenges/`
- Open an issue on GitHub

Happy building! 🎮
