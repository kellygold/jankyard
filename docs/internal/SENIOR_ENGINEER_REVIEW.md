# Senior Engineer Code Review - Jankyard.ai

**Date:** January 2026  
**Reviewer:** AI Code Analysis  
**Codebase:** FastAPI + SQLAlchemy + Multi-Agent LLM Challenges

---

## Executive Summary

The codebase is **functional and well-structured** for a side project, with clear separation of concerns and a solid challenge framework. However, there are several areas that would benefit from improvement before scaling or production hardening.

**Priority Levels:** 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low

---

## 1. Architecture Issues

### 🟠 HIGH: God Objects in Challenges
**Location:** `app/challenges/` (interrogation.py: 1096 LOC, telephone_game.py: 737 LOC)

**Problem:** Several challenge files exceed 500+ lines with mixed responsibilities (game logic, LLM calls, scoring, UI state).

**Recommendation:**
```
challenges/
  interrogation/
    __init__.py          # Challenge class
    game_logic.py        # Core game mechanics
    llm_prompts.py       # System prompts
    scoring.py           # Score calculation
```

### 🟡 MEDIUM: Inconsistent Async Patterns
**Finding:** Only 15 async functions vs 244 sync functions in challenges, but routes use async handlers.

**Problem:** Mixing sync LLM calls with async routes causes blocking. The `run_in_threadpool` workaround in `submissions.py:118` is a symptom.

**Recommendation:** Make LLM client fully async:
```python
# app/llm/client.py
async def call_async(self, system_prompt: str, user_message: str) -> str:
    if self.provider == "openai":
        response = await self.openai_client.chat.completions.acreate(...)
```

### 🟡 MEDIUM: Manual DB Session Management
**Location:** `app/routes/submissions.py:107-111`

```python
# Anti-pattern: Manual close
try:
    db.close()
except:
    pass
```

**Recommendation:** Use context managers or let FastAPI dependency handle lifecycle.

---

## 2. Code Quality Issues

### 🟠 HIGH: Bare Except Clauses (11 instances)
**Problem:** Silent exception swallowing hides bugs.

**Bad:**
```python
except:
    pass
```

**Good:**
```python
except ValueError as e:
    logger.warning(f"Expected error: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise
```

### 🟠 HIGH: Inline Imports (10+ instances)
**Location:** `app/routes/submissions.py:31, 53, 77, 94, 198, 240, 272, 319, 328, 335`

**Problem:** Imports inside functions suggest circular dependency issues or lazy loading hacks.

**Recommendation:** 
1. Refactor to break circular dependencies
2. Use `TYPE_CHECKING` for type hints
3. Move shared utilities to dedicated modules

### 🟡 MEDIUM: Inconsistent Logging Setup
**Finding:** 10 files with `import logging` but inconsistent logger naming.

**Current:**
```python
logger = logging.getLogger(__name__)  # Sometimes
import logging; logger = logging.getLogger(__name__)  # Inline
```

**Recommendation:** Use centralized logger factory:
```python
from app.core.logging import get_logger
logger = get_logger(__name__)
```

### 🟢 LOW: Magic Strings
**Problem:** Difficulty levels use string literals scattered across files.

```python
# Firewall
"LEVEL_1", "LEVEL_2", "LEVEL_3"
# GigaChad
"BABY_CHAD", "CHAD", "MEGA_CHAD", "GIGA_CHAD"
# Glitch
"level_1", "level_2", "level_3"  # Different casing!
```

**Recommendation:** Use enums:
```python
class FirewallDifficulty(str, Enum):
    LEVEL_1 = "LEVEL_1"
    LEVEL_2 = "LEVEL_2"
    LEVEL_3 = "LEVEL_3"
```

---

## 3. Security Concerns

### 🔴 CRITICAL: Hardcoded Secret Key Fallback
**Location:** `app/core/config.py:15`

```python
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
```

**Problem:** If env var is missing in production, insecure default is used silently.

**Fix:**
```python
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY and ENVIRONMENT != "development":
    raise ValueError("SECRET_KEY must be set in production")
```

### 🟠 HIGH: CORS Wildcard in Debug
**Location:** `app/main.py:42`

```python
allow_origins=["*"] if config.DEBUG else [...]
```

**Problem:** `DEBUG` is based on `ENVIRONMENT == "development"`, which could be misconfigured.

**Recommendation:** Explicit allowlist even in dev.

### 🟡 MEDIUM: No Input Sanitization on Username
**Location:** `app/routes/submissions.py:81-83`

```python
elif username:
    effective_username = username  # Directly from user input
```

**Recommendation:** Validate/sanitize username:
```python
import re
if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
    return JSONResponse({"error": "Invalid username"}, status_code=400)
```

### 🟡 MEDIUM: LLM Response Not Sanitized
**Problem:** LLM responses are streamed directly to frontend without sanitization.

**Risk:** Prompt injection could cause XSS if response contains `<script>` tags.

**Recommendation:** Escape HTML in LLM responses before sending to client.

---

## 4. Performance Issues

### 🟠 HIGH: N+1 Query Risk in Leaderboard
**Location:** `app/routes/leaderboard.py`

**Problem:** Iterating through entries and checking related data could cause N+1.

**Recommendation:** Use `joinedload` or batch queries.

### 🟡 MEDIUM: No Connection Pooling Config
**Location:** `app/core/database.py`

**Recommendation:** Configure pool size for production:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)
```

### 🟡 MEDIUM: LLM Client Created Per-Request
**Problem:** Each challenge creates new `LLMClient()` instance.

**Recommendation:** Use singleton or dependency injection for client reuse.

---

## 5. Testing Gaps

### Current State
- **API tests:** ✅ Good coverage for auth, progress, leaderboard
- **E2E tests:** ✅ Playwright tests exist
- **Unit tests:** ⚠️ Limited coverage on challenge logic
- **Integration:** ⚠️ No database migration tests

### Missing Tests
1. **Challenge edge cases** - What happens when LLM times out?
2. **Rate limiting** - No tests for rate limit behavior
3. **Concurrent submissions** - Race condition testing
4. **Error recovery** - DB connection failure handling

### Recommendation: Add Test Categories
```python
# pytest.ini
markers =
    unit: Pure logic tests (no IO)
    integration: Tests with database
    e2e: Full browser tests
    slow: Tests that hit real LLM APIs
```

---

## 6. Documentation Debt

### Issues Found
- **Tmp files in codebase:** `tmp.telephonegame.txt`, `tmp.telephonepersonas.txt`
- **Multiple planning docs:** 6+ `.md` files with overlapping content
- **No API documentation:** No OpenAPI descriptions on endpoints

### Recommendation
1. Delete tmp files
2. Consolidate docs into `docs/` folder
3. Add endpoint docstrings for auto-generated OpenAPI docs

---

## 7. Quick Wins (< 1 hour each)

| Priority | Task | Impact |
|----------|------|--------|
| 🔴 | Fix SECRET_KEY fallback | Security |
| 🟠 | Replace bare excepts with specific ones | Debugging |
| 🟠 | Add username validation | Security |
| 🟡 | Create difficulty enums | Maintainability |
| 🟡 | Delete tmp files | Cleanliness |
| 🟢 | Add type hints to route handlers | IDE support |

---

## 8. Recommended Refactoring Roadmap

### Phase 1: Security Hardening (1-2 days)
- [ ] Fix SECRET_KEY fallback
- [ ] Add input validation
- [ ] Sanitize LLM outputs
- [ ] Audit CORS settings

### Phase 2: Code Quality (3-5 days)
- [ ] Replace bare excepts
- [ ] Centralize logging
- [ ] Create difficulty enums
- [ ] Move inline imports to top of files

### Phase 3: Architecture (1-2 weeks)
- [ ] Make LLM client async
- [ ] Split large challenge files
- [ ] Add connection pooling
- [ ] Implement proper dependency injection

### Phase 4: Testing (1 week)
- [ ] Add unit tests for challenge logic
- [ ] Add rate limit tests
- [ ] Add concurrent submission tests
- [ ] Add LLM timeout handling tests

---

## Summary

**Strengths:**
- Clean separation between routes/services/repositories
- Well-designed challenge base class with registry pattern
- Good use of FastAPI features (dependency injection, streaming)
- Existing test infrastructure

**Areas for Improvement:**
- Security hardening (especially secrets management)
- Exception handling discipline
- Async consistency
- Large file decomposition
- Test coverage for edge cases

**Overall Assessment:** Solid foundation for a hobby/side project. Needs hardening before production scale or if handling sensitive data.
