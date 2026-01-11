/**
 * GlitchHandler - Handles The Glitch prompt injection challenge
 * Multi-level chat-based AI security testing
 */
class GlitchHandler extends BaseChatHandler {
    constructor(unlockedLevels = [1]) {
        super('chatMessages', 'chat-container');
        
        // Challenge state
        this.currentLevel = 1;
        this.attemptCount = 0;
        this.maxAttempts = 10;
        this.levelComplete = false;
        this.unlockedLevels = unlockedLevels; // Passed from template based on user progress
        
        // UI elements
        this.sendBtn = document.getElementById('sendBtn');
        this.userInput = document.getElementById('userInput');
        this.resetBtn = document.getElementById('resetBtn');
        this.chatMessages = document.getElementById('chatMessages');
        this.statusText = document.getElementById('statusText');
        this.statusDot = document.getElementById('statusDot');
        
        // Bind events
        this.setupEventListeners();
        
        // Initialize unlocked levels UI
        this.initializeUnlockedLevels();
    }
    
    initializeUnlockedLevels() {
        // Update UI to show which levels are unlocked
        for (let level = 1; level <= 3; level++) {
            const tab = document.querySelector(`.level-tab[data-level="${level}"]`);
            if (tab) {
                if (this.unlockedLevels.includes(level)) {
                    tab.disabled = false;
                    const status = tab.querySelector('.level-status');
                    if (status) {
                        if (level === 1) {
                            status.textContent = '🎯 Active';
                        } else {
                            status.textContent = '🔓 Unlocked';
                        }
                    }
                } else {
                    tab.disabled = true;
                    const status = tab.querySelector('.level-status');
                    if (status) {
                        status.textContent = '🔒 Locked';
                    }
                }
            }
        }
    }
    
    setupEventListeners() {
        // Send button
        this.sendBtn.addEventListener('click', () => this.sendAttack());
        
        // Enter key in textarea
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendAttack();
            }
        });
        
        // Reset button
        this.resetBtn.addEventListener('click', () => this.resetLevel());
        
        // Level tabs
        document.querySelectorAll('.level-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const level = parseInt(tab.dataset.level);
                if (!tab.disabled) {
                    this.selectLevel(level);
                }
            });
        });
        
        // Next level button in success modal
        const nextLevelBtn = document.getElementById('nextLevelBtn');
        if (nextLevelBtn) {
            nextLevelBtn.addEventListener('click', () => {
                this.closeSuccessModal();
                this.selectLevel(this.currentLevel + 1);
            });
        }
    }
    
    selectLevel(level) {
        if (!this.unlockedLevels.includes(level)) {
            return; // Can't select locked level
        }
        
        this.currentLevel = level;
        
        // Update active tab
        document.querySelectorAll('.level-tab').forEach(tab => {
            tab.classList.remove('active');
            if (parseInt(tab.dataset.level) === level) {
                tab.classList.add('active');
            }
        });
        
        // Reset level state
        this.resetLevel();
        
        // Request level data from server
        this.loadLevelData(level);
    }
    
    async loadLevelData(level) {
        // In a real implementation, this would fetch level config from server
        // For now, we'll use hardcoded data
        const levelConfigs = {
            1: {
                botName: 'HelpBot v1.0',
                description: 'University help desk assistant',
                defenses: [
                    '❌ No memory',
                    '❌ No meta-awareness',
                    '❌ No self-correction',
                    '✅ Simple fact-based prompts'
                ],
                maxAttempts: 10,
                maxScore: 190,
                hint: 'Try getting it to contradict its core facts or reveal its AI nature.'
            },
            2: {
                botName: 'ContentGuard AI',
                description: 'Content moderation system',
                defenses: [
                    '✅ Conversation memory',
                    '✅ Manipulation awareness',
                    '✅ Told to stay firm',
                    '❌ Single defense layer'
                ],
                maxAttempts: 15,
                maxScore: 410,
                hint: 'It remembers your attempts. Use indirect approaches and nested scenarios.'
            },
            3: {
                botName: 'SecureGate v2.1',
                description: 'Advanced security screening AI',
                defenses: [
                    '✅ Full conversation memory',
                    '✅ Multi-layer defense protocols',
                    '✅ Self-checking mechanism',
                    '✅ Active threat detection'
                ],
                maxAttempts: 20,
                maxScore: 680,
                hint: 'Attack the self-checker itself. Create paradoxes and cognitive overload.'
            }
        };
        
        const config = levelConfigs[level];
        if (config) {
            this.updateLevelUI(config);
            this.maxAttempts = config.maxAttempts;
        }
    }
    
    updateLevelUI(config) {
        // Update bot info
        document.getElementById('botName').textContent = config.botName;
        document.getElementById('botDescription').textContent = config.description;
        
        // Update defenses list
        const defenseList = document.getElementById('defenseList');
        defenseList.innerHTML = config.defenses.map(d => `<li>${d}</li>`).join('');
        
        // Update hint
        document.getElementById('botHint').innerHTML = `<strong>💡 Tip:</strong> ${config.hint}`;
        
        // Update stats
        document.getElementById('maxScore').textContent = `${config.maxScore} pts`;
        document.getElementById('attemptCounter').textContent = `0 / ${config.maxAttempts}`;
    }
    
    resetLevel() {
        this.attemptCount = 0;
        this.levelComplete = false;
        
        // Clear chat
        this.chatMessages.innerHTML = `
            <div class="chat-welcome">
                <div class="welcome-icon">🔓</div>
                <h3>Ready to Attack!</h3>
                <p>Send your prompt to manipulate the bot.</p>
            </div>
        `;
        
        // Reset UI
        document.getElementById('attemptCounter').textContent = `0 / ${this.maxAttempts}`;
        document.getElementById('currentScore').textContent = '0 pts';
        this.setStatus('Ready', 'ready');
        this.enableInput();
    }
    
    async sendAttack() {
        const userMessage = this.userInput.value.trim();
        if (!userMessage) return;
        
        if (this.levelComplete) {
            alert('Level complete! Select a new level or reset to try again.');
            return;
        }
        
        // Disable input while processing
        this.disableInput();
        this.setStatus('Processing...', 'processing');
        
        // Clear welcome message if first attempt
        if (this.attemptCount === 0) {
            this.chatMessages.innerHTML = '';
        }
        
        // Add user message
        this.addUserMessage(userMessage);
        
        // Clear input
        this.userInput.value = '';
        
        // Send to server
        try {
            await this.streamAttack(userMessage);
        } catch (error) {
            console.error('Attack failed:', error);
            this.addSystemMessage('❌ Error: ' + error.message);
            this.enableInput();
            this.setStatus('Error', 'error');
        }
    }
    
    async streamAttack(userMessage) {
        const formData = new FormData();
        formData.append('challenge_name', 'glitch');
        formData.append('agent_code', userMessage);
        formData.append('difficulty', `level_${this.currentLevel}`);
        formData.append('agent_type', 'prompt');
        
        // Include username if provided
        const usernameInput = document.getElementById('username');
        if (usernameInput && usernameInput.value) {
            formData.append('username', usernameInput.value);
        }
        
        const response = await fetch('/submit/stream', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const {value, done} = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    this.handleStreamEvent(data);
                }
            }
        }
    }
    
    handleStreamEvent(data) {
        switch (data.type) {
            case 'level_info':
                // Level configuration loaded
                break;
                
            case 'thinking':
                this.addThinkingIndicator(data.who || 'bot');
                break;
                
            case 'bot_response':
                this.handleBotResponse(data);
                break;
                
            case 'glitch_detected':
                this.handleGlitchDetected(data);
                break;
                
            case 'complete':
                this.handleComplete(data);
                break;
                
            case 'continue':
                this.handleContinue(data);
                break;
                
            case 'error':
                this.addSystemMessage('❌ Error: ' + data.message);
                this.enableInput();
                break;
        }
    }
    
    handleBotResponse(data) {
        // Remove thinking indicator
        this.removeLastThinkingIndicator();
        
        // Update attempt counter
        this.attemptCount = data.attempt_count;
        document.getElementById('attemptCounter').textContent = 
            `${data.attempt_count} / ${data.max_attempts}`;
        
        // Add bot message
        this.addBotMessage(data.response);
    }
    
    handleGlitchDetected(data) {
        // Add success system message
        this.addSystemMessage('⚡ GLITCH DETECTED! Bot compromised! ⚡');
        
        // Show success modal
        setTimeout(() => {
            this.showSuccessModal(data);
        }, 1000);
        
        this.levelComplete = true;
        this.setStatus('Level Complete!', 'success');
    }
    
    handleComplete(data) {
        if (data.level_complete) {
            // Level beaten - unlock next if available
            const nextLevel = this.currentLevel + 1;
            if (nextLevel <= 3 && !this.unlockedLevels.includes(nextLevel)) {
                this.unlockLevel(nextLevel);
            }
        } else {
            // Failed - out of attempts
            if (data.reason === 'max_attempts_reached') {
                this.addSystemMessage('❌ Out of attempts! Level failed. Try again with a different strategy.');
                this.levelComplete = true;
                this.setStatus('Failed', 'error');
            }
        }
        
        this.enableInput();
    }
    
    handleContinue(data) {
        // Bot held firm, continue trying
        this.addSystemMessage(`🛡️ ${data.message}`);
        this.enableInput();
        this.setStatus('Ready', 'ready');
    }
    
    unlockLevel(level) {
        if (!this.unlockedLevels.includes(level)) {
            this.unlockedLevels.push(level);
            
            // Update UI
            const tab = document.querySelector(`.level-tab[data-level="${level}"]`);
            if (tab) {
                tab.disabled = false;
                const status = tab.querySelector('.level-status');
                if (status) {
                    status.textContent = '🔓 Unlocked';
                }
            }
        }
    }
    
    showSuccessModal(data) {
        const modal = document.getElementById('successModal');
        const nextLevelBtn = document.getElementById('nextLevelBtn');
        
        // Update modal content
        document.getElementById('successMessage').textContent = 
            `You broke the ${data.level_name} in ${data.attempts_used} attempts!`;
        document.getElementById('successAttempts').textContent = 
            `${data.attempts_used} / ${this.maxAttempts}`;
        document.getElementById('successScore').textContent = 
            `${data.score} pts`;
        
        // Show/hide next level button
        if (data.level_id < 3) {
            nextLevelBtn.style.display = 'block';
        } else {
            nextLevelBtn.style.display = 'none';
        }
        
        // Show modal
        modal.style.display = 'flex';
    }
    
    closeSuccessModal() {
        document.getElementById('successModal').style.display = 'none';
    }
    
    // Message rendering
    addUserMessage(text) {
        const messageHTML = `
            <div class="chat-message user-message">
                <div class="message-header">
                    <span class="message-avatar">👤</span>
                    <span>You</span>
                </div>
                <div class="message-content">${this.escapeHtml(text)}</div>
            </div>
        `;
        this.chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        this.scrollToBottom();
    }
    
    addBotMessage(text) {
        const messageHTML = `
            <div class="chat-message bot-message">
                <div class="message-header">
                    <span class="message-avatar">🤖</span>
                    <span>Bot</span>
                </div>
                <div class="message-content">${this.escapeHtml(text)}</div>
            </div>
        `;
        this.chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        this.scrollToBottom();
    }
    
    addSystemMessage(text) {
        const messageHTML = `
            <div class="chat-message system-message">
                <div class="message-content">${text}</div>
            </div>
        `;
        this.chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        this.scrollToBottom();
    }
    
    addThinkingIndicator(who) {
        const messageHTML = `
            <div class="thinking-indicator">
                <span class="message-avatar">🤖</span>
                <span>Bot is thinking</span>
                <div class="thinking-dots">
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                    <div class="thinking-dot"></div>
                </div>
            </div>
        `;
        this.chatMessages.insertAdjacentHTML('beforeend', messageHTML);
        this.scrollToBottom();
    }
    
    removeLastThinkingIndicator() {
        const thinking = this.chatMessages.querySelector('.thinking-indicator:last-of-type');
        if (thinking) {
            thinking.remove();
        }
    }
    
    // UI state management
    disableInput() {
        this.sendBtn.disabled = true;
        this.userInput.disabled = true;
    }
    
    enableInput() {
        this.sendBtn.disabled = false;
        this.userInput.disabled = false;
        this.userInput.focus();
    }
    
    setStatus(text, state) {
        this.statusText.textContent = text;
        this.statusDot.className = 'status-dot status-' + state;
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
