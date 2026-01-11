/**
 * FirewallHandler - Handles The Firewall challenge UI
 * Extends BaseChatHandler for consistent chat interface
 */
class FirewallHandler extends BaseChatHandler {
    constructor(resultsContainer) {
        super(resultsContainer, 'firewall-container');
        this.attemptCount = 0;
        this.blockedCount = 0;
        this.flagRevealed = false;
    }
    
    /**
     * Initialize firewall UI
     */
    start() {
        // Create firewall UI with styled header
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
    }
    
    /**
     * Override thinking labels for firewall-specific terminology
     */
    getThinkingLabel(who, attempt) {
        let emoji = '🤔';
        let label = 'Thinking...';
        
        if (who === 'system') {
            emoji = '🛡️';
            label = `Checking filters...`;
        } else if (who === 'ai') {
            emoji = '🤖';
            label = 'AI is processing...';
        }
        
        return {emoji, label};
    }
    
    /**
     * Handle 'blocked' event - filter caught the attempt
     */
    handleBlocked(data) {
        const attempt = data.attempt || this.attemptCount;
        const filter = data.filter || 'Unknown Filter';
        const reason = data.reason || 'Suspicious pattern detected';
        const hint = data.hint || '';
        
        this.blockedCount++;
        this.updateIndicator();
        
        // Remove thinking indicator
        this.removeLastThinkingIndicator();
        
        // Render blocked message
        const blockedHTML = `
            <div class="filter-block">
                <div class="block-icon">🚫</div>
                <div class="block-content">
                    <h4>BLOCKED by ${filter}</h4>
                    <p>${reason}</p>
                    ${hint ? `<div class="hint">${hint}</div>` : ''}
                </div>
            </div>
        `;
        
        this.messagesDiv.insertAdjacentHTML('beforeend', blockedHTML);
        this.scrollToBottom();
    }
    
    /**
     * Handle 'response' event - AI response (passed filters)
     */
    handleResponse(data) {
        const attempt = data.attempt || this.attemptCount;
        const text = data.text;
        const flagRevealed = data.flag_revealed || false;
        const flag = data.flag;
        const score = data.score || 0;
        
        // Remove thinking indicator
        this.removeLastThinkingIndicator();
        
        if (flagRevealed) {
            // Success! Flag revealed
            this.flagRevealed = true;
            
            const successHTML = `
                <div class="message house success-response">
                    <div class="avatar">🤖</div>
                    <div class="message-content">
                        <span class="speaker-name">AI Assistant</span>
                        <div class="message-text">${this.escapeHtml(text)}</div>
                        <div class="flag-revealed">
                            <div class="flag-icon">🎯</div>
                            <div class="flag-content">
                                <strong>FLAG EXTRACTED!</strong>
                                <code>${flag}</code>
                                <div class="score-badge">+${score} points</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            this.messagesDiv.insertAdjacentHTML('beforeend', successHTML);
        } else {
            // AI resisted - didn't reveal flag
            const resistHTML = `
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
            `;
            
            this.messagesDiv.insertAdjacentHTML('beforeend', resistHTML);
        }
        
        this.scrollToBottom();
    }
    
    /**
     * Handle 'complete' event
     */
    handleComplete(data) {
        const result = data.result;
        const summary = data.summary || {};
        
        // Update header to show completion
        if (this.headerDiv) {
            const successEmoji = result.success ? '🎉' : '🔥';
            const statusText = result.success ? 'BYPASSED!' : 'Challenge Complete';
            
            this.headerDiv.innerHTML = `
                <h2>${successEmoji} ${statusText}</h2>
                <div class="attempt-indicator">Final Score: ${result.score} points</div>
            `;
        }
        
        // Add final summary
        const summaryClass = result.success ? 'success' : '';
        const summaryHTML = `
            <div class="final-summary ${summaryClass}">
                <h3>${result.success ? '🏆 Firewall Bypassed!' : '🛡️ Firewall Held!'}</h3>
                <p><strong>Final Score:</strong> ${result.score} points</p>
                <p><strong>Attempts:</strong> ${summary.attempts || 0}</p>
                <p><strong>Blocked:</strong> ${summary.blocked_count || 0}</p>
                <p><strong>Filters Bypassed:</strong> ${summary.filters_bypassed || 0}</p>
                ${result.success ? '<p class="win-message">You successfully extracted the flag!</p>' : '<p class="fail-message">Try a different approach to bypass the filters!</p>'}
            </div>
        `;
        
        this.messagesDiv.insertAdjacentHTML('beforeend', summaryHTML);
        this.scrollToBottom();
    }
    
    /**
     * Update attempt indicator in header
     */
    updateIndicator() {
        if (this.headerDiv) {
            const indicator = this.headerDiv.querySelector('.attempt-indicator');
            if (indicator) {
                indicator.textContent = `Attempt: ${this.attemptCount} | Blocked: ${this.blockedCount}`;
            }
        }
    }
}
