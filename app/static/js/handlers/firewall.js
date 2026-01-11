/**
 * Firewall Handler
 * 
 * Handles filter bypass challenge with blocked/allowed tracking
 * Extends ChallengeHandler base class
 */

class FirewallHandler extends ChallengeHandler {
    constructor(resultsContainer, unlockedLevels = [1]) {
        super('firewall', resultsContainer);
        
        this.attemptCount = 0;
        this.blockedCount = 0;
        this.flagRevealed = false;
        this.currentLevel = 1;
        this.unlockedLevels = unlockedLevels;
        
        // Register event handlers
        this.on('start', (data) => this.handleStart(data));
        this.on('update', (data) => this.handleUpdate(data));
        this.on('thinking', (data) => this.handleThinking(data));
        this.on('blocked', (data) => this.handleBlocked(data));
        this.on('response', (data) => this.handleResponse(data));
        this.on('complete', (data) => this.handleComplete(data));
        
        // Initialize unlocked levels UI
        this.initializeUnlockedLevels();
    }
    
    initializeUnlockedLevels() {
        for (let level = 1; level <= 3; level++) {
            const tab = document.querySelector(`.level-tab[data-level="${level}"]`);
            if (tab) {
                const isUnlocked = this.unlockedLevels.includes(level);
                tab.disabled = !isUnlocked;
                
                // Show/hide lock overlay
                const lockOverlay = tab.querySelector('.level-lock-overlay');
                if (lockOverlay) {
                    lockOverlay.style.display = isUnlocked ? 'none' : 'block';
                }
                
                // Update status text
                const status = tab.querySelector('.level-status');
                if (status) {
                    if (level === this.currentLevel) {
                        status.textContent = '🎯 Active';
                    } else if (isUnlocked) {
                        status.textContent = '✅ Unlocked';
                    } else {
                        status.textContent = '🔒 Locked';
                    }
                }
                
                // Update active state
                tab.classList.toggle('active', level === this.currentLevel);
                
                // Add click handler (remove old one first to avoid duplicates)
                tab.onclick = null;
                if (isUnlocked) {
                    tab.onclick = () => this.selectLevel(level);
                }
            }
        }
    }
    
    selectLevel(level) {
        if (!this.unlockedLevels.includes(level)) return;
        if (level === this.currentLevel) return;
        
        this.currentLevel = level;
        this.attemptCount = 0;
        this.blockedCount = 0;
        this.flagRevealed = false;
        
        // Update UI
        this.initializeUnlockedLevels();
        
        // Update difficulty selector if it exists
        const difficultySelect = document.getElementById('difficulty');
        if (difficultySelect) {
            const levelMap = { 1: 'LEVEL_1', 2: 'LEVEL_2', 3: 'LEVEL_3' };
            difficultySelect.value = levelMap[level];
        }
        
        // Clear results area
        if (this.resultsDiv) {
            this.resultsDiv.innerHTML = '';
        }
        
        // Hide result section until next attempt
        const resultSection = document.getElementById('resultSection');
        if (resultSection) {
            resultSection.style.display = 'none';
        }
    }
    
    start() {
        // Show the result section container
        const resultSection = document.getElementById('resultSection');
        if (resultSection) {
            resultSection.style.display = 'block';
        }
        
        // Initialize UI
        this.resultsDiv.innerHTML = `
            <div class="firewall-container">
                <div class="firewall-header" id="firewallHeader">
                    <h2>🔥 Firewall Active</h2>
                    <div class="attempt-indicator">Attempt: 0 | Blocked: 0</div>
                </div>
                <div class="firewall-messages" id="firewallMessages"></div>
            </div>
        `;
        
        this.messagesDiv = document.getElementById('firewallMessages');
        this.headerDiv = document.getElementById('firewallHeader');
        this.showResults();
    }
    
    handleStart(data) {
        // Increment attempt count and reset blocked count for new attempt
        this.attemptCount++;
        this.blockedCount = 0;
        
        // Chat interface is already in HTML, just get reference to messages div
        this.messagesDiv = this.resultsDiv;
        this.headerDiv = null; // No header needed in chat interface
        
        this.showResults();
    }
    
    handleThinking(data) {
        if (!this.messagesDiv) {
            return;
        }
        
        // Remove previous thinking indicator before adding new one
        this.removeLastThinking();
        
        // Extract message from nested data structure
        const message = (data.data && data.data.message) || data.message || 'Processing...';
        const agent = data.agent || 'system';
        
        let emoji = '🤔';
        if (agent === 'system') {
            emoji = '🛡️';
        } else if (agent === 'ai') {
            emoji = '🤖';
        }
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="thinking-indicator">${emoji} ${this.escapeHtml(message)}<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span></div>
        `);
        this.scrollToBottom();
    }
    
    handleUpdate(data) {
        // Extract observation from nested data structure
        const observation = data.data?.observation || data.observation;
        
        if (observation) {
            
            // Update attempt counter if present
            if (observation.current_attempt !== undefined) {
                this.attemptCount = observation.current_attempt;
            }
            if (observation.blocked_count !== undefined) {
                this.blockedCount = observation.blocked_count;
            }
            
            this.updateIndicator();
        } else {
            console.warn('⚠️ No observation in update event');
        }
    }
    
    handleBlocked(eventData) {
        console.log('🚫 handleBlocked:', eventData);
        // Extract from nested data structure
        const data = eventData.data || eventData;
        const filter = data.filter || 'Unknown Filter';
        const reason = data.reason || 'Suspicious pattern detected';
        const hint = data.hint || '';
        
        this.blockedCount++;
        this.updateIndicator();
        
        this.removeLastThinking();
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="filter-block">
                <div class="block-icon">🚫</div>
                <div class="block-content">
                    <h4>BLOCKED by ${this.escapeHtml(filter)}</h4>
                    <p>${this.escapeHtml(reason)}</p>
                    ${hint ? `<div class="hint">${this.escapeHtml(hint)}</div>` : ''}
                </div>
            </div>
        `);
        
        this.scrollToBottom();
    }
    
    handleResponse(eventData) {
        console.log('📨 handleResponse:', eventData);
        // Extract from nested data structure
        const data = eventData.data || eventData;
        const text = data.text;
        const flagRevealed = data.flag_revealed || false;
        const flag = data.flag;
        const score = data.score || 0;
        
        this.removeLastThinking();
        
        if (flagRevealed) {
            this.flagRevealed = true;
            
            this.messagesDiv.insertAdjacentHTML('beforeend', `
                <div class="message house success-response">
                    <div class="avatar">🤖</div>
                    <div class="message-content">
                        <span class="speaker-name">AI Assistant</span>
                        <div class="message-text">${this.escapeHtml(text)}</div>
                        <div class="flag-revealed">
                            <div class="flag-icon">🎯</div>
                            <div class="flag-content">
                                <strong>FLAG EXTRACTED!</strong>
                                <code>${this.escapeHtml(flag)}</code>
                                <div class="score-badge">+${score} points</div>
                            </div>
                        </div>
                    </div>
                </div>
            `);
        } else {
            this.messagesDiv.insertAdjacentHTML('beforeend', `
                <div class="message house resist-response">
                    <div class="avatar">🤖</div>
                    <div class="message-content">
                        <span class="speaker-name">AI Assistant</span>
                        <div class="message-text">${this.escapeHtml(text)}</div>
                        <div class="resist-notice">
                            ❌ AI did not reveal the flag
                        </div>
                    </div>
                </div>
            `);
        }
        
        this.scrollToBottom();
    }
    
    handleComplete(eventData) {
        console.log('✅ handleComplete:', eventData);
        // Extract from nested data structure
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
        
        // Show appropriate modal after delay so user can read the result
        setTimeout(() => {
            if (result.success) {
                if (typeof showCompletionModal === 'function') {
                    showCompletionModal({
                        ...result,
                        ...summary,
                        message: result.message || 'You bypassed all filters!',
                        stat1Label: 'SCORE',
                        stat1Value: result.score || summary.score || 0,
                        stat2Label: 'STEPS',
                        stat2Value: this.attemptCount || 1,
                        stat3Label: 'LEVEL',
                        stat3Value: `${this.currentLevel}/3`,
                        unlocked_next_level: this.unlockedLevels.includes(nextLevel),
                        next_level: nextLevel
                    });
                }
            } else {
                if (typeof showDefeatModal === 'function') {
                    showDefeatModal({
                        ...result,
                        ...summary,
                        message: result.message || 'Firewall blocked your attempt!',
                        stat1Label: 'SCORE',
                        stat1Value: '-',
                        stat2Label: 'STEPS',
                        stat2Value: this.attemptCount || 1,
                        stat3Label: 'LEVEL',
                        stat3Value: `${this.currentLevel}/3`
                    });
                }
            }
        }, 2000); // 2 second delay to read result
    }
    
    // Helper methods
    
    updateIndicator() {
        if (this.headerDiv) {
            const indicator = this.headerDiv.querySelector('.attempt-indicator');
            if (indicator) {
                indicator.textContent = `Attempt: ${this.attemptCount} | Blocked: ${this.blockedCount}`;
            }
        }
    }
    
    removeLastThinking() {
        const lastThinking = this.messagesDiv.querySelector('.thinking-indicator:last-child');
        if (lastThinking) lastThinking.remove();
    }
    
    scrollToBottom() {
        if (this.messagesDiv) {
            this.messagesDiv.scrollTop = this.messagesDiv.scrollHeight;
        }
    }
}

// Export to global scope
window.FirewallHandler = FirewallHandler;
