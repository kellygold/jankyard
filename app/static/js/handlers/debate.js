/**
 * Debate Challenge Handler
 * 
 * Handles debate battles with judge rulings
 * Extends ChallengeHandler base class
 */

class DebateHandler extends ChallengeHandler {
    constructor(resultsContainer) {
        super('debate_battle', resultsContainer);
        
        this.currentRound = 0;
        this.currentLevel = 1;  // Track current case/level
        
        // Register event handlers
        this.on('start', (data) => this.handleStart(data));
        this.on('update', (data) => this.handleUpdate(data));
        this.on('thinking', (data) => this.handleThinking(data));
        this.on('message', (data) => this.handleMessage(data));
        this.on('judgment', (data) => this.handleJudgment(data));
        this.on('summary', (data) => this.handleSummary(data));
        this.on('complete', (data) => this.handleComplete(data));
    }
    
    handleStart(data) {
        // Chat interface is already in HTML, just get reference to messages div
        this.messagesDiv = this.resultsDiv;
        this.headerDiv = null; // No header needed in chat interface
        this.showResults();
    }
    
    handleUpdate(data) {
        // Extract from nested structure
        const eventData = data.data || data;
        const round = eventData.metadata?.round || this.currentRound;
        const maxRounds = eventData.metadata?.max_rounds || 3;
        
        this.currentRound = round;
        
        // Update round indicator if it exists
        this.updateRoundIndicator(round);
    }
    
    handleThinking(data) {
        // Extract from nested structure
        const eventData = data.data || data;
        const agent = data.agent || 'system';
        const role = eventData.metadata?.role || '';
        let thinkingText = '';
        
        if (agent === 'user') {
            thinkingText = '👤 Your AI is thinking<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        } else if (agent === 'chad' || agent === 'house') {
            thinkingText = '🤖 Chad is thinking<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        } else if (agent === 'judge') {
            thinkingText = '⚖️ Judge is deliberating<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        }
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="thinking-indicator">${thinkingText}</div>
        `);
        this.scrollToBottom();
    }
    
    handleMessage(data) {
        // Extract from nested structure (new format) or fall back to old format
        const eventData = data.data || data;
        const agent = data.agent || 'system';
        const message = eventData.message || data.message || data.text || '';
        const metadata = eventData.metadata || {};
        const round = metadata.round || data.round || this.currentRound;
        
        // Remove thinking indicator
        this.removeLastThinking();
        
        // Check if this is a forfeit message
        if (metadata.forfeit) {
            this.messagesDiv.insertAdjacentHTML('beforeend', `
                <div class="system-message forfeit">
                    <strong>⚠️ FORFEIT:</strong> ${this.escapeHtml(message)}
                </div>
            `);
            this.scrollToBottom();
            return;
        }
        
        // Render normal message
        const speakerLabel = agent === 'user' ? `USER (PRO) - Round ${round}` : `CHAD (CON) - Round ${round}`;
        const messageClass = agent === 'user' ? 'user' : 'house';
        const avatar = agent === 'user' ? '👤' : '🤖';
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="message ${messageClass}">
                <div class="avatar">${avatar}</div>
                <div class="message-content">
                    <span class="speaker-name">${speakerLabel}</span>
                    <div class="message-text">${this.escapeHtml(message)}</div>
                </div>
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleJudgment(data) {
        // Extract from nested structure
        // Note: metadata is at TOP LEVEL (data.metadata), not nested in data.data
        const eventData = data.data || data;
        const metadata = data.metadata || {};  // Fixed: read from top level
        const message = eventData.message || data.message || '';
        
        const winner = metadata.winner || '';
        const scores = metadata.scores || {pro: 0, con: 0};
        const reasoning = message;
        
        // Remove all thinking indicators
        const thinkingIndicators = this.messagesDiv.querySelectorAll('.thinking-indicator');
        thinkingIndicators.forEach(el => el.remove());
        
        // Add judgment card
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="judgment-card">
                <h3>⚖️ Judge's Decision</h3>
                <div class="winner">
                    <strong>Winner:</strong> ${winner === 'USER' ? '👤 YOU!' : '🤖 Chad'}
                </div>
                <div class="scores">
                    <div class="score-item">
                        <span>👤 PRO (You):</span>
                        <span class="score-value">${scores.pro}/100</span>
                    </div>
                    <div class="score-item">
                        <span>🤖 CON (Chad):</span>
                        <span class="score-value">${scores.con}/100</span>
                    </div>
                </div>
                <div class="reasoning">
                    <div class="reasoning-content" style="white-space: pre-wrap;">${this.escapeHtml(reasoning)}</div>
                </div>
                <!-- Score shown in complete event -->
            </div>
        `);
        
        this.scrollToBottom();
    }
    
    handleSummary(data) {
        // Extract from nested structure
        const eventData = data.data || data;
        const message = eventData.message || data.message || '';
        const metadata = eventData.metadata || {};
        
        // Remove thinking indicator
        this.removeLastThinking();
        
        // Show summary message
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="system-message summary">
                <strong>📋 Summary:</strong>
                <pre>${this.escapeHtml(message)}</pre>
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleComplete(eventData) {
        // Extract from nested structure
        const data = eventData.data || eventData;
        const result = data.result;
        
        // Old inline completion banner removed - now using modal
        this.scrollToBottom();
        
        // Determine next level
        const currentLevel = this.currentLevel || 1;
        const nextLevel = currentLevel + 1;
        const hasNextLevel = nextLevel <= 3;  // Debate has 3 cases (normal/hard/expert)
        
        // Show appropriate modal based on success after delay so user can read the final judgment
        setTimeout(() => {
            if (result.success) {
                if (typeof showCompletionModal === 'function') {
                    showCompletionModal({
                        ...result,
                        message: result.message || 'Your arguments were more persuasive!',
                        stat1Label: 'YOUR SCORE',
                        stat1Value: result.score || '-',
                        stat2Label: 'CASE',
                        stat2Value: `${currentLevel}/3`,
                        stat3Label: 'TOTAL',
                        stat3Value: result.total_score || result.score || '-',
                        unlocked_next_level: hasNextLevel,
                        next_level: hasNextLevel ? nextLevel : null,
                        next_level_text: '💼 Next Case'  // Custom button text
                    });
                }
            } else {
                if (typeof showDefeatModal === 'function') {
                    showDefeatModal({
                        ...result,
                        message: result.message || 'Your opponent was more persuasive. Study their arguments and try again!',
                        stat1Label: 'YOUR SCORE',
                        stat1Value: result.score || '-',
                        stat2Label: 'CASE',
                        stat2Value: `${currentLevel}/3`
                    });
                }
            }
        }, 2000); // 2 second delay to read result
    }
    
    // Helper methods
    
    updateRoundIndicator(round) {
        if (this.headerDiv) {
            const indicator = this.headerDiv.querySelector('.round-indicator');
            if (indicator) {
                indicator.textContent = `Round ${round} of 3`;
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
window.DebateHandler = DebateHandler;
