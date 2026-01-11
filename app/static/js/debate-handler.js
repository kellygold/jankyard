/**
 * Debate Challenge UI Handler
 * 
 * Extends BaseChatHandler with debate-specific functionality.
 */

class DebateHandler extends BaseChatHandler {
    constructor(resultsContainer) {
        super(resultsContainer, 'debate-container');
    }
    
    /**
     * Initialize debate UI
     */
    start() {
        super.start('🎭', 'Debate Starting...', 'Preparing...');
        // Rename IDs for backward compatibility
        this.headerDiv.id = 'debateHeader';
        this.messagesDiv.id = 'debateMessages';
        this.headerDiv.querySelector('.chat-indicator').className = 'round-indicator';
        this.messagesDiv.className = 'debate-messages';
    }
    
    /**
     * Handle 'message' event (debate argument)
     */
    handleMessage(data) {
        const who = data.who; // 'user' or 'house'
        const text = data.text;
        const round = data.round || this.currentRound;
        
        // Update round if changed
        if (round !== this.currentRound) {
            this.currentRound = round;
            this.updateRoundIndicator(round);
        }
        
        // Remove thinking indicator
        this.removeLastThinkingIndicator();
        
        // Render message with speaker label
        const speakerLabel = who === 'user' ? `USER (PRO) - Round ${round}` : `CHAD - Round ${round}`;
        this.renderMessage(who, text, speakerLabel);
    }
    
    /**
     * Handle 'judgment' event
     */
    handleJudgment(data) {
        const judgment = data.judgment;
        const score = data.score;
        
        // Remove all thinking indicators
        const thinkingIndicators = this.messagesDiv.querySelectorAll('.thinking-indicator');
        thinkingIndicators.forEach(el => el.remove());
        
        // Add judgment card
        const winner = judgment.winner;
        const scores = judgment.scores;
        const reasoning = judgment.reasoning;
        
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
                    <strong>Reasoning:</strong>
                    <p>${this.escapeHtml(reasoning)}</p>
                </div>
                <div class="final-score">
                    <strong>Your Score:</strong> <span class="score-badge">${score} points</span>
                </div>
            </div>
        `);
        
        this.scrollToBottom();
    }
    
    /**
     * Handle 'complete' event
     */
    handleComplete(data) {
        const result = data.result;
        
        // Update header to show completion
        if (this.headerDiv) {
            this.headerDiv.innerHTML = `
                <h2>${result.success ? '🎉 Debate Complete!' : '❌ Debate Ended'}</h2>
                <div class="round-indicator">Final Score: ${result.score} points</div>
            `;
        }
        
        this.scrollToBottom();
    }
    
    /**
     * Update round indicator in header
     */
    updateRoundIndicator(round) {
        this.updateHeaderIndicator(`Round ${round} of 3`);
    }
}
