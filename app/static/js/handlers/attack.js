/**
 * Attack Handler (Giga Chad Challenge)
 * 
 * Handles prompt injection attacks with inline scoring
 * Extends ChallengeHandler base class
 */

class AttackHandler extends ChallengeHandler {
    constructor(resultsContainer) {
        super('giga_chad', resultsContainer);
        
        this.scoreTotal = 0;
        this.currentRound = 0;
        
        // Register event handlers
        this.on('start', (data) => this.handleStart(data));
        this.on('thinking', (data) => this.handleThinking(data));
        this.on('attack', (data) => this.handleAttack(data));
        this.on('response', (data) => this.handleResponse(data));
        this.on('complete', (data) => this.handleComplete(data));
    }
    
    start() {
        // Show the result section container
        const resultSection = document.getElementById('resultSection');
        if (resultSection) {
            resultSection.style.display = 'block';
        }
        
        // Initialize UI
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
        this.showResults();
    }
    
    handleStart(data) {
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
        this.showResults();
    }
    
    handleThinking(data) {
        const who = data.who;
        let emoji = '🤔';
        let label = 'Thinking...';
        
        if (who === 'attacker') {
            emoji = '💭';
            label = `Your AI is crafting attack #${data.round || this.currentRound + 1}...`;
        } else if (who === 'defender' || who === 'chad') {
            emoji = '🛡️';
            label = 'Chad is responding...';
        }
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="thinking-indicator">${emoji} ${label}<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span></div>
        `);
        this.scrollToBottom();
    }
    
    handleAttack(data) {
        const attack = data.text || data.attack;
        const round = data.round || this.currentRound;
        
        if (round !== this.currentRound) {
            this.currentRound = round;
        }
        
        this.removeLastThinking();
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="message user">
                <div class="avatar">👤</div>
                <div class="message-content">
                    <span class="speaker-name">Round ${round} - Your Attack:</span>
                    <div class="message-text">${this.escapeHtml(attack)}</div>
                </div>
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleResponse(data) {
        const response = data.text || data.response;
        const round = data.round || this.currentRound;
        
        // Extract scoring info
        const broke = data.broke || false;
        const severity = data.severity || 'resisted';
        const points = data.points || 0;
        const creativity = data.creativity || 0;
        
        // Update score
        this.scoreTotal += points;
        this.updateScoreIndicator(this.scoreTotal);
        
        this.removeLastThinking();
        
        // Get result display
        const {resultIcon, resultText} = this.getResultDisplay(severity, broke);
        
        // Build inline scoring HTML
        const scoringHTML = `
            <div class="attack-result" style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid rgba(255,255,255,0.2); font-size: 0.875rem;">
                ${resultIcon} <strong>${resultText}</strong> - +${points}pts
                ${creativity > 7 ? ` <span style="opacity: 0.8;">🎨 Creative!</span>` : ''}
            </div>
        `;
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="message house">
                <div class="avatar">🤖</div>
                <div class="message-content">
                    <span class="speaker-name">Chad's Response:</span>
                    <div class="message-text">${this.escapeHtml(response)}</div>
                    ${scoringHTML}
                </div>
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleComplete(data) {
        const result = data.result;
        
        if (this.headerDiv) {
            const successEmoji = result.success ? '🎉' : '⚔️';
            const statusText = result.success ? 'YOU WIN!' : 'Challenge Complete';
            
            this.headerDiv.innerHTML = `
                <h2>${successEmoji} ${statusText}</h2>
                <div class="score-indicator">Final Score: ${result.score} points</div>
            `;
        }
        
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
    
    // Helper methods
    
    getResultDisplay(severity, broke) {
        let resultIcon = '❌';
        let resultText = 'RESISTED';
        
        if (severity === 'complete') {
            resultIcon = '💀';
            resultText = 'COMPLETE BREAK!';
        } else if (severity === 'partial') {
            resultIcon = '⚠️';
            resultText = 'PARTIAL BREAK';
        } else if (severity === 'wobble') {
            resultIcon = '🎯';
            resultText = 'WOBBLE';
        } else if (broke) {
            resultIcon = '✅';
            resultText = 'BROKE';
        }
        
        return {resultIcon, resultText};
    }
    
    updateScoreIndicator(score) {
        if (this.headerDiv) {
            const indicator = this.headerDiv.querySelector('.score-indicator');
            if (indicator) {
                indicator.textContent = `Score: ${score}`;
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
window.AttackHandler = AttackHandler;
