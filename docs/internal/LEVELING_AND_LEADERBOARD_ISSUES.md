# Leveling System & Leaderboard Issues

**Date:** January 2026  
**Status:** Documentation of current inconsistencies (no fixes applied)

---

## Executive Summary

The codebase has a **standard leveling infrastructure** that was built, but **each challenge implements it differently**. This causes:
1. Next Level buttons breaking when customizing win screens
2. Inconsistent behavior across challenges
3. Progress not persisting correctly in some cases
4. Different experiences for logged-in vs anonymous users

---

## Part 1: Modal & Next Level System

### Standard Infrastructure (Exists)

| Component | Location | Purpose |
|-----------|----------|---------|
| `ChallengeHandler.checkUnlockedLevels()` | `app/static/js/core/challenge-handler.js:424-447` | Fetches unlocked levels from server |
| `ChallengeHandler.updateLevelTabs()` | `app/static/js/core/challenge-handler.js:459-473` | Updates tab UI based on unlocked levels |
| `ChallengeHandler.init()` | `app/static/js/core/challenge-handler.js:494-557` | Standardized init (auth, username, levels) |
| `_completion_modal.html` macro | `app/templates/challenges/_completion_modal.html` | Shared modal with `showCompletionModal()`, `showDefeatModal()` |
| `_level_tabs.html` | `app/templates/challenges/_level_tabs.html` | Shared level tab component |

### The Problem: Every Challenge Does It Differently

| Challenge | Modal Implementation | Next Level Button | Level Unlock Location | State Management |
|-----------|---------------------|-------------------|----------------------|------------------|
| **Glitch** | Custom `successModal` in template HTML | Own `nextLevelBtn`, own `showSuccessModal()` in template script | Handler's `handleLevelComplete()` | Handler's `this.unlockedLevels` |
| **Interrogation** | Custom `successModal` in template HTML | Own `nextLevelBtn`, own `showSuccessModal()` in handler class | Handler's `showSuccessModal()` method | Handler's `this.unlockedLevels` |
| **Giga Chad** | Custom `gigaChadVictoryModal` in template | Overrides global `showCompletionModal` function | Template wraps `handleComplete` | Template outer scope + handler sync |
| **Firewall** | Uses shared `_completion_modal` | Uses shared modal's button | Handler's `handleComplete()` | Handler's `this.unlockedLevels` |
| **Debate** | Uses shared `_completion_modal` | Uses shared modal's button | Handler's `handleComplete()` | Handler's `this.currentLevel` only |
| **Arena** | Uses shared `_completion_modal` | Uses shared modal's button | Template wraps `handleComplete` | Template outer scope `unlockedLevels` |

### Why Customization Breaks Things

When you customize a win screen, you typically:
1. Create custom modal HTML (replacing shared modal)
2. Create custom `showSuccessModal()` function (overriding shared one)
3. Manage `nextLevelBtn` differently

**But the level unlock logic is scattered:**
- Some in JS handler class (`handleComplete`)
- Some in template `<script>` that wraps handler
- Some rely on outer scope variables that don't sync with handler

**Result:** Custom modal works, but next level button breaks because:
- Handler unlocks level but custom modal doesn't know about it
- Or: Custom modal has button but handler's state wasn't updated
- Or: Server sync after completion is missing

### Root Cause Pattern

```
┌─────────────────────────────────────────────────────────────┐
│ Template Script (outer scope)                                │
│   - unlockedLevels = [1, 2]  ← from Jinja context           │
│   - Wraps handler.handleComplete()                           │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │ Handler Class                                        │   │
│   │   - this.unlockedLevels = [...] ← DIFFERENT COPY    │   │
│   │   - handleComplete() pushes to this.unlockedLevels  │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
│ PROBLEM: Two copies of unlockedLevels that can get out of   │
│ sync. When handler unlocks level, outer scope doesn't know. │
└─────────────────────────────────────────────────────────────┘
```

### Button Text Inconsistency

| Challenge | Button Text |
|-----------|-------------|
| Shared Modal | "➡️ Next Level" |
| Glitch | "➡️ Next Level" |
| Interrogation | "Next Level" |
| Giga Chad | "➜ NEXT LEVEL" (terminal style) / "💪 Next Chad" |
| Debate | "💼 Next Case" |

### Close Button Says "Continue" Everywhere

The shared modal's close button says "Continue" which is confusing when there's also a "Next Level" button.

---

## Part 2: Leaderboard & Progress Issues

### How Progress Tracking Works

```
1. User completes challenge
2. Backend saves to submissions table
3. Backend updates leaderboard table (if score is better)
4. Frontend can query /leaderboard/{challenge}/progress to get unlocked_levels
```

### Signed-In vs Anonymous Users

| Aspect | Signed-In User | Anonymous User |
|--------|---------------|----------------|
| Username source | `current_user.username` from JWT | Form field OR auto-generated (e.g., "GoofyPanther42") |
| `user_id` in DB | User's actual ID | `NULL` |
| Progress endpoint | Works - fetches from `/leaderboard/{challenge}/progress` | **FAILS** - endpoint requires auth (`get_current_user`) |
| Level unlock on reload | ✅ Persists (server fetch) | ❌ Resets to level 1 |
| Leaderboard entry | Linked to account | Orphaned (can't reclaim) |

### Key Issue: Progress Endpoint Requires Auth

```python
# app/routes/leaderboard.py:83-88
@router.get("/{challenge_name}/progress", response_class=JSONResponse)
async def get_user_progress(
    challenge_name: str,
    current_user: User = Depends(get_current_user),  # ← REQUIRES AUTH!
    db: Session = Depends(get_db)
):
```

**Impact:** Anonymous users who enter a username in the form:
1. Get their score saved to leaderboard under that username
2. Can see themselves on the leaderboard page
3. But CANNOT fetch their progress on page reload (endpoint 401s)
4. So levels reset to 1 even though they beat levels

### Anonymous Username Generation

When no username provided, backend generates random name:
```python
# app/routes/submissions.py:86-87
from app.utils.name_generator import generate_anonymous_username
effective_username = generate_anonymous_username()  # e.g., "GoofyPanther42"
```

This means:
- Score appears on leaderboard under random name
- User has no way to reclaim or continue with that identity
- Each submission gets a NEW random name if form is blank

### Frontend Auth Flow Issues

```javascript
// app/static/js/core/challenge-handler.js:424-446
static async checkUnlockedLevels(challengeName) {
    const token = localStorage.getItem('access_token');
    if (!token) {
        return [1]; // Guest = only level 1
    }
    // ... fetch from /progress endpoint
}
```

**Flow:**
1. No token → returns `[1]` immediately (no server check)
2. Has token → fetches from server

**Missing:** No fallback for "user entered username but isn't logged in" case.

### Username Field Handling Varies

| Challenge | Username Field Behavior |
|-----------|------------------------|
| Giga Chad | Pre-filled from `current_user`, readonly if logged in |
| Firewall | Placeholder only, uses `ChallengeHandler.init()` to prefill |
| Arena | Placeholder only, uses `ChallengeHandler.init()` to prefill |
| Interrogation | Placeholder only, separate init in template |
| Glitch | Has own init, similar pattern |
| Jank Maze | Has own `prefillUsername()` function |

---

## Part 3: jankyard2 Uncommitted Changes

The `/Users/teebox-admin/Code/jankyard2/jankyard` repo has 4 uncommitted files with changes that are **unrelated to modal/level issues**:

| File | Change |
|------|--------|
| `app/challenges/arena.py` | Refactoring `StepResult` to use `reward`/`done`/`info` instead of `status`/`complete` |
| `app/challenges/glitch.py` | Same refactoring |
| `app/challenges/interrogation.py` | Same refactoring + `status.value` for enum |
| `app/utils/generic_stream.py` | Using `status.value` instead of `status` (enum to string) |

These are backend API changes, not related to the frontend modal issues.

---

## Recommendations (When Ready to Fix)

### Option A: Standardize on Shared Modal

1. Remove custom modals from Glitch, Interrogation, Giga Chad
2. Use `_completion_modal.html` macro with customization params
3. Pass theme colors, icons, button text as macro arguments
4. Single source of truth for modal logic

### Option B: Standardize Level Unlock Pattern

Create ONE pattern all challenges follow:
```javascript
// In handler's handleComplete():
async handleComplete(data) {
    const result = data.result || data;
    if (result.success) {
        // 1. Optimistically unlock next level locally
        const nextLevel = this.currentLevel + 1;
        if (!this.unlockedLevels.includes(nextLevel)) {
            this.unlockedLevels.push(nextLevel);
        }
        
        // 2. Update UI
        ChallengeHandler.updateLevelTabs(this.unlockedLevels, this.maxLevel);
        
        // 3. Sync with server (in background)
        const serverLevels = await ChallengeHandler.checkUnlockedLevels(this.challengeName);
        this.unlockedLevels = serverLevels;
        
        // 4. Show modal with correct next_level info
        showCompletionModal({
            ...result,
            unlocked_next_level: this.unlockedLevels.includes(nextLevel),
            next_level: nextLevel
        });
    }
}
```

### Option C: Fix Anonymous User Progress

1. Change `/progress` endpoint to use `get_current_user_optional`
2. Accept `username` query param for anonymous users
3. Store username in localStorage when form submitted
4. On reload, check localStorage username and query progress

```python
@router.get("/{challenge_name}/progress")
async def get_user_progress(
    challenge_name: str,
    username: Optional[str] = None,  # Allow anonymous lookup
    current_user: User = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    effective_username = current_user.username if current_user else username
    if not effective_username:
        return {"unlocked_levels": [1]}
    # ... lookup by username
```

---

---

## Part 4: Styling & Theming (The Fun Stuff You Want to Keep)

Each challenge has unique, themed styling that gives it personality. **Any standardization should preserve these themes.**

### Level Tab Themes

| Challenge | Theme | Icons | Colors | Special Elements |
|-----------|-------|-------|--------|------------------|
| **Giga Chad** | Terminal/Hacker | 🐣💪⚡🔥 (progression) | Blue (`#60a5fa`, `#3b82f6`) | ASCII art header, terminal window bar with red/yellow/green dots, `BABY CHAD → CHAD → MEGA CHAD → GIGA CHAD` |
| **Glitch** | Cyberpunk | ⚡🔷🔶 | Cyan (`#00f5ff`), Purple (`#a855f7`), Pink (`#ec4899`) | Compact horizontal tabs, neon glow effects, `--glitch-cyan` theme |
| **Interrogation** | Detective Noir | ⭐☆☆ star ratings | Amber/Gold (`#FFB74D`), Dark grays | Case names like "The Last Transmission", evidence bar, film noir vibe |
| **Firewall** | Hacker/Matrix | ⭐☆☆ star ratings | Green (`#00ff41` terminal green) | "Security Clearance Level" header, matrix-style terminal |
| **Arena** | Gladiator/Battle | ⚔️🛡️ | Red/Orange combat colors | HP bars, damage display, battle stats |
| **Debate** | Courthouse | ⚖️ | Purple/Blue judicial | "Case 1", "Case 2" naming |

### Custom Victory Modals

| Challenge | Modal Style | Special Features |
|-----------|-------------|------------------|
| **Giga Chad** | Terminal modal with ASCII "YOU WON!" art | `[ ATTACK RESULT ]` header, stat boxes styled like terminal output, `TOTAL DMG`, `ROUNDS`, `SCORE` |
| **Glitch** | Cyberpunk with glitch animation | `⚡ GLITCH DETECTED ⚡` animated text, cyan glow, "Bot Compromised!" |
| **Interrogation** | Detective noir with amber border | `✅ CASE SOLVED!` header, key evidence list, score display with amber theme |
| **Firewall** | Uses shared modal BUT with terminal CSS overrides | Green glow, monospace font, `--firewall-green` styling applied to `#completionModal` |
| **Debate/Arena** | Uses shared modal with theme colors passed as params | `primary_color` macro parameter customizes border/accent |

### Preserving Themes in Standardization

**Option A: Keep Custom Modals (Current)**
- ✅ Full creative control per challenge
- ❌ Logic scattered, breaks easily

**Option B: Theme Variables for Shared Modal**
```html
{{ completion_modal(
    challenge_name='giga_chad',
    primary_color='#60a5fa',
    success_title='CHAD BROKEN!',
    success_icon='💪',
    theme_class='terminal-theme',
    custom_ascii='<pre>YOU WON ASCII ART</pre>'
) }}
```
- ✅ Consistent logic
- ✅ Still customizable per challenge
- ❌ Limited to what macro supports

**Option C: Slot-Based Composition**
```html
{% call completion_modal_wrapper() %}
    <!-- Custom content goes here -->
    <div class="giga-chad-victory-art">...</div>
{% endcall %}
```
- ✅ Full styling freedom
- ✅ Shared button/logic handling
- ⚠️ More complex implementation

### What You'd Lose vs Keep

| If Standardized | Keep | Lose |
|-----------------|------|------|
| **Giga Chad** | Colors, terminal styling | ASCII art in modal (unless slot-based) |
| **Glitch** | Cyan theme, glow effects | "GLITCH DETECTED" animation |
| **Interrogation** | Amber/noir theme | Evidence list in modal, custom layout |
| **Firewall** | Already uses shared modal | Nothing (just CSS overrides) |
| **Debate/Arena** | Already use shared modal | Nothing |

### CSS Variables Already Defined

```css
/* Glitch */
--glitch-cyan: #00f5ff;
--glitch-purple: #a855f7;
--glitch-pink: #ec4899;

/* Interrogation */  
--detective-amber: #FFB74D;
--detective-dark: #1a1a1a;
--detective-gray: #2a2a2a;

/* Firewall */
--firewall-green: #00ff41;
--terminal-dark: #0a0a0a;

/* Giga Chad uses inline blue theme */
/* Arena uses inline red/orange theme */
```

### Recommendation for Styling

**Don't standardize the HTML/visual design** - keep each challenge's unique look.

**DO standardize the JavaScript logic** - extract level unlock + next button logic into a shared function that each custom modal calls:

```javascript
// Shared utility (in challenge-handler.js)
ChallengeHandler.handleLevelCompletion = async function(handler, result, maxLevel) {
    const nextLevel = handler.currentLevel + 1;
    if (result.success && nextLevel <= maxLevel) {
        handler.unlockedLevels.push(nextLevel);
        await this.syncWithServer(handler.challengeName);
    }
    return {
        unlocked_next_level: handler.unlockedLevels.includes(nextLevel),
        next_level: nextLevel
    };
};

// Then each custom modal just calls this and wires up its own button
```

This way:
- **Keep:** All your fun themed modals and styling
- **Fix:** The next level button logic works consistently

---

## Files Reference

### Core Infrastructure
- `app/static/js/core/challenge-handler.js` - Base class with level utilities
- `app/templates/challenges/_completion_modal.html` - Shared modal
- `app/templates/challenges/_level_tabs.html` - Shared tabs
- `app/routes/leaderboard.py` - Progress endpoint

### Per-Challenge (Modal/Levels)
- `app/templates/challenges/glitch.html` - Custom modal
- `app/templates/challenges/interrogation.html` - Custom modal
- `app/templates/challenges/giga_chad.html` - Custom modal + overrides
- `app/templates/challenges/firewall.html` - Uses shared modal
- `app/templates/challenges/debate.html` - Uses shared modal
- `app/templates/challenges/arena.html` - Uses shared modal

### Handlers
- `app/static/js/handlers/glitch.js`
- `app/static/js/handlers/interrogation.js`
- `app/static/js/handlers/giga_chad.js`
- `app/static/js/handlers/firewall.js`
- `app/static/js/handlers/debate.js`
- `app/static/js/handlers/arena.js`
