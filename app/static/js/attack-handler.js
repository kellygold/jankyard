/**
 * Attack Challenge (Giga Chad) UI Handler
 * 
 * Extends BaseChatHandler with attack-specific functionality (inline scoring).
 */

class AttackHandler extends BaseChatHandler {
    constructor(resultsContainer) {
        super(resultsContainer, 'attack-container');
        this.scoreTotal = 0;
    }
    
    /**
     * Initialize attack UI
     */
    start() {
        // Create attack UI with styled header matching debate
        this.resultsDiv.innerHTML = `
            <div class="attack-container">
                <div class="attack-header" id="attackHeader">
                    <h2>🔥 Let the battle begin!</h2>
                    <div class="score-indicator">Score: 0</div>
                </div>
                <div class="attack-messages" id="attackMessages"></div>
            </div>
        `;
        
        this.messagesDiv = document.getElementById('attackMessages');
        this.headerDiv = document.getElementById('attackHeader');
    }
    
    /**
     * Override thinking labels for attack-specific terminology
     */
    getThinkingLabel(who, round) {
        let emoji = '🤔';
        let label = 'Thinking...';
        
        if (who === 'attacker') {
            emoji = '💭';
            label = `Your AI is crafting attack #${round}...`;
        } else if (who === 'defender' || who === 'chad') {
            emoji = '🛡️';
            label = 'Chad is responding...';
        }
        
        return {emoji, label};
    }
    
    /**
     * Handle 'attack' event
     */
    handleAttack(data) {
        const attack = data.text || data.attack;  // Backend sends 'text'
        const round = data.round || this.currentRound;
        
        // Update round if changed
        if (round !== this.currentRound) {
            this.currentRound = round;
        }
        
        // Remove thinking indicator
        this.removeLastThinkingIndicator();
        
        // Render attack message with round label
        const speakerLabel = `Round ${round} - Your Attack:`;
        this.renderMessage('user', attack, speakerLabel);
    }
    
    /**
     * Handle 'response' event
     */
    handleResponse(data) {
        const response = data.text || data.response;  // Backend sends 'text'
        const round = data.round || this.currentRound;
        
        // Extract scoring info (sent with response)
        const broke = data.broke || false;
        const severity = data.severity || 'resisted';
        const points = data.points || 0;
        const creativity = data.creativity || 0;
        
        // Update total score
        this.scoreTotal += points;
        this.updateScoreIndicator(this.scoreTotal);
        
        // Remove thinking indicator
        this.removeLastThinkingIndicator();
        
        // Determine result display
        const {resultIcon, resultText, resultClass} = this.getResultDisplay(severity, broke);
        
        // Build inline scoring HTML
        const scoringHTML = `
            <div class="attack-result" style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.2); font-size: 0.875rem;">
                ${resultIcon} <strong>${resultText}</strong> - +${points}pts
                ${creativity > 7 ? ` <span style="opacity: 0.8;">🎨 Creative!</span>` : ''}
            </div>
        `;
        
        // Render response message with speaker label and inline scoring
        const speakerLabel = `Chad's Response:`;
        this.renderMessage('house', response, speakerLabel, scoringHTML);
    }
    
    /**
     * Get result display elements based on severity
     */
    getResultDisplay(severity, broke) {
        let resultIcon = '❌';
        let resultText = 'RESISTED';
        let resultClass = 'resisted';
        
        if (severity === 'complete') {
            resultIcon = '💀';
            resultText = 'COMPLETE BREAK!';
            resultClass = 'complete-break';
        } else if (severity === 'partial') {
            resultIcon = '⚠️';
            resultText = 'PARTIAL BREAK';
            resultClass = 'partial-break';
        } else if (severity === 'wobble') {
            resultIcon = '🎯';
            resultText = 'WOBBLE';
            resultClass = 'wobble';
        } else if (broke) {
            resultIcon = '✅';
            resultText = 'BROKE';
            resultClass = 'wobble';
        }
        
        return {resultIcon, resultText, resultClass};
    }
    
    /**
     * Note: handleJudgment removed - scoring is now inline with handleResponse
     */
    
    /**
     * Handle 'complete' event
     */
    handleComplete(data) {
        const result = data.result;
        
        // Update header to show completion
        if (this.headerDiv) {
            const successEmoji = result.success ? '🎉' : '⚔️';
            const statusText = result.success ? 'YOU WIN!' : 'Challenge Complete';
            
            this.headerDiv.innerHTML = `
                <h2>${successEmoji} ${statusText}</h2>
                <div class="score-indicator">Final Score: ${result.score} points</div>
            `;
        }
        
        // Add final summary
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="final-summary ${result.success ? 'success' : ''}">
                <h3>${result.success ? '🏆 Victory!' : '⚔️ Nice Try!'}</h3>
                <p><strong>Final Score:</strong> ${result.score} points</p>
                <p><strong>Rounds Completed:</strong> ${result.steps}</p>
                ${result.success ? '<p class="win-message">You successfully broke Chad\'s role!</p>' : ''}
            </div>
        `);
        
        this.scrollToBottom();
    }
    
    /**
     * Update score indicator in header
     */
    updateScoreIndicator(score) {
        if (this.headerDiv) {
            const indicator = this.headerDiv.querySelector('.score-indicator');
            if (indicator) {
                indicator.textContent = `Score: ${score}`;
            }
        }
    }
}
