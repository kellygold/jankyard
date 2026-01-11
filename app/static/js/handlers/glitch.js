/**
 * Glitch Challenge Handler (Refactored)
 * 
 * Extends the base ChallengeHandler - much simpler!
 * Only contains Glitch-specific UI logic.
 */
class GlitchHandler extends ChallengeHandler {
    constructor(resultsContainer, unlockedLevels = [1]) {
        super('glitch', resultsContainer);
        
        // Challenge state
        this.currentLevel = 1;
        this.attemptCount = 0;
        this.unlockedLevels = unlockedLevels;
        this.levelComplete = false;
        
        // UI elements
        this.chatMessages = this.resultsDiv;
        this.userInput = document.getElementById('userInput');
        this.sendBtn = document.getElementById('sendBtn');
        this.resetBtn = document.getElementById('resetBtn');
        
        // Register Glitch-specific event handlers (standardized events)
        this.on('start', (data) => this.handleStart(data));
        this.on('level_info', (data) => this.handleLevelInfo(data));
        this.on('thinking', (data) => this.showBotThinking(data));
        this.on('bot_response', (data) => this.showBotResponse(data));
        this.on('glitch_detected', (data) => this.handleSuccess(data));
        this.on('continue', (data) => this.handleContinue(data));
        this.on('complete', (data) => this.handleLevelComplete(data));
        
        // Setup UI
        this.setupEventListeners();
        this.initializeUnlockedLevels();
    }
    
    setupEventListeners() {
        // Send attack
        this.sendBtn?.addEventListener('click', () => this.sendAttack());
        this.userInput?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendAttack();
            }
        });
        
        // Reset
        this.resetBtn?.addEventListener('click', () => this.resetLevel());
        
        // Level selection
        document.querySelectorAll('.level-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const level = parseInt(tab.dataset.level);
                if (!tab.disabled) {
                    this.selectLevel(level);
                }
            });
        });
    }
    
    initializeUnlockedLevels() {
        for (let level = 1; level <= 3; level++) {
            const tab = document.querySelector(`.level-tab[data-level="${level}"]`);
            if (tab) {
                tab.disabled = !this.unlockedLevels.includes(level);
                const status = tab.querySelector('.level-status');
                if (status) {
                    if (this.unlockedLevels.includes(level)) {
                        status.textContent = level === 1 ? '🎯 Active' : '🔓 Unlocked';
                    } else {
                        status.textContent = '🔒 Locked';
                    }
                }
            }
        }
    }
    
    selectLevel(level) {
        if (!this.unlockedLevels.includes(level)) return;
        
        this.currentLevel = level;
        this.attemptCount = 0;
        this.levelComplete = false;
        
        // Update UI
        document.querySelectorAll('.level-tab').forEach(tab => {
            tab.classList.toggle('active', parseInt(tab.dataset.level) === level);
        });
        
        // Update bot info card
        this.updateBotInfo(level);
        this.clearResults();
    }
    
    updateBotInfo(level) {
        const botConfigs = {
            1: {
                name: 'HelpBot v1.0',
                description: 'University help desk assistant',
                defenses: ['❌ No memory', '❌ No meta-awareness', '❌ No self-correction', '✅ Simple fact-based prompts'],
                hint: 'Try getting it to contradict its core facts or reveal its AI nature.'
            },
            2: {
                name: 'ModBot v2.0',
                description: 'Content moderation assistant',
                defenses: ['✅ Basic memory', '✅ Pattern detection', '❌ No adaptive learning', '⚠️  Some meta-awareness'],
                hint: 'More sophisticated - look for edge cases in its moderation rules.'
            },
            3: {
                name: 'SecureBot v3.0',
                description: 'High-security screening system',
                defenses: ['✅ Full memory', '✅ Self-correction', '✅ Meta-awareness', '✅ Adaptive defense'],
                hint: 'Advanced AI - creative social engineering or novel attack vectors may be needed.'
            }
        };
        
        const config = botConfigs[level];
        document.getElementById('botName').textContent = config.name;
        document.getElementById('botDescription').textContent = config.description;
        
        const defenseList = document.getElementById('defenseList');
        if (defenseList) {
            defenseList.innerHTML = config.defenses.map(d => `<li>${d}</li>`).join('');
        }
        
        const hint = document.getElementById('botHint');
        if (hint) {
            hint.innerHTML = `<strong>💡 Tip:</strong> ${config.hint}`;
        }
    }
    
    async sendAttack() {
        const userMessage = this.userInput?.value.trim();
        if (!userMessage || this.isStreaming) return;
        
        this.attemptCount++;
        
        // Disable input
        this.disableButton(this.sendBtn, '⏳ Attacking...');
        if (this.userInput) this.userInput.disabled = true;
        
        // Clear input
        if (this.userInput) this.userInput.value = '';
        
        // Show user message immediately
        this.showUserMessage({ message: userMessage });
        
        try {
            // Use base class stream method!
            await this.stream(userMessage, `level_${this.currentLevel}`);
        } finally {
            // Re-enable input
            this.enableButton(this.sendBtn);
            if (this.userInput) this.userInput.disabled = false;
            if (this.userInput) this.userInput.focus();
        }
    }
    
    resetLevel() {
        this.attemptCount = 0;
        this.levelComplete = false;
        this.clearResults();
        this.updateStatus('Ready', 'blue');
    }
    
    // Event Handlers - Just the unique Glitch UI logic
    
    handleStart(data) {
        // Challenge started
    }
    
    handleLevelInfo(eventData) {
        // Extract level info from nested data structure
        const level = eventData.data?.level || eventData.level;
        // Update UI with level info if needed
    }
    
    handleContinue(eventData) {
        // Extract data from nested structure
        const data = eventData.data || eventData;
        const attemptsRemaining = data.attempts_remaining || 0;
        this.updateStatus(`${attemptsRemaining} attempts remaining`, 'yellow');
    }
    
    showUserMessage(data) {
        const message = data.message || data.text;
        this.chatMessages.insertAdjacentHTML('beforeend', `
            <div class="message user">
                <div class="avatar">👤</div>
                <div class="message-content">
                    <span class="speaker-name">You</span>
                    <div class="message-text">${this.escapeHtml(message)}</div>
                </div>
            </div>
        `);
        this.scrollToBottom();
    }
    
    showBotThinking(data) {
        this.chatMessages.insertAdjacentHTML('beforeend', `
            <div class="thinking-indicator">
                🧠 <em>Bot is processing...</em>
            </div>
        `);
        this.scrollToBottom();
    }
    
    showBotResponse(eventData) {
        // Remove thinking indicator
        const thinking = this.chatMessages.querySelector('.thinking-indicator');
        if (thinking) thinking.remove();
        
        // Extract data from nested structure
        const data = eventData.data || eventData;
        const response = data.response || data.message;
        
        this.chatMessages.insertAdjacentHTML('beforeend', `
            <div class="message bot">
                <div class="avatar">🤖</div>
                <div class="message-content">
                    <span class="speaker-name">Bot</span>
                    <div class="message-text">${this.escapeHtml(response)}</div>
                </div>
            </div>
        `);
        this.scrollToBottom();
        
        // Update attempt counter
        if (data.attempts_remaining !== undefined) {
            this.updateStatus(`${data.attempts_remaining} attempts remaining`, 'yellow');
        }
    }
    
    handleSuccess(eventData) {
        // Extract data from nested structure
        const data = eventData.data || eventData;
        
        this.levelComplete = true;
        this.chatMessages.insertAdjacentHTML('beforeend', `
            <div class="success-message" style="background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.3); padding: 1.5rem; border-radius: 8px; margin: 1rem 0; text-align: center;">
                <div style="font-size: 2rem; margin-bottom: 0.5rem;">⚡️</div>
                <h3 style="margin: 0 0 0.5rem 0;">GLITCH DETECTED!</h3>
                <p style="margin: 0; opacity: 0.9;">You broke the bot's defenses in ${data.attempts_used || this.attemptCount} attempts!</p>
            </div>
        `);
        this.updateStatus('Compromised', 'green');
        this.scrollToBottom();
    }
    
    handleFailure(data) {
        this.chatMessages.insertAdjacentHTML('beforeend', `
            <div class="failure-message" style="background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <strong>❌ Attack Failed</strong>
                <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">${data.message || 'The bot held strong against your attack.'}</p>
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleProgress(data) {
        const attemptsLeft = data.max_attempts - data.attempts;
        this.updateStatus(`${attemptsLeft} attempts left`, 'yellow');
    }
    
    handleLevelComplete(eventData) {
        // Level complete - show full results
        const data = eventData.data || eventData;
        const result = data.result || data;
        
        // Check if next level unlocked
        const nextLevel = this.currentLevel + 1;
        if (result.success && nextLevel <= 3 && !this.unlockedLevels.includes(nextLevel)) {
            this.unlockedLevels.push(nextLevel);
        }
        
        // Update unlocked levels UI
        this.initializeUnlockedLevels();
        
        // Show success modal with stats after delay so user can read result
        if (result.success) {
            setTimeout(() => {
                this.showSuccessModal(result);
            }, 2000);
        }
    }
    
    showSuccessModal(result) {
        // Populate modal with results
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
                // Set up click handler to switch to next level
                nextLevelBtn.onclick = () => {
                    document.getElementById('successModal').style.display = 'none';
                    this.selectLevel(nextLevel);
                };
            } else {
                nextLevelBtn.style.display = 'none';
            }
        }
        
        // Show the modal
        if (modal) {
            modal.style.display = 'flex';
        }
    }
    
    
    updateStatus(text, color = 'blue') {
        const statusText = document.getElementById('statusText');
        const statusDot = document.getElementById('statusDot');
        
        if (statusText) statusText.textContent = text;
        if (statusDot) {
            const colors = {
                blue: '#3b82f6',
                green: '#22c55e',
                yellow: '#eab308',
                red: '#ef4444'
            };
            statusDot.style.background = colors[color] || colors.blue;
        }
    }
}

// Export to global scope
window.GlitchHandler = GlitchHandler;
