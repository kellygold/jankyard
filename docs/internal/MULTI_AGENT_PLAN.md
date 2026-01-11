# Generic Multi-Agent Challenge System - Implementation Plan

## 🎯 GOAL

Enable contributors to build **BOTH single-agent AND multi-agent** challenges with just 2 files:
1. **Backend** - Python challenge class
2. **Frontend** - HTML template

**Same pattern, same simplicity, whether you have 1 agent or 10 agents.**

---

## 📋 Implementation Phases

### **Phase 1: Standardize Message Format** ✅ DO FIRST
**Why:** All challenges need to speak the same language

**Standardized SSE Event Structure:**
```python
{
    'type': str,        # 'thinking', 'message', 'judgment', 'update', 'complete', 'error'
    'agent': str,       # 'user', 'junior', 'manager', 'judge', 'system'
    'data': dict,       # Event-specific payload
    'metadata': dict    # Optional context (round, step, etc.)
}
```

**Files to modify:**
- ✏️ `app/challenges/base.py` - Update default `stream_events()` to use standard format
- ✏️ `app/utils/generic_stream.py` - Update legacy `_stream_*` functions to standard format
- ✏️ Frontend handlers (optional) - Ensure compatibility with standard format

**Outcome:** 
- Trivia (single-agent) emits standardized events
- Debate (multi-agent) emits standardized events
- No breaking changes

---

### **Phase 2: Create Agent Infrastructure**
**Why:** Need models for multi-agent challenges

**New files:**

**➕ `app/challenges/agents.py`** - Agent & Turn models
```python
@dataclass
class Agent:
    """Represents an AI agent in a multi-agent challenge"""
    name: str              # 'junior', 'manager', 'ceo'
    role: str              # 'Junior Developer'
    system_prompt: str     # Agent's personality/instructions
    model: str = 'gpt-4'
    temperature: float = 0.7
    max_tokens: int = 200

@dataclass
class ConversationTurn:
    """Single turn in a multi-agent conversation"""
    agent: str                              # Who's acting
    message: str = ''                       # What they say (empty for thinking)
    type: str = 'message'                   # 'thinking', 'message', 'judgment'
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Outcome:**
- Standard way to define agents
- Standard way to describe conversation turns

---

### **Phase 3: Create Conversation Orchestrator**
**Why:** Generic engine to run any multi-agent conversation

**New file:**

**➕ `app/challenges/orchestrator.py`** - Generic conversation runner
```python
async def run_conversation(
    conversation_flow: AsyncGenerator[ConversationTurn, None],
    agents: Dict[str, Agent],
    llm_client: LLMClient
) -> AsyncGenerator[str, None]:
    """
    Generic orchestrator for ANY multi-agent conversation.
    
    Input: ConversationTurn objects from challenge
    Output: Standardized SSE events
    
    Handles:
    - Thinking indicators
    - Agent LLM calls
    - Message formatting
    - Error handling
    """
```

**Outcome:**
- Contributors never write streaming code
- Just yield ConversationTurn objects
- Orchestrator handles the rest

---

### **Phase 4: Enhance BaseChallenge**
**Why:** Make multi-agent support built-in, auto-detected

**Modify:** ✏️ `app/challenges/base.py`

**Add to BaseChallenge:**
```python
class BaseChallenge(ABC):
    # === NEW: Multi-agent support (optional) ===
    agents: Dict[str, Agent] = {}  # Empty = single-agent
    
    async def conversation_flow(
        self, 
        user_input: str, 
        context: Dict[str, Any]
    ) -> AsyncGenerator[ConversationTurn, None]:
        """
        OPTIONAL: Override for multi-agent challenges.
        Yield ConversationTurn objects to define the conversation.
        """
        raise NotImplementedError("Override for multi-agent challenges")
    
    async def call_agent(self, agent_name: str, message: str, context: Dict = None) -> str:
        """
        Helper to call an agent and get response.
        Available to all multi-agent challenges.
        """
        agent = self.agents[agent_name]
        return self.llm_client.call(
            system_prompt=agent.system_prompt,
            user_message=message,
            temperature=agent.temperature,
            max_tokens=agent.max_tokens
        )
    
    async def stream_events(self, user_action: str, llm_client=None):
        """
        ENHANCED: Auto-detect single vs multi-agent pattern
        """
        # Multi-agent: has agents + conversation_flow
        if self.agents and hasattr(self, 'conversation_flow'):
            from app.challenges.orchestrator import run_conversation
            async for event in run_conversation(
                self.conversation_flow(user_action, {}),
                self.agents,
                llm_client or getattr(self, 'llm_client', None)
            ):
                yield event
        
        # Single-agent: use existing simple streaming
        else:
            # ... existing implementation (already standardized in Phase 1)
```

**Outcome:**
- System auto-detects challenge type
- No manual registration needed
- Both patterns use same base class

---

### **Phase 5: Create Example Challenges**

**Example 1: Single-Agent** (already exists, just verify)
**✅ `app/challenges/trivia.py`**
```python
class TriviaChallenge(BaseChallenge):
    def reset(self): ...
    def step(self): ...
    # Done! 2 files total
```

**Example 2: Multi-Agent** (new)
**➕ `app/challenges/corporate_ladder.py`**
```python
class CorporateLadderChallenge(BaseChallenge):
    agents = {
        'junior': Agent(...),
        'manager': Agent(...),
        'vp': Agent(...),
        'ceo': Agent(...)
    }
    
    async def conversation_flow(self, user_input, context):
        # Yield turns to define conversation
        yield Turn(agent='user', message=user_input, type='message')
        yield Turn(agent='junior', type='thinking')
        response = await self.call_agent('junior', user_input)
        yield Turn(agent='junior', message=response, type='message')
        # ... chain continues
    
    def reset(self): ...
    def step(self): ...
    # Done! 2 files total
```

**➕ `app/templates/challenges/corporate_ladder.html`**
```html
{% extends "challenges/base_challenge.html" %}
<script>
const handler = new ChallengeHandler('corporate_ladder', 'results');
handler.on('complete', (data) => {
    if (data.result.success) showSuccessModal({...});
    else showFailureModal({...});
});
</script>
```

**Outcome:**
- Clear examples of both patterns
- Same simplicity for both
- 2 files each

---

### **Phase 6: Update Documentation**
**Why:** Contributors need to know the patterns

**Modify:** ✏️ `docs/ADDING_CHALLENGES.md`

**Add sections:**
- Single-Agent Pattern (Trivia example)
- Multi-Agent Pattern (Corporate Ladder example)
- When to use which
- Standardized event format reference

---

## 📁 Files Summary

| File | Action | Purpose |
|------|--------|---------|
| **Phase 1: Standardize** | | |
| `app/challenges/base.py` | ✏️ MODIFY | Standardize `stream_events()` output |
| `app/utils/generic_stream.py` | ✏️ MODIFY | Standardize legacy stream functions |
| **Phase 2: Agent Models** | | |
| `app/challenges/agents.py` | ➕ NEW | Agent & ConversationTurn models |
| **Phase 3: Orchestrator** | | |
| `app/challenges/orchestrator.py` | ➕ NEW | Generic conversation runner |
| **Phase 4: Enhanced Base** | | |
| `app/challenges/base.py` | ✏️ MODIFY | Add multi-agent support (again) |
| **Phase 5: Examples** | | |
| `app/challenges/trivia.py` | ✅ VERIFY | Single-agent example |
| `app/challenges/corporate_ladder.py` | ➕ NEW | Multi-agent example |
| `app/templates/challenges/corporate_ladder.html` | ➕ NEW | Multi-agent frontend |
| **Phase 6: Docs** | | |
| `docs/ADDING_CHALLENGES.md` | ✏️ MODIFY | Document both patterns |

---

## ✅ Success Criteria

**For Contributors:**
- ✅ Single-agent challenge = 2 files (Python + HTML)
- ✅ Multi-agent challenge = 2 files (Python + HTML)
- ✅ Same base class for both
- ✅ System auto-detects pattern

**For Single-Agent Challenges:**
- ✅ Trivia still works
- ✅ Uses standardized events
- ✅ No breaking changes

**For Multi-Agent Challenges:**
- ✅ Corporate Ladder works with 2 files
- ✅ Chain of persuasion flows correctly
- ✅ Each agent shows thinking indicators
- ✅ Uses same standardized events
- ✅ Progress saves automatically
- ✅ Modals work automatically

**For Existing Multi-Agent:**
- ✅ Debate still works (uses legacy fallback initially)
- ✅ Can be migrated to new pattern later
- ✅ No breaking changes

---

## 🎯 Usage Examples

### Single-Agent Challenge (Firewall)
```python
class FirewallChallenge(BaseChallenge):
    """User's LLM vs deterministic system logic"""
    
    def reset(self):
        return {'message': 'Try to bypass the filters'}
    
    def step(self, action: str):
        if self._check_filters(action):
            return StepResult(
                observation={'message': 'Blocked!'},
                reward=0,
                done=False,
                info={}
            )
        return StepResult(
            observation={'message': 'Success!'},
            reward=100,
            done=True,
            info={}
        )
    
    def _check_filters(self, prompt: str) -> bool:
        # Your custom logic
        return 'ignore' in prompt.lower()
```

### Multi-Agent Challenge (Corporate Ladder)
```python
class CorporateLadderChallenge(BaseChallenge):
    """User agent convinces chain of corporate agents"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.llm_client = LLMClient()
        
        self.agents = {
            'junior': Agent(
                name='junior',
                role='Junior Developer',
                system_prompt='You are enthusiastic but cautious...',
                model='gpt-4'
            ),
            'manager': Agent(
                name='manager',
                role='Engineering Manager',
                system_prompt='You care about timelines and team morale...',
                model='gpt-4'
            ),
            'vp': Agent(
                name='vp',
                role='VP of Engineering',
                system_prompt='You focus on ROI and business value...',
                model='gpt-4o'
            )
        }
    
    async def conversation_flow(self, user_proposal, context):
        """Define the conversation chain"""
        # User proposes to junior
        yield ConversationTurn(
            agent='user',
            message=user_proposal,
            type='message'
        )
        
        # Junior thinks
        yield ConversationTurn(
            agent='junior',
            type='thinking'
        )
        
        # Junior responds
        junior_response = await self.call_agent(
            'junior',
            f"Proposal: {user_proposal}. Will you support it?"
        )
        yield ConversationTurn(
            agent='junior',
            message=junior_response,
            type='message'
        )
        
        # Check approval
        if not self._is_approved(junior_response):
            return  # Chain broken, orchestrator sends failure
        
        # Junior pitches to manager
        yield ConversationTurn(
            agent='manager',
            type='thinking'
        )
        
        manager_response = await self.call_agent(
            'manager',
            f"Junior says: {junior_response}. Will you escalate?"
        )
        yield ConversationTurn(
            agent='manager',
            message=manager_response,
            type='message'
        )
        
        # ... continue chain to VP, etc.
    
    def _is_approved(self, response: str) -> bool:
        """Helper to check if agent approved"""
        positive = ['yes', 'approve', 'support']
        return any(word in response.lower() for word in positive)
    
    def reset(self):
        return {'message': 'Pitch your idea to the junior developer'}
    
    def step(self, action):
        return StepResult(
            observation={'message': 'Use streaming mode'},
            reward=0,
            done=True,
            info={}
        )
```

---

## 🚀 Implementation Order

1. **Phase 1** - Standardize messages (foundation for everything)
2. **Phase 2** - Create agent models (needed by orchestrator)
3. **Phase 3** - Build orchestrator (uses agent models)
4. **Phase 4** - Enhance BaseChallenge (uses orchestrator)
5. **Phase 5** - Build Corporate Ladder example (uses enhanced base)
6. **Phase 6** - Update docs (document the patterns)

---

**Status:** Ready to begin Phase 1
**Next Step:** Standardize SSE event format in `base.py` and `generic_stream.py`
