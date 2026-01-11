/**
 * Honeypot Challenge Handler
 * 
 * Handles the deception-based security challenge where the AI
 * pretends to be vulnerable and players must reverse-engineer
 * its detection taxonomy.
 */
class HoneypotHandler extends ChallengeHandler {
    constructor(config = {}) {
        super('honeypot', document.getElementById('chatMessages'));
        
        // Challenge config
        this.currentLevel = config.currentLevel || 1;
        this.maxLevels = config.maxLevels || 3;
        this.levelMapping = config.levelMapping || {
            1: 'TRIPWIRE',
            2: 'CANARY',
            3: 'COUNTERINTEL'
        };
        
        // Game state
        this.phase = 'bait';
        this.attemptCount = 0;
        this.maxAttempts = 10;
        this.categoriesFound = [];
        this.categoriesNeeded = 3;
        this.attackLog = [];
        this.unlockedLevels = [1];
        
        // UI elements
        this.chatMessages = document.getElementById('chatMessages');
        this.userInput = document.getElementById('userInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.resetBtn = document.getElementById('resetBtn');
        this.attackLogEl = document.getElementById('attackLog');
        this.categoriesPanel = document.getElementById('categoriesPanel');
        this.categoriesList = document.getElementById('categoriesList');
        this.phaseDisplay = document.getElementById('phaseDisplay');
        
        // Register event handlers
        this.on('thinking', (data) => this.showThinking(data));
        this.on('response', (data) => this.showResponse(data));
        this.on('log_update', (data) => this.updateAttackLog(data));
        this.on('phase_change', (data) => this.handlePhaseChange(data));
        this.on('reveal', (data) => this.handleReveal(data));
        this.on('complete', (data) => this.handleComplete(data));
        this.on('continue', (data) => this.handleContinue(data));
        
        // Setup
        this.setupEventListeners();
        this.loadProgress();
    }
    
    setupEventListeners() {
        // Send button
        this.sendBtn?.addEventListener('click', () => this.sendProbe());
        
        // Enter to send
        this.userInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendProbe();
            }
        });
        
        // Reset button
        this.resetBtn?.addEventListener('click', () => this.resetLevel());
        
        // Level tabs
        document.querySelectorAll('.level-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const level = parseInt(tab.dataset.level);
                if (!tab.disabled && this.unlockedLevels.includes(level)) {
                    this.selectLevel(level);
                }
            });
        });
    }
    
    async loadProgress() {
        try {
            const username = document.getElementById('username')?.value || '';
            const url = `/leaderboard/honeypot/progress${username ? `?username=${encodeURIComponent(username)}` : ''}`;
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                this.unlockedLevels = data.unlocked_levels || [1];
                this.updateLevelTabs();
            }
        } catch (e) {
            console.log('Could not load progress:', e);
        }
    }
    
    updateLevelTabs() {
        for (let level = 1; level <= this.maxLevels; level++) {
            const tab = document.querySelector(`.level-tab[data-level="${level}"]`);
            if (tab) {
                const isUnlocked = this.unlockedLevels.includes(level);
                tab.disabled = !isUnlocked;
                
                const status = tab.querySelector('.level-status');
                if (status) {
                    if (level === this.currentLevel) {
                        status.textContent = '🎯';
                    } else if (isUnlocked) {
                        status.textContent = '✅';
                    } else {
                        status.textContent = '🔒';
                    }
                }
            }
        }
    }
    
    selectLevel(level) {
        if (!this.unlockedLevels.includes(level)) return;
        
        this.currentLevel = level;
        this.resetState();
        
        // Update UI
        document.querySelectorAll('.level-tab').forEach(tab => {
            tab.classList.toggle('active', parseInt(tab.dataset.level) === level);
        });
        
        // Update level-specific config
        const configs = {
            1: { maxAttempts: 10, categoriesNeeded: 3 },
            2: { maxAttempts: 8, categoriesNeeded: 4 },
            3: { maxAttempts: 5, categoriesNeeded: 6 }
        };
        
        const config = configs[level] || configs[1];
        this.maxAttempts = config.maxAttempts;
        this.categoriesNeeded = config.categoriesNeeded;
        
        this.updateUI();
        this.updateLevelTabs();
    }
    
    resetState() {
        this.phase = 'bait';
        this.attemptCount = 0;
        this.categoriesFound = [];
        this.attackLog = [];
    }
    
    resetLevel() {
        this.resetState();
        this.clearResults();
        this.updateUI();
        this.updateAttackLogUI();
        
        // Show welcome message again
        const welcome = document.getElementById('welcomeMessage');
        if (welcome) welcome.style.display = 'block';
    }
    
    updateUI() {
        // Update attempt counter
        const counter = document.getElementById('attemptCounter');
        if (counter) {
            counter.textContent = `${this.attemptCount}/${this.maxAttempts}`;
        }
        
        // Update phase display
        if (this.phaseDisplay) {
            this.phaseDisplay.textContent = this.phase.toUpperCase();
            this.phaseDisplay.className = `stat-value phase-${this.phase}`;
        }
        
        // Update categories panel
        if (this.categoriesPanel) {
            this.categoriesPanel.style.display = this.phase === 'hunt' ? 'block' : 'none';
        }
        
        const categoriesCount = document.getElementById('categoriesCount');
        if (categoriesCount) {
            categoriesCount.textContent = `${this.categoriesFound.length}/${this.categoriesNeeded}`;
        }
        
        // Update categories list
        if (this.categoriesList) {
            this.categoriesList.innerHTML = this.categoriesFound
                .map(cat => `<span class="category-tag">${cat}</span>`)
                .join('');
        }
    }
    
    async sendProbe() {
        const userMessage = this.userInput?.value.trim();
        if (!userMessage || this.isStreaming) return;
        
        // Hide welcome message
        const welcome = document.getElementById('welcomeMessage');
        if (welcome) welcome.style.display = 'none';
        
        // Disable input
        this.disableButton(this.sendBtn, '⏳ Probing...');
        if (this.userInput) this.userInput.disabled = true;
        
        // Clear input
        if (this.userInput) this.userInput.value = '';
        
        // Show user message
        this.showUserMessage(userMessage);
        
        try {
            const difficulty = this.levelMapping[this.currentLevel];
            await this.stream(userMessage, difficulty);
        } catch (e) {
            console.error('Probe error:', e);
            this.showError('Failed to send probe. Please try again.');
        } finally {
            this.enableButton(this.sendBtn, '🍯 PROBE');
            if (this.userInput) this.userInput.disabled = false;
            this.userInput?.focus();
        }
    }
    
    showUserMessage(message) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user-message';
        msgDiv.innerHTML = `
            <div class="message-avatar user">👤</div>
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(message)}</div>
                <div class="message-meta">Attempt ${this.attemptCount + 1}</div>
            </div>
        `;
        this.chatMessages?.appendChild(msgDiv);
        this.scrollToBottom();
    }
    
    showThinking(data) {
        // Remove any existing thinking indicator
        const existing = document.querySelector('.thinking-indicator');
        if (existing) existing.remove();
        
        const thinkingDiv = document.createElement('div');
        thinkingDiv.className = 'message thinking-indicator';
        thinkingDiv.innerHTML = `
            <div class="message-avatar honeypot">🍯</div>
            <div class="message-content">
                <div class="message-text typing-animation">
                    <span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>
                </div>
            </div>
        `;
        this.chatMessages?.appendChild(thinkingDiv);
        this.scrollToBottom();
    }
    
    showResponse(data) {
        // Remove thinking indicator
        const thinking = document.querySelector('.thinking-indicator');
        if (thinking) thinking.remove();
        
        this.attemptCount = data.data?.attempt || this.attemptCount + 1;
        
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message honeypot-message';
        
        let metaText = `Attempt ${this.attemptCount}`;
        if (data.data?.category_logged && data.data.category_logged !== '████████') {
            metaText += ` • Logged: ${data.data.category_logged}`;
        }
        
        msgDiv.innerHTML = `
            <div class="message-avatar honeypot">🍯</div>
            <div class="message-content">
                <div class="message-text">${this.escapeHtml(data.data?.text || '')}</div>
                <div class="message-meta">${metaText}</div>
            </div>
        `;
        this.chatMessages?.appendChild(msgDiv);
        this.scrollToBottom();
        this.updateUI();
    }
    
    updateAttackLog(data) {
        if (data.data?.attack_log) {
            this.attackLog = data.data.attack_log;
            this.updateAttackLogUI();
        }
        
        if (data.data?.newly_found && data.data.newly_found.length > 0) {
            data.data.newly_found.forEach(cat => {
                if (!this.categoriesFound.includes(cat)) {
                    this.categoriesFound.push(cat);
                    this.showCategoryFound(cat);
                }
            });
            this.updateUI();
        }
    }
    
    updateAttackLogUI() {
        if (!this.attackLogEl) return;
        
        if (this.attackLog.length === 0) {
            this.attackLogEl.innerHTML = `
                <div class="log-empty">
                    <span class="log-empty-icon">🔍</span>
                    <span class="log-empty-text">No attacks logged yet</span>
                </div>
            `;
            return;
        }
        
        this.attackLogEl.innerHTML = this.attackLog.map(entry => `
            <div class="log-entry">
                <div class="log-entry-header">
                    <span class="log-attempt">#${entry.attempt}</span>
                    <span class="log-confidence">${entry.confidence}</span>
                </div>
                <div class="log-category ${entry.category.includes('█') ? '' : 'revealed'}">
                    ${entry.category}
                </div>
            </div>
        `).join('');
    }
    
    showCategoryFound(category) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message system-message category-found';
        msgDiv.innerHTML = `
            <div class="message-content system">
                <div class="message-text">🏷️ <strong>CATEGORY IDENTIFIED:</strong> ${category}</div>
            </div>
        `;
        this.chatMessages?.appendChild(msgDiv);
        this.scrollToBottom();
    }
    
    handlePhaseChange(data) {
        this.phase = data.data?.new_phase || 'reveal';
        
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message system-message phase-change';
        msgDiv.innerHTML = `
            <div class="message-content system">
                <div class="message-text">⚠️ <strong>PHASE CHANGE:</strong> ${data.data?.message || 'Something has changed...'}</div>
            </div>
        `;
        this.chatMessages?.appendChild(msgDiv);
        this.scrollToBottom();
        this.updateUI();
    }
    
    handleReveal(data) {
        this.phase = 'hunt';
        
        // Show reveal message
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message honeypot-message reveal-message';
        msgDiv.innerHTML = `
            <div class="message-avatar honeypot">🍯</div>
            <div class="message-content reveal">
                <div class="message-text">${this.escapeHtml(data.data?.text || '')}</div>
                <div class="message-meta">The hunt begins...</div>
            </div>
        `;
        this.chatMessages?.appendChild(msgDiv);
        this.scrollToBottom();
        
        // Show categories panel
        if (this.categoriesPanel) {
            this.categoriesPanel.style.display = 'block';
        }
        
        // Update hint
        const hint = document.getElementById('missionHint');
        if (hint) {
            hint.innerHTML = '💡 <strong>Phase 3:</strong> Now identify the threat categories! Type category names like SOCIAL, INJECT, PROBE, etc.';
        }
        
        this.updateUI();
        this.updateAttackLogUI();
    }
    
    handleContinue(data) {
        // Update from continue event
        if (data.data?.phase) {
            this.phase = data.data.phase;
        }
        if (data.data?.categories_found !== undefined) {
            // Categories count from server
        }
        this.updateUI();
    }
    
    handleComplete(data) {
        const result = data.data?.result;
        const isSuccess = result?.success;
        
        if (isSuccess) {
            this.showSuccessModal(data);
        } else {
            this.showFailureModal(data);
        }
    }
    
    showSuccessModal(data) {
        const result = data.data?.result;
        const stats = data.data?.stats || [];
        
        // Update modal content
        document.getElementById('successMessage').textContent = 
            data.data?.message || 'You cracked the detection system!';
        
        // Update stats
        if (stats[0]) document.getElementById('successCategories').textContent = stats[0].value;
        if (stats[1]) document.getElementById('successAttempts').textContent = `${stats[1].value} / ${this.maxAttempts}`;
        if (stats[2]) document.getElementById('successScore').textContent = `${stats[2].value} pts`;
        
        // Show found categories
        const foundDisplay = document.getElementById('foundCategoriesDisplay');
        if (foundDisplay && result?.found_categories) {
            foundDisplay.innerHTML = `
                <div class="found-categories-title">Categories Found:</div>
                <div class="categories-list">
                    ${result.found_categories.map(cat => `<span class="category-tag">${cat}</span>`).join('')}
                </div>
            `;
        }
        
        // Handle next level button
        const nextBtn = document.getElementById('nextLevelBtn');
        if (nextBtn) {
            if (this.currentLevel < this.maxLevels) {
                nextBtn.style.display = 'inline-block';
                nextBtn.onclick = () => {
                    document.getElementById('successModal').style.display = 'none';
                    this.unlockedLevels.push(this.currentLevel + 1);
                    this.selectLevel(this.currentLevel + 1);
                };
            } else {
                nextBtn.style.display = 'none';
            }
        }
        
        document.getElementById('successModal').style.display = 'flex';
    }
    
    showFailureModal(data) {
        const result = data.data?.result;
        const stats = data.data?.stats || [];
        
        document.getElementById('failureMessage').textContent = 
            data.data?.message || 'The honeypot wins this round.';
        
        if (stats[0]) document.getElementById('failureCategories').textContent = stats[0].value;
        if (stats[1]) document.getElementById('failureAttempts').textContent = `${stats[1].value} / ${this.maxAttempts}`;
        
        document.getElementById('failureModal').style.display = 'flex';
    }
    
    showError(message) {
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message error-message';
        msgDiv.innerHTML = `
            <div class="message-content error">
                <div class="message-text">❌ ${message}</div>
            </div>
        `;
        this.chatMessages?.appendChild(msgDiv);
        this.scrollToBottom();
    }
    
    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    disableButton(btn, text) {
        if (btn) {
            btn.disabled = true;
            btn.textContent = text;
        }
    }
    
    enableButton(btn, text) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = text;
        }
    }
}

// Export for use
window.HoneypotHandler = HoneypotHandler;
