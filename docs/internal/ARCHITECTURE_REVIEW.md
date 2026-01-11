# 🏗️ Jankyard Architecture Review & Refactoring Plan

## Executive Summary

**Date:** November 28, 2024  
**Status:** Growing codebase entering technical debt accumulation phase  
**Priority:** Address now before adding more features  
**Impact:** High - Will significantly improve maintainability and enable community contributions

---

## 📊 Current State Analysis

### Folder Structure
```
jankyard/
├── app/
│   ├── challenges/        # ✅ Good: Modular challenge system
│   │   ├── filters/       # ✅ Good: Separated concerns
│   │   ├── base.py        # ✅ Excellent: Base class + registry pattern
│   │   └── *.py          # 7 challenges
│   ├── core/             # ✅ Good: Core utilities
│   ├── llm/              # ✅ Good: Unified LLM client
│   ├── models/           # ✅ Good: Database models
│   ├── repositories/     # ✅ Good: Data access layer
│   ├── routes/           # ✅ Good: API endpoints
│   ├── sandbox/          # ✅ Good: Isolated execution
│   ├── schemas/          # ✅ Good: Pydantic validation
│   ├── services/         # ✅ Good: Business logic
│   ├── static/           # ⚠️  ISSUE: JS handlers have duplication
│   │   ├── css/
│   │   └── js/           # 11 files, some duplication
│   ├── templates/        # ⚠️  ISSUE: 18 HTML files, high duplication
│   └── utils/            # ✅ Good: Helper functions
├── assets/               # ⚠️  Unused?
├── docs/                 # ⚠️  Empty?
├── examples/             # ✅ Good
├── scripts/              # ✅ Good
└── src/                  # ❌ BAD: Contains app2run (not ours)
```

---

## 🔴 Critical Issues

### 1. **Manual Challenge Registration**
**Current Problem:**
```python
# app/challenges/__init__.py - MUST manually import every challenge
from app.challenges.jank_maze import JankMazeChallenge
from app.challenges.debate_battle import DebateBattleChallenge
from app.challenges.giga_chad import GigaChadMainChallenge
# ... 7 imports
```

**Impact:**
- New challenges require editing `__init__.py`
- Easy to forget registration
- Not discoverable
- Blocks community submissions

**Solution: Auto-Discovery Pattern**
```python
# Scan challenges/ directory and auto-register
import os
import importlib
import inspect

def auto_discover_challenges():
    challenges_dir = os.path.dirname(__file__)
    for filename in os.listdir(challenges_dir):
        if filename.endswith('.py') and not filename.startswith('_'):
            module_name = filename[:-3]
            module = importlib.import_module(f'app.challenges.{module_name}')
            
            # Find Challenge classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseChallenge) and obj != BaseChallenge:
                    # Auto-registers via decorator
                    pass
```

---

### 2. **JavaScript Handler Duplication**

**Current State:**
- `arena-handler.js` (11KB)
- `glitch-handler.js` (16KB)
- `interrogation-handler.js` (26KB!)
- `debate-handler.js` (3KB)
- `firewall-handler.js` (6KB)
- `attack-handler.js` (6KB)

**Duplication Found:**
```javascript
// EVERY handler has this pattern:
async streamAttack/streamQuestion/streamMove() {
    const formData = new FormData();
    formData.append('challenge_name', 'glitch');
    formData.append('agent_code', userMessage);
    formData.append('difficulty', `level_${this.currentLevel}`);
    
    const response = await fetch('/submit/stream', {
        method: 'POST',
        body: formData
    });
    // ... parse SSE events
}
```

**Solution: Generic Challenge Handler**
```javascript
// challenge-handler-base.js
class ChallengeHandler {
    constructor(challengeName, resultsContainer) {
        this.challengeName = challengeName;
        this.resultsDiv = document.getElementById(resultsContainer);
        this.eventHandlers = {}; // Map event types to handlers
    }
    
    // Generic stream method
    async stream(actionData, difficulty = null) {
        const formData = this.buildFormData(actionData, difficulty);
        const fingerprintHeaders = await getFingerprintHeaders();
        
        const response = await fetch('/submit/stream', {
            method: 'POST',
            body: formData,
            headers: fingerprintHeaders
        });
        
        await this.processSSE(response);
    }
    
    // Subclasses register event handlers
    on(eventType, handler) {
        this.eventHandlers[eventType] = handler;
    }
    
    // Process SSE stream
    async processSSE(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        // ... standard SSE parsing
        // Calls this.eventHandlers[eventType](data)
    }
}

// glitch-handler.js becomes:
class GlitchHandler extends ChallengeHandler {
    constructor(resultsContainer, level) {
        super('glitch', resultsContainer);
        this.level = level;
        
        // Register specific event handlers
        this.on('bot_response', (data) => this.renderBotResponse(data));
        this.on('success', (data) => this.handleSuccess(data));
    }
}
```

**Savings:** ~50KB code → ~15KB code (70% reduction!)

---

### 3. **Template Duplication**

**18 HTML templates with repeated patterns:**

**Common Patterns Found:**
```html
<!-- Every detail page has: -->
<div class="challenge-header">
    <h1>{emoji} {title}</h1>
    <p class="description">{description}</p>
    <div class="difficulty-selector">...</div>
</div>

<div class="challenge-content">
    <div class="challenge-instructions">...</div>
    <div class="agent-submission-form">...</div>
</div>

<div id="results"></div>
```

**Solution: Template Inheritance + Macros**
```jinja2
<!-- templates/challenges/base_challenge.html -->
{% extends "base.html" %}

{% block content %}
<div class="challenge-layout">
    <div class="challenge-header">
        {% block challenge_header %}{% endblock %}
    </div>
    
    <div class="challenge-content">
        {% block challenge_instructions %}{% endblock %}
        
        <!-- Generic submission form -->
        {% include "challenges/_submission_form.html" %}
    </div>
    
    <div id="results" class="results-container">
        {% block results_container %}{% endblock %}
    </div>
</div>

<!-- Load challenge-specific JS -->
<script src="/static/js/fingerprint-helper.js"></script>
<script src="/static/js/challenge-handler-base.js"></script>
{% block challenge_js %}{% endblock %}
{% endblock %}

<!-- templates/challenges/glitch_detail.html -->
{% extends "challenges/base_challenge.html" %}

{% block challenge_header %}
<h1>🔓 The Glitch</h1>
<p>Break the bots through prompt injection</p>
{% endblock %}

{% block challenge_js %}
<script src="/static/js/glitch-handler.js"></script>
{% endblock %}
```

**Savings:** 18 files (~15KB avg) → 1 base + 7 small files (~3KB each) = 240KB → 80KB (66% reduction!)

---

### 4. **LLM Client Instantiation**

**Current: Every challenge creates its own LLMClient**
```python
# Repeated in 4+ challenge files:
def __init__(self, config=None):
    super().__init__(config)
    self.llm_client = LLMClient()  # ← Duplication
    self.judge_client = LLMClient()  # ← More duplication
```

**Issues:**
- Repeated initialization
- No connection pooling
- Harder to mock for testing
- Can't easily swap providers globally

**Solution: Dependency Injection**
```python
# app/challenges/base.py
class BaseChallenge(ABC):
    def __init__(self, config=None, llm_client=None, judge_client=None):
        self.config = config or {}
        self.llm_client = llm_client or self._get_default_llm_client()
        self.judge_client = judge_client or self._get_default_judge_client()
        # ...
    
    @staticmethod
    def _get_default_llm_client():
        """Override for testing or custom config"""
        return LLMClient()
    
    @staticmethod
    def _get_default_judge_client():
        """Override for testing or custom config"""
        return LLMClient()

# Now challenges don't need to instantiate:
class GlitchChallenge(BaseChallenge):
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        # self.llm_client is already available!
```

---

### 5. **Config Management**

**Current: Scattered config access**
```python
# Some files:
from app.core.config import config
if config.RATE_LIMIT_ENABLED:

# Other files:
import os
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

# More files:
MAX_STEPS = 100  # Hardcoded!
```

**Solution: Centralized + Typed Config**
```python
# app/core/config.py - Enhanced
from dataclasses import dataclass
from typing import Optional

@dataclass
class ChallengeConfig:
    """Configuration for challenge execution"""
    max_steps: int = 100
    timeout_seconds: int = 300
    max_memory_mb: int = 1
    
@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    enabled: bool = True
    anon_per_minute: int = 5
    anon_per_day: int = 50
    auth_per_minute: int = 10
    auth_per_day: int = 100
    
@dataclass
class Config:
    """Application configuration (immutable after init)"""
    environment: str
    database_url: str
    secret_key: str
    
    challenges: ChallengeConfig
    rate_limits: RateLimitConfig
    # ...
    
    @classmethod
    def from_env(cls):
        """Load from environment variables"""
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            challenges=ChallengeConfig(
                max_steps=int(os.getenv("MAX_STEPS", "100"))
            ),
            # ...
        )

# Single global instance
config = Config.from_env()
```

---

## 🟡 Medium Priority Issues

### 6. **Service Layer Inconsistency**

**Some services are singletons, others aren't:**
```python
# app/services/challenge_service.py
class ChallengeService:
    def __init__(self, db: Session):  # Needs DB
        self.db = db

# app/services/rate_limit_service.py
class RateLimitService:
    def __init__(self, db: Session):  # Needs DB
        self.db = db
```

**But then:**
```python
# In routes - create new instance every time
rate_limit_service = RateLimitService(db)
challenge_service = ChallengeService(db)
```

**Better Pattern:**
```python
# Use FastAPI dependency injection
from fastapi import Depends

def get_challenge_service(db: Session = Depends(get_db)) -> ChallengeService:
    return ChallengeService(db)

@router.post("/submit")
async def submit_agent(
    challenge_service: ChallengeService = Depends(get_challenge_service)
):
    # No manual instantiation!
```

---

### 7. **Repository Pattern Incomplete**

**Good: You have repositories**
```python
leaderboard_repo.py
rate_limit_repo.py
submission_repo.py
user_repo.py
```

**Issue: Direct DB access still happening**
```python
# In routes/leaderboard.py
entries = db.query(LeaderboardEntry).filter(...).all()  # ❌ Direct query
```

**Should be:**
```python
# In routes/leaderboard.py
entries = leaderboard_repo.get_by_challenge(...)  # ✅ Through repository
```

---

### 8. **Error Handling Inconsistency**

**Mix of patterns:**
```python
# Pattern 1: Return JSONResponse
return JSONResponse(content={"error": "..."}, status_code=400)

# Pattern 2: Raise HTTPException
raise HTTPException(status_code=400, detail="...")

# Pattern 3: Return dict
return {"error": "..."}
```

**Standardize:**
```python
# app/core/exceptions.py - Custom exceptions
class JankyardException(Exception):
    """Base exception"""
    status_code = 500
    
class ValidationError(JankyardException):
    status_code = 400
    
class RateLimitError(JankyardException):
    status_code = 429

# app/main.py - Global exception handler
@app.exception_handler(JankyardException)
async def jankyard_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )
```

---

## 🟢 What's Working Well

### ✅ **Challenge Base Class Pattern**
```python
class BaseChallenge(ABC):
    @abstractmethod
    def step(self, action: str) -> StepResult:
    @abstractmethod
    def reset(self) -> Dict[str, Any]:
```
**This is excellent!** Consistent interface for all challenges.

### ✅ **Registry Pattern**
```python
@ChallengeRegistry.register
class MyChallenge(BaseChallenge):
```
**Clean auto-registration** - just needs auto-discovery.

### ✅ **Repository Layer**
**Good separation** between data access and business logic.

### ✅ **Service Layer**
**Clean business logic** separation from routes.

### ✅ **Unified LLM Client**
**Single interface** for OpenAI/Anthropic is great.

### ✅ **Base Chat Handler (JS)**
**Just added!** Shows you're already thinking about reusability.

---

## 🎯 Recommended Refactoring Priority

### **Phase 1: Foundation (High Impact, Low Risk)** - 4-6 hours

1. **Auto-discovery for challenges** (2h)
   - Enables community contributions
   - Remove manual registration
   
2. **Generic JS Challenge Handler** (2h)
   - Reduce JS code by 70%
   - Make new challenges easier
   
3. **Template inheritance** (2h)
   - Reduce HTML duplication
   - Faster development

### **Phase 2: Architecture (Medium Impact, Medium Risk)** - 6-8 hours

4. **Dependency injection for services** (2h)
   - Cleaner code
   - Easier testing
   
5. **Complete repository pattern** (2h)
   - Remove direct DB queries
   - Better abstraction
   
6. **Standardize error handling** (2h)
   - Consistent API responses
   - Better debugging

### **Phase 3: Polish (Low Impact, Low Risk)** - 2-4 hours

7. **Config refactor** (1h)
   - Typed configuration
   - Better validation
   
8. **LLM client DI** (1h)
   - Reduce duplication
   - Easier testing

---

## 📦 Proposed New Structure

### **Challenges (Community-Ready)**
```
app/challenges/
├── __init__.py          # Auto-discovery magic
├── base.py              # BaseChallenge (unchanged)
├── registry.py          # ChallengeRegistry (enhanced)
├── _template.py         # Template for new challenges
├── README.md            # How to create a challenge
├── filters/             # Shared utilities
├── contrib/             # Community challenges (future)
│   ├── __init__.py
│   └── your_challenge.py
└── official/            # Your challenges (future org)
    ├── glitch.py
    ├── arena.py
    └── ...
```

### **Frontend (DRY)**
```
app/static/js/
├── core/
│   ├── challenge-handler.js    # Base class (new)
│   ├── sse-client.js            # SSE parsing (extracted)
│   ├── fingerprint.js           # (existing)
│   └── utils.js                 # Shared utilities
├── handlers/
│   ├── glitch.js               # Extends ChallengeHandler
│   ├── arena.js                # Extends ChallengeHandler
│   └── ...
└── legacy/                     # Old handlers (delete after migration)
```

### **Templates (DRY)**
```
app/templates/
├── base.html                   # Site-wide base
├── challenges/
│   ├── base_challenge.html     # Challenge layout base
│   ├── _macros.html            # Reusable components
│   ├── _submission_form.html   # Standard form
│   ├── glitch.html             # Just unique content
│   ├── arena.html              # Just unique content
│   └── ...
├── pages/
│   ├── index.html
│   ├── leaderboard.html
│   └── ...
└── components/                 # Shared components
    ├── _header.html
    ├── _footer.html
    └── ...
```

---

## 🔧 Implementation Guide

### **Step 1: Auto-Discovery Pattern**

**Create `app/challenges/registry.py`:**
```python
"""Enhanced Challenge Registry with Auto-Discovery"""
import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, Type
from app.challenges.base import BaseChallenge

class ChallengeRegistry:
    _challenges: Dict[str, Type[BaseChallenge]] = {}
    _auto_discovered = False
    
    @classmethod
    def register(cls, challenge_class: Type[BaseChallenge]):
        """Decorator to register a challenge"""
        name = challenge_class.name if hasattr(challenge_class, 'name') else \
               challenge_class.__name__.replace('Challenge', '').lower()
        cls._challenges[name] = challenge_class
        return challenge_class
    
    @classmethod
    def auto_discover(cls):
        """Auto-discover and register challenges"""
        if cls._auto_discovered:
            return
        
        challenges_dir = Path(__file__).parent
        for filepath in challenges_dir.glob('*.py'):
            if filepath.stem.startswith('_'):
                continue  # Skip __init__, _template, etc.
            
            try:
                module_name = f'app.challenges.{filepath.stem}'
                module = importlib.import_module(module_name)
                
                # Find Challenge classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseChallenge) and 
                        obj != BaseChallenge and
                        not name.startswith('_')):
                        
                        # Register if not already registered
                        if hasattr(obj, '__challenge_name__'):
                            cls._challenges[obj.__challenge_name__] = obj
                        elif not any(obj == v for v in cls._challenges.values()):
                            # Auto-generate name
                            challenge_name = filepath.stem
                            cls._challenges[challenge_name] = obj
            
            except Exception as e:
                print(f"⚠️  Failed to import {filepath}: {e}")
        
        cls._auto_discovered = True
    
    @classmethod
    def get_all(cls) -> Dict[str, Type[BaseChallenge]]:
        """Get all registered challenges"""
        if not cls._auto_discovered:
            cls.auto_discover()
        return cls._challenges.copy()
```

**Update `app/challenges/__init__.py`:**
```python
"""Challenges module - Auto-discovers all challenges"""
from app.challenges.registry import ChallengeRegistry
from app.challenges.base import BaseChallenge

# Trigger auto-discovery
ChallengeRegistry.auto_discover()

# Export for backward compatibility
CHALLENGES = ChallengeRegistry.get_all()

__all__ = ['BaseChallenge', 'ChallengeRegistry', 'CHALLENGES']
```

**Now adding a challenge is just:**
```python
# app/challenges/my_new_challenge.py
from app.challenges.base import BaseChallenge

class MyNewChallenge(BaseChallenge):
    # That's it! Auto-discovered and registered!
    pass
```

---

### **Step 2: Generic JS Handler**

**Create `app/static/js/core/challenge-handler.js`:**
```javascript
/**
 * Generic Challenge Handler Base Class
 * All challenge-specific handlers extend this
 */
class ChallengeHandler {
    constructor(challengeName, resultsContainer, options = {}) {
        this.challengeName = challengeName;
        this.resultsDiv = typeof resultsContainer === 'string'
            ? document.getElementById(resultsContainer)
            : resultsContainer;
        
        this.options = {
            autoScroll: true,
            showThinking: true,
            ...options
        };
        
        // Event handlers map
        this.eventHandlers = {};
        this.isStreaming = false;
    }
    
    /**
     * Register an event handler
     * @param {string} eventType - Event type from SSE
     * @param {function} handler - Handler function
     */
    on(eventType, handler) {
        this.eventHandlers[eventType] = handler;
        return this; // Chainable
    }
    
    /**
     * Stream a challenge action
     * @param {object} actionData - Action-specific data
     * @param {string} difficulty - Optional difficulty level
     */
    async stream(actionData, difficulty = null) {
        if (this.isStreaming) {
            throw new Error('Already streaming');
        }
        
        this.isStreaming = true;
        this.showResults();
        
        try {
            // Build form data
            const formData = this.buildFormData(actionData, difficulty);
            
            // Get fingerprint headers
            const headers = await getFingerprintHeaders();
            
            // Make request
            const response = await fetch('/submit/stream', {
                method: 'POST',
                body: formData,
                headers: headers
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Submission failed');
            }
            
            // Process SSE stream
            await this.processSSE(response);
            
        } catch (error) {
            this.handleError(error);
        } finally {
            this.isStreaming = false;
        }
    }
    
    /**
     * Build form data for submission
     * Override if custom fields needed
     */
    buildFormData(actionData, difficulty) {
        const formData = new FormData();
        formData.append('challenge_name', this.challengeName);
        formData.append('agent_type', 'prompt');
        
        if (difficulty) {
            formData.append('difficulty', difficulty);
        }
        
        // Add action data
        if (typeof actionData === 'string') {
            formData.append('agent_code', actionData);
        } else if (typeof actionData === 'object') {
            formData.append('agent_code', JSON.stringify(actionData));
        }
        
        // Add username if available
        const username = document.getElementById('username')?.value;
        if (username) {
            formData.append('username', username);
        }
        
        return formData;
    }
    
    /**
     * Process Server-Sent Events stream
     */
    async processSSE(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const {done, value} = await reader.read();
            
            if (done) break;
            
            buffer += decoder.decode(value, {stream: true});
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        this.handleEvent(data);
                    } catch (e) {
                        console.error('Failed to parse SSE:', e);
                    }
                }
            }
        }
    }
    
    /**
     * Route event to appropriate handler
     */
    handleEvent(data) {
        const eventType = data.type || data.event;
        
        // Call registered handler if exists
        if (this.eventHandlers[eventType]) {
            this.eventHandlers[eventType](data);
        } else {
            // Default handlers
            switch(eventType) {
                case 'error':
                    this.handleError(data);
                    break;
                case 'complete':
                    this.handleComplete(data);
                    break;
                default:
                    console.warn('Unhandled event:', eventType, data);
            }
        }
    }
    
    /**
     * Default error handler
     */
    handleError(error) {
        const message = error.message || error.error || 'Unknown error';
        this.resultsDiv.innerHTML += `
            <div class="error-message">
                <strong>❌ Error:</strong> ${this.escapeHtml(message)}
            </div>
        `;
    }
    
    /**
     * Default completion handler
     */
    handleComplete(data) {
        // Subclasses should override
        console.log('Challenge complete:', data);
    }
    
    /**
     * Show results container
     */
    showResults() {
        if (this.resultsDiv) {
            this.resultsDiv.style.display = 'block';
        }
    }
    
    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Export
window.ChallengeHandler = ChallengeHandler;
```

**Now challenges become tiny:**
```javascript
// app/static/js/handlers/glitch.js
class GlitchHandler extends ChallengeHandler {
    constructor(resultsContainer, level) {
        super('glitch', resultsContainer);
        this.level = level;
        
        // Register event handlers
        this.on('bot_response', (data) => this.renderBotResponse(data));
        this.on('success', (data) => this.handleSuccess(data));
        this.on('thinking', (data) => this.showThinking(data));
    }
    
    renderBotResponse(data) {
        // Just the unique rendering logic
        this.resultsDiv.innerHTML += `
            <div class="bot-message">${data.response}</div>
        `;
    }
    
    handleSuccess(data) {
        this.resultsDiv.innerHTML += `
            <div class="success">🎉 You broke the bot!</div>
        `;
    }
}
```

---

## 📝 Challenge Creation Template

**Create `app/challenges/_TEMPLATE.py`:**
```python
"""
Challenge Template
Copy this file to create a new challenge!

1. Copy this file: cp _TEMPLATE.py my_challenge.py
2. Rename the class
3. Implement the abstract methods
4. That's it! Auto-discovered and registered!
"""
from typing import Dict, Any, List
from app.challenges.base import BaseChallenge, StepResult, ChallengeResult

class MyChallenge(BaseChallenge):
    """
    Brief description of your challenge
    
    Explain what the user needs to do to win.
    """
    
    def __init__(self, config=None, **kwargs):
        super().__init__(config, **kwargs)
        # Initialize your challenge state
        self.score = 0
    
    @property
    def name(self) -> str:
        """Unique identifier (lowercase, no spaces)"""
        return "my_challenge"
    
    @property
    def display_name(self) -> str:
        """Human-readable name with emoji"""
        return "🎯 My Challenge"
    
    @property
    def description(self) -> str:
        """Short description for the UI"""
        return "A brief description of what this challenge does"
    
    @property
    def max_steps(self) -> int:
        """Maximum number of actions allowed"""
        return 100
    
    @property
    def allowed_actions(self) -> List[str]:
        """List of valid action strings"""
        return ["ACTION_1", "ACTION_2"]
    
    @property
    def challenge_type(self) -> str:
        """Type for routing (e.g., 'code', 'prompt', 'debate')"""
        return "generic"
    
    @property
    def supports_streaming(self) -> bool:
        """Whether this challenge supports SSE streaming"""
        return True
    
    @property
    def template_name(self) -> str:
        """Custom template name (or None for default)"""
        return "my_challenge_detail.html"
    
    def reset(self) -> Dict[str, Any]:
        """
        Reset challenge to initial state
        
        Returns:
            Initial observation dictionary
        """
        self.score = 0
        return {
            "message": "Challenge started!",
            "score": self.score
        }
    
    def step(self, action: str) -> StepResult:
        """
        Execute one step of the challenge
        
        Args:
            action: The action string from the agent
            
        Returns:
            StepResult with observation, reward, done flag, and info
        """
        # Your challenge logic here
        observation = {"message": f"You took action: {action}"}
        reward = 10
        done = False
        info = {"step_count": 1}
        
        return StepResult(
            observation=observation,
            reward=reward,
            done=done,
            info=info
        )
    
    def render(self) -> str:
        """
        Render current state as string
        
        Returns:
            String representation of state
        """
        return f"Score: {self.score}"
```

---

## 💡 Community Contribution Guide

**Create `app/challenges/README.md`:**
```markdown
# Creating a Jankyard Challenge

## Quick Start

1. **Copy the template:**
   ```bash
   cp _TEMPLATE.py your_challenge_name.py
   ```

2. **Implement the required methods:**
   - `name` - Unique identifier
   - `display_name` - Human-readable name
   - `description` - What the challenge is about
   - `reset()` - Initialize challenge state
   - `step()` - Process one action
   - `render()` - Display current state

3. **Test locally:**
   ```bash
   python -m pytest tests/test_your_challenge.py
   ```

4. **Submit a PR!**
   - Challenges are auto-discovered
   - No need to edit __init__.py
   - Just add your file and go!

## Challenge Types

### Prompt-Based Challenges
Users submit a prompt, you evaluate it:
```python
def step(self, action: str) -> StepResult:
    # action is the user's prompt
    response = self.llm_client.call(
        system_prompt="Your system prompt",
        user_message=action
    )
    # Evaluate response
    success = self.check_success(response)
    return StepResult(...)
```

### Code-Based Challenges
Users submit Python code:
```python
def step(self, action: str) -> StepResult:
    # action is return value from user's act() function
    # Update game state
    # Check win condition
    return StepResult(...)
```

### Multi-Turn Challenges
Challenges with multiple rounds:
```python
def reset(self):
    self.round = 0
    self.history = []
    return {"round": 0}

def step(self, action):
    self.round += 1
    self.history.append(action)
    done = self.round >= MAX_ROUNDS
    return StepResult(done=done, ...)
```

## Scoring Guidelines

- Base score: 100-1000 points
- Difficulty multipliers: 1.0x (easy), 1.5x (medium), 2.0x (hard)
- Efficiency bonuses: Reward fewer steps
- Creativity bonuses: Reward novel solutions

## Templates

Create a template in `app/templates/your_challenge_detail.html`:
```html
{% extends "challenges/base_challenge.html" %}

{% block challenge_header %}
<h1>🎯 Your Challenge</h1>
<p>Description here</p>
{% endblock %}

{% block challenge_js %}
<script src="/static/js/handlers/your_challenge.js"></script>
{% endblock %}
```

## JavaScript Handler

Create a handler in `app/static/js/handlers/your_challenge.js`:
```javascript
class YourChallengeHandler extends ChallengeHandler {
    constructor(resultsContainer) {
        super('your_challenge', resultsContainer);
        
        this.on('custom_event', (data) => this.handleCustomEvent(data));
    }
    
    handleCustomEvent(data) {
        // Your rendering logic
    }
}
```

## Examples

See existing challenges:
- `glitch.py` - Prompt injection (simple)
- `arena.py` - Turn-based combat (medium)
- `interrogation.py` - Multi-witness (complex)
```

---

## 📊 Expected Impact

### **Code Metrics**

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Lines of JS | ~70KB | ~25KB | **-64%** |
| Lines of HTML | ~150KB | ~55KB | **-63%** |
| Challenge Registration | Manual | Auto | **∞%** |
| Time to Add Challenge | ~4 hours | **~1 hour** | **-75%** |

### **Developer Experience**

| Task | Before | After | Improvement |
|------|--------|-------|-------------|
| Add new challenge | Edit 5+ files | 1 file | **5x faster** |
| Understand codebase | Hunt through duplication | Clear patterns | **3x faster** |
| Fix a bug | Change 7 places | Change 1 place | **7x safer** |
| Onboard contributor | 2-3 days | Few hours | **4x faster** |

---

## ✅ Acceptance Criteria

### **Phase 1 Complete When:**
- [ ] New challenge added in <2 hours
- [ ] No manual registration needed
- [ ] JS handlers <5KB each
- [ ] Templates <3KB each
- [ ] All existing challenges still work

### **Phase 2 Complete When:**
- [ ] No direct DB queries in routes
- [ ] Services use FastAPI DI
- [ ] All errors use custom exceptions
- [ ] Test coverage >70%

### **Phase 3 Complete When:**
- [ ] Config is typed and validated
- [ ] LLM clients use DI
- [ ] Documentation is complete
- [ ] Community can contribute easily

---

## 🎯 Next Steps

**What should we tackle first?**

1. **Auto-discovery** → Enables everything else
2. **Generic JS handler** → 70% code reduction
3. **Template refactor** → Faster development

**Estimated time: 4-6 hours total**
**Best done: Before adding more features**

---

**Want me to start implementing? I can do Phase 1 in one session!**
