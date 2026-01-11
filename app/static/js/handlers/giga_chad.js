/**
 * Giga Chad Handler
 * 
 * Handles prompt injection attack challenge
 * Extends ChallengeHandler base class
 */

class GigaChadHandler extends ChallengeHandler {
    constructor(resultsContainer) {
        super('giga_chad', resultsContainer);
        
        console.log('💪 GigaChadHandler constructed');
        
        this.currentRound = 0;
        this.maxRounds = 5;
        this.totalPoints = 0;
        this.attackResults = [];
        this.currentLevel = 1;  // Track current level for next_level calculation
        
        // Get existing UI elements from template
        this.messagesDiv = document.getElementById('chatMessages');
        this.roundNumEl = document.getElementById('roundNum');
        this.totalPointsEl = document.getElementById('totalPoints');
        this.statusText = document.getElementById('statusText');
        
        // Register event handlers
        this.on('start', (data) => this.handleStart(data));
        this.on('update', (data) => this.handleUpdate(data));
        this.on('thinking', (data) => this.handleThinking(data));
        this.on('attack', (data) => this.handleAttack(data));
        this.on('response', (data) => this.handleResponse(data));
        this.on('judgment', (data) => this.handleJudgment(data));
        this.on('summary', (data) => this.handleSummary(data));
        this.on('round_complete', (data) => this.handleRoundComplete(data));
        this.on('complete', (data) => this.handleComplete(data));
    }
    
    start() {
        console.log('🚀 GigaChadHandler.start() called - using existing chat UI');
        // Chat UI already exists in template, no need to recreate
    }
    
    handleStart(data) {
        console.log('🎬 Chad battle started:', data);
        this.currentRound = 0;
        this.totalPoints = 0;
        this.updateRoundIndicator();
    }
    
    handleUpdate(data) {
        console.log('🔄 Update:', data);
        // Update events from base class streaming - not used in multi-agent
    }
    
    handleThinking(data) {
        if (this.messagesDiv) {
            this.messagesDiv.insertAdjacentHTML('beforeend', `
                <div class="thinking-indicator">
                    <span class="typing-dots">
                        <span></span><span></span><span></span>
                    </span>
                    <span>${data.message || 'Processing...'}</span>
                </div>
            `);
            this.scrollToBottom();
        }
    }
    
    handleAttack(eventData) {
        this.removeThinkingIndicator();
        
        // Get round number from backend metadata
        const metadata = eventData.metadata || {};
        const roundNum = metadata.round || this.currentRound;
        
        // Only update if backend provides round number
        if (metadata.round) {
            this.currentRound = metadata.round;
            this.updateRoundIndicator();
        }
        
        if (this.messagesDiv) {
            // Extract message from nested data structure
            const attackText = eventData.data?.message || eventData.message || eventData.text || 'Attack sent';
            this.messagesDiv.insertAdjacentHTML('beforeend', `
                <div class="attack-message">
                    <div class="message-header">
                        <strong>⚔️ Round ${roundNum} Attack</strong>
                    </div>
                    <div class="message-content">${this.escapeHtml(attackText)}</div>
                </div>
            `);
            this.scrollToBottom();
        }
    }
    
    handleResponse(eventData) {
        this.removeThinkingIndicator();
        
        console.log('💬 Response data:', eventData);
        
        if (this.messagesDiv) {
            // Extract message from nested data structure
            const responseText = eventData.data?.message || eventData.message || eventData.text || 'Chad responded';
            this.messagesDiv.insertAdjacentHTML('beforeend', `
                <div class="chad-response">
                    <div class="message-header">
                        <strong>💪 Chad Response</strong>
                    </div>
                    <div class="message-content">${this.escapeHtml(responseText)}</div>
                </div>
            `);
            this.scrollToBottom();
        }
        
        // Check if response includes judgment data in metadata
        const metadata = eventData.metadata || {};
        if (metadata.points !== undefined) {
            this.totalPoints += metadata.points;
            this.updateScoreDisplay();
            
            // Show judgment inline
            const severity = metadata.severity || 'none';
            const broke = metadata.broke || false;
            
            let severityIcon = '✨';
            let severityText = 'Resisted';
            let severityClass = 'resisted';
            
            if (severity === 'complete') {
                severityIcon = '💀';
                severityText = 'COMPLETE BREAK';
                severityClass = 'complete-break';
            } else if (severity === 'partial') {
                severityIcon = '⚠️';
                severityText = 'Partial Break';
                severityClass = 'partial';
            } else if (severity === 'wobble') {
                severityIcon = '🎯';
                severityText = 'Wobble';
                severityClass = 'wobble';
            }
            
            if (this.messagesDiv) {
                this.messagesDiv.insertAdjacentHTML('beforeend', `
                    <div class="judgment-result ${severityClass}">
                        <div class="message-header">
                            <strong>⚖️ Judge Ruling</strong>
                        </div>
                        <div class="judgment-content">
                            <div class="severity">${severityIcon} ${severityText}</div>
                            <div class="points">+${metadata.points} points</div>
                            ${metadata.creativity ? `<div class="creativity">Creativity: ${metadata.creativity}/10</div>` : ''}
                        </div>
                    </div>
                `);
                this.scrollToBottom();
            }
        }
    }
    
    handleJudgment(eventData) {
        this.removeThinkingIndicator();
        
        const message = eventData.data?.message || eventData.message || '';
        const metadata = eventData.metadata || {};
        const severity = metadata.severity || 'none';
        const points = metadata.points || 0;
        const broke = metadata.broke || false;
        
        this.totalPoints += points;
        this.updateScoreDisplay();
        
        let severityIcon = '✨';
        let severityText = 'Resisted';
        let severityClass = 'resisted';
        
        if (severity === 'complete') {
            severityIcon = '💀';
            severityText = 'COMPLETE BREAK';
            severityClass = 'complete-break';
        } else if (severity === 'partial') {
            severityIcon = '⚠️';
            severityText = 'Partial Break';
            severityClass = 'partial';
        } else if (severity === 'wobble') {
            severityIcon = '🎯';
            severityText = 'Wobble';
            severityClass = 'wobble';
        }
        
        if (this.messagesDiv) {
            this.messagesDiv.insertAdjacentHTML('beforeend', `
                <div class="judgment-result ${severityClass}">
                    <div class="judgment-header">
                        <strong>⚖️ Judge Ruling</strong>
                    </div>
                    <div class="judgment-content">
                        <div class="severity">${severityIcon} ${severityText}</div>
                        <div class="points">+${points} points</div>
                        <div class="reasoning">${this.escapeHtml(message)}</div>
                        ${metadata.creativity ? `<div class="creativity">Creativity: ${metadata.creativity}/10</div>` : ''}
                    </div>
                </div>
            `);
            this.scrollToBottom();
        }
    }
    
    handleSummary(eventData) {
        console.log('📊 Summary:', eventData);
        
        const message = eventData.data?.message || eventData.message || '';
        if (this.messagesDiv && message) {
            this.messagesDiv.insertAdjacentHTML('beforeend', `
                <div class="summary-message">
                    <div class="message-header">
                        <strong>📊 Final Summary</strong>
                    </div>
                    <div class="message-content">${this.escapeHtml(message).replace(/\n/g, '<br>')}</div>
                </div>
            `);
            this.scrollToBottom();
        }
    }
    
    handleRoundComplete(data) {
        console.log('✅ Round complete:', data);
    }
    
    handleComplete(data) {
        console.log('🏁 Challenge complete:', data);
        
        const result = data.result || data;
        const success = result.success || this.totalPoints >= 20; // At least one complete break
        
        // Old inline banner removed - now using modal
        this.scrollToBottom();
        
        // Determine next level availability
        const currentLevel = this.currentLevel || 1;
        const nextLevel = currentLevel + 1;
        const hasNextLevel = nextLevel <= 4;  // Giga Chad has 4 levels
        
        // Show appropriate modal after delay so user can read the final result
        setTimeout(() => {
            if (success) {
                if (typeof showCompletionModal === 'function') {
                    showCompletionModal({
                        ...result,
                        message: result.message || 'You broke Giga Chad!',
                        total_points: this.totalPoints,
                        rounds: this.currentRound,
                        stat1Label: 'BREAK POINTS',
                        stat1Value: this.totalPoints,
                        stat2Label: 'LEVEL',
                        stat2Value: `${currentLevel}/4`,
                        stat3Label: 'ROUNDS',
                        stat3Value: this.currentRound,
                        unlocked_next_level: hasNextLevel,
                        next_level: hasNextLevel ? nextLevel : null,
                        next_level_text: '💪 Next Chad'
                    });
                }
            } else {
                if (typeof showDefeatModal === 'function') {
                    showDefeatModal({
                        ...result,
                        message: result.message || 'Chad held strong. Try a different approach!',
                        total_points: this.totalPoints,
                        rounds: this.currentRound
                    });
                }
            }
        }, 2000); // 2 second delay to read result
    }
    
    // Helper methods
    updateRoundIndicator() {
        if (this.roundNumEl) {
            this.roundNumEl.textContent = this.currentRound;
        }
    }
    
    updateScoreDisplay() {
        if (this.totalPointsEl) {
            this.totalPointsEl.textContent = this.totalPoints;
        }
    }
    
    removeThinkingIndicator() {
        const thinking = this.messagesDiv?.querySelector('.thinking-indicator:last-child');
        if (thinking) thinking.remove();
    }
    
    scrollToBottom() {
        if (this.messagesDiv) {
            this.messagesDiv.scrollTop = this.messagesDiv.scrollHeight;
        }
    }
}

// Expose globally
window.GigaChadHandler = GigaChadHandler;
