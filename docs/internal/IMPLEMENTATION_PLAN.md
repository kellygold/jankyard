# Level System & Leaderboard Fix - Implementation Plan

**Date:** January 2026  
**Base Repo:** `/Users/teebox-admin/Code/jankyard` (clean, no uncommitted changes)  
**Do NOT use:** `/Users/teebox-admin/Code/jankyard2/jankyard` (has unrelated backend refactoring)

---

## Why jankyard (not jankyard2)

| Criteria | jankyard | jankyard2/jankyard |
|----------|----------|-------------------|
| Git status | ✅ Clean | ❌ 4 uncommitted files |
| Uncommitted changes | None | `arena.py`, `glitch.py`, `interrogation.py`, `generic_stream.py` |
| Nature of changes | N/A | Backend `StepResult` refactoring (unrelated to modal/level issues) |
| Extra docs | Has `CHALLENGE_STATUS.md`, `CLEANUP_RECOMMENDATIONS.md` | Missing these |

**Decision:** Use `jankyard`. The jankyard2 changes can be cherry-picked later if needed.

---

## Overview

### Goals
1. **Fix Next Level button** - works consistently across all challenges
2. **Fix progress persistence** - survives page reload for all users
3. **Fix anonymous user progress** - non-logged-in users who enter username can track progress
4. **Keep all custom styling** - no visual changes

### Non-Goals
- Not changing any HTML/CSS
- Not replacing custom modals with shared modal
- Not touching backend challenge logic

---

## Phase 1: Add Shared Level Completion Utility

### File: `app/static/js/core/challenge-handler.js`

**Location:** After `static async init(config)` method (around line 557)

**Add this new static method:**

```javascript
    /**
     * Handle level completion - unlocks next level and syncs with server
     * Call this from handleComplete() or custom modal logic
     * 
     * @param {Object} config - Configuration object
     * @param {ChallengeHandler} config.handler - The challenge handler instance
     * @param {Object} config.result - The completion result from backend
     * @param {number} config.maxLevel - Maximum level for this challenge
     * @param {string} config.challengeName - Name of the challenge
     * @returns {Promise<Object>} - {unlockedLevels, nextLevel, hasNextLevel, shouldShowNextButton}
     * 
     * @example
     * const levelInfo = await ChallengeHandler.handleLevelCompletion({
     *     handler: this,
     *     result: result,
     *     maxLevel: 4,
     *     challengeName: 'giga_chad'
     * });
     * if (levelInfo.shouldShowNextButton) {
     *     nextLevelBtn.style.display = 'block';
     * }
     */
    static async handleLevelCompletion(config) {
        const { handler, result, maxLevel, challengeName } = config;
        
        const currentLevel = handler.currentLevel || 1;
        const nextLevel = currentLevel + 1;
        const hasNextLevel = nextLevel <= maxLevel;
        
        // Initialize unlockedLevels if not present
        if (!handler.unlockedLevels) {
            handler.unlockedLevels = [1];
        }
        
        // Step 1: Optimistically unlock next level locally if success
        let locallyUnlocked = false;
        if (result.success && hasNextLevel && !handler.unlockedLevels.includes(nextLevel)) {
            handler.unlockedLevels.push(nextLevel);
            locallyUnlocked = true;
            console.log(`🔓 Locally unlocked level ${nextLevel}`);
        }
        
        // Step 2: Update UI immediately
        ChallengeHandler.updateLevelTabs(handler.unlockedLevels, maxLevel);
        
        // Step 3: Sync with server (async, don't block)
        try {
            const serverLevels = await ChallengeHandler.checkUnlockedLevels(challengeName);
            
            // Merge local and server (keep any locally unlocked that server hasn't saved yet)
            const mergedLevels = [...new Set([...handler.unlockedLevels, ...serverLevels])];
            handler.unlockedLevels = mergedLevels;
            
            // Update UI with merged state
            ChallengeHandler.updateLevelTabs(mergedLevels, maxLevel);
            console.log(`📊 Synced levels: [${mergedLevels.join(', ')}]`);
        } catch (error) {
            console.warn('⚠️ Server sync failed, using local state:', error);
        }
        
        // Step 4: Determine if next button should show
        const shouldShowNextButton = result.success && hasNextLevel && handler.unlockedLevels.includes(nextLevel);
        
        return {
            unlockedLevels: handler.unlockedLevels,
            currentLevel,
            nextLevel,
            hasNextLevel,
            shouldShowNextButton,
            locallyUnlocked
        };
    }
    
    /**
     * Wire up a next level button with standard behavior
     * 
     * @param {HTMLElement|string} button - Button element or ID
     * @param {number} nextLevel - Level number to switch to
     * @param {Function} closeModalFn - Function to close the modal
     * @param {Function} selectLevelFn - Function to select a level (receives level number)
     */
    static wireNextLevelButton(button, nextLevel, closeModalFn, selectLevelFn) {
        const btn = typeof button === 'string' ? document.getElementById(button) : button;
        if (!btn) return;
        
        btn.style.display = 'block';
        btn.onclick = () => {
            if (closeModalFn) closeModalFn();
            if (selectLevelFn) selectLevelFn(nextLevel);
        };
    }
```

**Exact insertion point in file:**

```
Line 557: }  // end of static async init(config)
Line 558: 
Line 559: [INSERT NEW METHODS HERE]
Line 560:
Line 561: }  // end of class ChallengeHandler
```

---

## Phase 2: Fix Each Challenge's Modal Integration

### 2.1 Glitch Challenge

**File:** `app/static/js/handlers/glitch.js`

**Current code (lines 265-284):**
```javascript
    handleLevelComplete(eventData) {
        const data = eventData.data || eventData;
        const result = data.result || data;
        
        // Check if next level unlocked
        const nextLevel = this.currentLevel + 1;
        if (result.success && nextLevel <= 3 && !this.unlockedLevels.includes(nextLevel)) {
            this.unlockedLevels.push(nextLevel);
        }
        
        // Update unlocked levels UI
        this.initializeUnlockedLevels();
        
        // Show success modal with stats after delay
        if (result.success) {
            setTimeout(() => {
                this.showSuccessModal(result);
            }, 2000);
        }
    }
```

**Replace with:**
```javascript
    async handleLevelComplete(eventData) {
        const data = eventData.data || eventData;
        const result = data.result || data;
        
        // Use shared level completion utility
        const levelInfo = await ChallengeHandler.handleLevelCompletion({
            handler: this,
            result: result,
            maxLevel: 3,
            challengeName: 'glitch'
        });
        
        // Update our local UI method too
        this.initializeUnlockedLevels();
        
        // Show success modal with stats after delay
        if (result.success) {
            setTimeout(() => {
                this.showSuccessModal(result, levelInfo);
            }, 2000);
        }
    }
```

**Current showSuccessModal (lines 287-326):**
```javascript
    showSuccessModal(result) {
        const modal = document.getElementById('successModal');
        const successMessage = document.getElementById('successMessage');
        const successAttempts = document.getElementById('successAttempts');
        const successScore = document.getElementById('successScore');
        const nextLevelBtn = document.getElementById('nextLevelBtn');
        
        if (successMessage) {
            successMessage.textContent = `You broke the bot in ${this.attemptCount} attempts!`;
        }
        
        if (successAttempts) {
            successAttempts.textContent = `${this.attemptCount} / 10`;
        }
        
        if (successScore) {
            successScore.textContent = `${result.score} pts`;
        }
        
        // Show next level button if next level exists and is unlocked
        const nextLevel = this.currentLevel + 1;
        if (nextLevelBtn && nextLevel <= 3) {
            if (this.unlockedLevels.includes(nextLevel) || result.success) {
                nextLevelBtn.style.display = 'block';
                nextLevelBtn.onclick = () => {
                    document.getElementById('successModal').style.display = 'none';
                    this.selectLevel(nextLevel);
                };
            } else {
                nextLevelBtn.style.display = 'none';
            }
        }
        
        if (modal) {
            modal.style.display = 'flex';
        }
    }
```

**Replace with:**
```javascript
    showSuccessModal(result, levelInfo) {
        const modal = document.getElementById('successModal');
        const successMessage = document.getElementById('successMessage');
        const successAttempts = document.getElementById('successAttempts');
        const successScore = document.getElementById('successScore');
        const nextLevelBtn = document.getElementById('nextLevelBtn');
        
        if (successMessage) {
            successMessage.textContent = `You broke the bot in ${this.attemptCount} attempts!`;
        }
        
        if (successAttempts) {
            successAttempts.textContent = `${this.attemptCount} / 10`;
        }
        
        if (successScore) {
            successScore.textContent = `${result.score} pts`;
        }
        
        // Use shared utility for next level button
        if (nextLevelBtn) {
            if (levelInfo && levelInfo.shouldShowNextButton) {
                ChallengeHandler.wireNextLevelButton(
                    nextLevelBtn,
                    levelInfo.nextLevel,
                    () => { document.getElementById('successModal').style.display = 'none'; },
                    (level) => { this.selectLevel(level); }
                );
            } else {
                nextLevelBtn.style.display = 'none';
            }
        }
        
        if (modal) {
            modal.style.display = 'flex';
        }
    }
```

---

### 2.2 Interrogation Challenge

**File:** `app/static/js/handlers/interrogation.js`

**Current code (lines 789-830):**
```javascript
    showSuccessModal(data) {
        if (!this.elements.successModal) return;
        
        // ... populate message, evidence, score ...
        
        // Setup Next Level button
        const nextLevelBtn = document.getElementById('nextLevelBtn');
        if (nextLevelBtn) {
            const nextLevel = this.currentLevel + 1;
            const hasNextLevel = this.unlockedLevels.includes(nextLevel) || nextLevel <= 3;
            
            if (hasNextLevel && nextLevel <= 3) {
                nextLevelBtn.style.display = 'block';
                nextLevelBtn.onclick = () => {
                    document.getElementById('successModal').style.display = 'none';
                    this.switchLevel(nextLevel);
                };
            } else {
                nextLevelBtn.style.display = 'none';
            }
        }
        
        this.elements.successModal.style.display = 'flex';
    }
```

**Step 1: Add handleLevelCompletion call in handleVerdict (around line 576-582):**

Find this code:
```javascript
        if (correct) {
            // Success!
            this.addSystemMessage(`✅ ${data.verdict || 'CASE SOLVED!'}`);
            // Show success modal after delay so user can read verdict
            setTimeout(() => {
                this.showSuccessModal(data);
            }, 2000);
        }
```

**Replace with:**
```javascript
        if (correct) {
            // Success!
            this.addSystemMessage(`✅ ${data.verdict || 'CASE SOLVED!'}`);
            
            // Use shared level completion utility
            const levelInfo = await ChallengeHandler.handleLevelCompletion({
                handler: this,
                result: { success: true, ...data },
                maxLevel: 3,
                challengeName: 'interrogation'
            });
            
            // Show success modal after delay so user can read verdict
            setTimeout(() => {
                this.showSuccessModal(data, levelInfo);
            }, 2000);
        }
```

**Also make handleVerdict async:**
```javascript
    async handleVerdict(eventData) {  // ADD async
```

**Step 2: Update showSuccessModal signature and next button logic:**

```javascript
    showSuccessModal(data, levelInfo) {  // ADD levelInfo parameter
        if (!this.elements.successModal) return;
        
        // Populate success message
        const successMessage = document.getElementById('successMessage');
        if (successMessage) {
            successMessage.textContent = data.verdict || 'You correctly identified the culprit!';
        }
        
        // Populate key evidence
        const keyEvidence = document.getElementById('keyEvidence');
        if (keyEvidence && data.key_evidence && data.key_evidence.length > 0) {
            keyEvidence.innerHTML = '<h3>🔍 Key Evidence:</h3><ul>' +
                data.key_evidence.map(ev => `<li>${ev}</li>`).join('') +
                '</ul>';
        }
        
        // Populate score
        const scoreDisplay = document.getElementById('scoreDisplay');
        if (scoreDisplay && data.score) {
            scoreDisplay.innerHTML = `<h3>🏆 Score: ${data.score} points</h3>`;
        }
        
        // Use shared utility for next level button
        const nextLevelBtn = document.getElementById('nextLevelBtn');
        if (nextLevelBtn) {
            if (levelInfo && levelInfo.shouldShowNextButton) {
                ChallengeHandler.wireNextLevelButton(
                    nextLevelBtn,
                    levelInfo.nextLevel,
                    () => { document.getElementById('successModal').style.display = 'none'; },
                    (level) => { this.switchLevel(level); }
                );
            } else {
                nextLevelBtn.style.display = 'none';
            }
        }
        
        this.elements.successModal.style.display = 'flex';
    }
```

---

### 2.3 Giga Chad Challenge

**File:** `app/templates/challenges/giga_chad.html`

This challenge already has good patterns but has duplicate logic. We'll simplify.

**Current code (lines 1052-1067):**
```javascript
    // Wrap handleComplete to unlock next level BEFORE modal shows
    const originalHandleComplete = chadHandler.handleComplete.bind(chadHandler);
    chadHandler.handleComplete = function(data) {
        const result = data.result || data;
        const success = result.success || this.totalPoints >= 20;
        const nextLevel = this.currentLevel + 1;
        
        // If success and next level exists, unlock it immediately (BEFORE modal shows)
        if (success && nextLevel <= 4 && !this.unlockedLevels.includes(nextLevel)) {
            this.unlockedLevels.push(nextLevel);
            ChallengeHandler.updateLevelTabs(this.unlockedLevels, 4);
        }
        
        // Call the original handler (which shows the modal)
        originalHandleComplete(data);
    };
```

**Replace with:**
```javascript
    // Wrap handleComplete to use shared level completion utility
    const originalHandleComplete = chadHandler.handleComplete.bind(chadHandler);
    chadHandler.handleComplete = async function(data) {
        const result = data.result || data;
        const success = result.success || this.totalPoints >= 20;
        
        // Use shared level completion utility
        const levelInfo = await ChallengeHandler.handleLevelCompletion({
            handler: this,
            result: { success, ...result },
            maxLevel: 4,
            challengeName: 'giga_chad'
        });
        
        // Store for modal to use
        this._levelInfo = levelInfo;
        
        // Call the original handler (which shows the modal)
        originalHandleComplete(data);
    };
```

**Current showCompletionModal override (lines 1121-1158):**

Find and update the next level button section:
```javascript
    // Setup next level button - find current level from active tab and click next tab
    const nextLevelBtn = document.getElementById('nextLevelBtn');
    if (nextLevelBtn) {
        const activeTab = document.querySelector('.level-tab.active');
        const currentLevel = activeTab ? parseInt(activeTab.dataset.level) : 1;
        const nextLevel = currentLevel + 1;
        const nextTab = document.querySelector(`.level-tab[data-level="${nextLevel}"]`);
        
        if (nextLevel <= 4 && nextTab && result.unlocked_next_level) {
            // ... unlock logic ...
        }
    }
```

**Replace with:**
```javascript
    // Use handler's levelInfo from handleComplete
    const nextLevelBtn = document.getElementById('nextLevelBtn');
    const handler = window.gigaChadHandler;
    const levelInfo = handler?._levelInfo;
    
    if (nextLevelBtn && levelInfo) {
        if (levelInfo.shouldShowNextButton) {
            const nextTab = document.querySelector(`.level-tab[data-level="${levelInfo.nextLevel}"]`);
            
            // Update next tab UI
            if (nextTab) {
                nextTab.disabled = false;
                const lockOverlay = nextTab.querySelector('.level-lock-overlay');
                if (lockOverlay) lockOverlay.style.display = 'none';
                const status = nextTab.querySelector('.level-status');
                if (status) status.textContent = '🔓 Unlocked';
            }
            
            ChallengeHandler.wireNextLevelButton(
                nextLevelBtn,
                levelInfo.nextLevel,
                closeCompletionModal,
                (level) => { nextTab?.click(); }
            );
        } else {
            nextLevelBtn.style.display = 'none';
        }
    }
```

**Also remove duplicate server sync (lines 1094-1100)** since `handleLevelCompletion` already does this:
```javascript
            // After completion, re-check unlocked levels from server
            const serverUnlockedLevels = await ChallengeHandler.checkUnlockedLevels('giga_chad');
            // ... merge logic ...
```
**Delete these lines** - the shared utility handles it now.

---

### 2.4 Firewall Challenge

**File:** `app/static/js/handlers/firewall.js`

**Current handleComplete (lines 254-293):**
```javascript
    handleComplete(eventData) {
        console.log('✅ handleComplete:', eventData);
        const data = eventData.data || eventData;
        const result = data.result;
        const summary = data.summary || {};
        
        // Check if next level should be unlocked
        const nextLevel = this.currentLevel + 1;
        if (result.success && nextLevel <= 3 && !this.unlockedLevels.includes(nextLevel)) {
            console.log(`🔓 Unlocking level ${nextLevel}!`);
            this.unlockedLevels.push(nextLevel);
            this.initializeUnlockedLevels();
        }
        
        this.scrollToBottom();
        
        // Show appropriate modal after delay
        setTimeout(() => {
            if (result.success) {
                if (typeof showCompletionModal === 'function') {
                    showCompletionModal({
                        ...result,
                        ...summary,
                        message: result.message || 'You bypassed all filters!',
                        unlocked_next_level: this.unlockedLevels.includes(nextLevel),
                        next_level: nextLevel
                    });
                }
            } else {
                // ... defeat modal ...
            }
        }, 2000);
    }
```

**Replace with:**
```javascript
    async handleComplete(eventData) {
        const data = eventData.data || eventData;
        const result = data.result;
        const summary = data.summary || {};
        
        // Use shared level completion utility
        const levelInfo = await ChallengeHandler.handleLevelCompletion({
            handler: this,
            result: result,
            maxLevel: 3,
            challengeName: 'firewall'
        });
        
        // Update our local UI method too
        this.initializeUnlockedLevels();
        
        this.scrollToBottom();
        
        // Show appropriate modal after delay
        setTimeout(() => {
            if (result.success) {
                if (typeof showCompletionModal === 'function') {
                    showCompletionModal({
                        ...result,
                        ...summary,
                        message: result.message || 'You bypassed all filters!',
                        unlocked_next_level: levelInfo.shouldShowNextButton,
                        next_level: levelInfo.nextLevel
                    });
                }
            } else {
                if (typeof showDefeatModal === 'function') {
                    showDefeatModal({
                        ...result,
                        ...summary,
                        message: result.message || 'Firewall blocked your attempt!'
                    });
                }
            }
        }, 2000);
    }
```

---

### 2.5 Debate Challenge

**File:** `app/static/js/handlers/debate.js`

**Current handleComplete (lines 166-210):**
```javascript
    handleComplete(eventData) {
        const data = eventData.data || eventData;
        const result = data.result;
        
        this.scrollToBottom();
        
        const currentLevel = this.currentLevel || 1;
        const nextLevel = currentLevel + 1;
        const hasNextLevel = nextLevel <= 2;
        
        setTimeout(() => {
            if (result.success) {
                if (typeof showCompletionModal === 'function') {
                    showCompletionModal({
                        ...result,
                        unlocked_next_level: hasNextLevel,
                        next_level: hasNextLevel ? nextLevel : null,
                        // ...
                    });
                }
            }
        }, 2000);
    }
```

**Replace with:**
```javascript
    async handleComplete(eventData) {
        const data = eventData.data || eventData;
        const result = data.result;
        
        this.scrollToBottom();
        
        // Use shared level completion utility
        const levelInfo = await ChallengeHandler.handleLevelCompletion({
            handler: this,
            result: result,
            maxLevel: 2,
            challengeName: 'debate_battle'
        });
        
        setTimeout(() => {
            if (result.success) {
                if (typeof showCompletionModal === 'function') {
                    showCompletionModal({
                        ...result,
                        message: result.message || 'Your arguments were more persuasive!',
                        stat1Label: 'YOUR SCORE',
                        stat1Value: result.score || '-',
                        stat2Label: 'CASE',
                        stat2Value: `${levelInfo.currentLevel}/2`,
                        stat3Label: 'TOTAL',
                        stat3Value: result.total_score || result.score || '-',
                        unlocked_next_level: levelInfo.shouldShowNextButton,
                        next_level: levelInfo.nextLevel,
                        next_level_text: '💼 Next Case'
                    });
                }
            } else {
                if (typeof showDefeatModal === 'function') {
                    showDefeatModal({
                        ...result,
                        message: result.message || 'Your opponent was more persuasive. Try again!',
                        stat1Label: 'YOUR SCORE',
                        stat1Value: result.score || '-',
                        stat2Label: 'CASE',
                        stat2Value: `${levelInfo.currentLevel}/2`
                    });
                }
            }
        }, 2000);
    }
```

**Also add unlockedLevels tracking in constructor or where handler is created.** In `debate.html` template, after handler creation:
```javascript
debateHandler.unlockedLevels = [...unlockedLevels];
debateHandler.currentLevel = currentLevel;
```

---

### 2.6 Arena Challenge

**File:** `app/templates/challenges/arena.html`

Similar pattern to Giga Chad - has wrapper that needs updating.

**Current code (lines 787-803):**
```javascript
    const originalHandleComplete = arenaHandler.handleComplete.bind(arenaHandler);
    arenaHandler.handleComplete = function(data) {
        const eventData = data.data || data;
        const result = eventData.result || data.result || {};
        const nextLevel = currentLevel + 1;
        
        if (result.success && nextLevel <= 2 && !unlockedLevels.includes(nextLevel)) {
            unlockedLevels.push(nextLevel);
            initLevelTabs();
        }
        
        originalHandleComplete(data);
    };
```

**Replace with:**
```javascript
    const originalHandleComplete = arenaHandler.handleComplete.bind(arenaHandler);
    arenaHandler.handleComplete = async function(data) {
        const eventData = data.data || data;
        const result = eventData.result || data.result || {};
        
        // Use shared level completion utility
        const levelInfo = await ChallengeHandler.handleLevelCompletion({
            handler: this,
            result: result,
            maxLevel: 2,
            challengeName: 'arena'
        });
        
        // Sync outer scope variable (for tab click handlers)
        unlockedLevels = levelInfo.unlockedLevels;
        initLevelTabs();
        
        // Store for modal to use
        this._levelInfo = levelInfo;
        
        originalHandleComplete(data);
    };
```

---

## Phase 3: Fix Anonymous User Progress Tracking

### 3.1 Backend: Make Progress Endpoint Support Anonymous Users

**File:** `app/routes/leaderboard.py`

**Current code (lines 83-88):**
```python
@router.get("/{challenge_name}/progress", response_class=JSONResponse)
async def get_user_progress(
    challenge_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
```

**Replace with:**
```python
@router.get("/{challenge_name}/progress", response_class=JSONResponse)
async def get_user_progress(
    challenge_name: str,
    username: Optional[str] = None,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db)
):
    """Get user's progress for a challenge (unlocked levels)
    
    Works for both authenticated users and anonymous users who provide username.
    """
    # Determine effective username
    if current_user:
        effective_username = current_user.username
    elif username:
        effective_username = username
    else:
        return {"unlocked_levels": [1]}
    
    leaderboard_service = LeaderboardService(db)
```

**Also add import at top of file:**
```python
from app.routes.deps import get_current_user_optional  # ADD THIS
```

**Then update all the username checks** from:
```python
if any(entry.username == current_user.username for entry in ...):
```

**To:**
```python
if any(entry.username == effective_username for entry in ...):
```

This affects lines: 102, 106, 110, 124, 132, 147, 151, 167, 168, 185

---

### 3.2 Frontend: Store and Send Username for Anonymous Users

**File:** `app/static/js/core/challenge-handler.js`

**Update checkUnlockedLevels method (lines 424-447):**

```javascript
    static async checkUnlockedLevels(challengeName) {
        try {
            const token = localStorage.getItem('access_token');
            const storedUsername = localStorage.getItem('jankyard_username');
            
            // Build URL with optional username param for anonymous users
            let url = `/leaderboard/${challengeName}/progress`;
            if (!token && storedUsername) {
                url += `?username=${encodeURIComponent(storedUsername)}`;
            }
            
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            
            const progressResponse = await fetch(url, { headers });
            
            if (progressResponse.ok) {
                const progressData = await progressResponse.json();
                return progressData.unlocked_levels || [1];
            }
            
            return [1];
        } catch (error) {
            console.error(`Failed to check unlocked levels for ${challengeName}:`, error);
            return [1];
        }
    }
```

---

### 3.3 Ensure Username is Stored on Submission

Each challenge template already has this pattern (good):
```javascript
if (username.value) {
    localStorage.setItem('jankyard_username', username.value);
}
```

**Verify this exists in:** 
- `firewall.html` ✅ (line 770-772)
- `arena.html` ✅ (line 827-830)
- `giga_chad.html` - **NEEDS ADDING** before stream call

**Add to giga_chad.html before the stream call (around line 1091):**
```javascript
        // Save username for anonymous progress tracking
        const usernameField = document.getElementById('username');
        if (usernameField && usernameField.value) {
            localStorage.setItem('jankyard_username', usernameField.value);
        }
```

---

## Phase 4: Testing Checklist

### Per-Challenge Test (Run for Each)

| Step | Expected Result |
|------|-----------------|
| 1. Clear localStorage, logout | Start fresh |
| 2. Load challenge page | Only level 1 unlocked |
| 3. Enter username in form | Username saved to localStorage |
| 4. Complete level 1 successfully | Next Level button appears in modal |
| 5. Click Next Level | Modal closes, level 2 tab becomes active |
| 6. Click level 1 tab | Can switch back to level 1 |
| 7. Refresh page | Level 2 still unlocked (persisted) |
| 8. Check console | No errors, see sync logs |

### Logged-In User Test

| Step | Expected Result |
|------|-----------------|
| 1. Login with test account | Token in localStorage |
| 2. Complete level 1 | Progress saved to DB |
| 3. Logout, login again | Progress still there |
| 4. Different browser/incognito | Progress loads from server |

### Anonymous User Test

| Step | Expected Result |
|------|-----------------|
| 1. Not logged in | No token |
| 2. Enter username "TestAnon123" | Stored in localStorage |
| 3. Complete level 1 | Score saved under "TestAnon123" |
| 4. Refresh page | Level 2 still unlocked |
| 5. Check leaderboard page | "TestAnon123" appears |

---

## Execution Order

1. **Phase 1** - Add shared utility (low risk, additive)
2. **Phase 3.1** - Fix backend endpoint (enables anonymous progress)  
3. **Phase 3.2** - Update frontend checkUnlockedLevels
4. **Phase 2.1** - Fix Glitch (simplest custom modal)
5. **Phase 2.4** - Fix Firewall (uses shared modal, simpler)
6. **Phase 2.5** - Fix Debate (uses shared modal)
7. **Phase 2.6** - Fix Arena (template wrapper pattern)
8. **Phase 2.2** - Fix Interrogation (complex custom modal)
9. **Phase 2.3** - Fix Giga Chad (most complex)
10. **Phase 3.3** - Add username storage to giga_chad
11. **Testing** - Run full checklist

---

## Rollback Plan

If issues arise:
1. Git stash all changes: `git stash`
2. Test original: `git status` should be clean
3. Investigate specific file: `git diff stash app/path/to/file.js`
4. Selectively apply: `git stash pop` then revert specific files

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `app/static/js/core/challenge-handler.js` | +2 static methods (~70 lines) |
| `app/static/js/handlers/glitch.js` | Update 2 methods |
| `app/static/js/handlers/interrogation.js` | Update 2 methods, add async |
| `app/static/js/handlers/firewall.js` | Update 1 method |
| `app/static/js/handlers/debate.js` | Update 1 method |
| `app/templates/challenges/giga_chad.html` | Update wrapper + modal function |
| `app/templates/challenges/arena.html` | Update wrapper |
| `app/routes/leaderboard.py` | Update 1 endpoint signature + username refs |
