/**
 * Base Chat Handler
 * 
 * Shared functionality for all streaming chat-based challenges.
 * Handles common operations like message rendering, scrolling, and utilities.
 */

class BaseChatHandler {
    constructor(resultsContainer, containerClass = 'chat-container') {
        this.resultsDiv = typeof resultsContainer === 'string' 
            ? document.getElementById(resultsContainer) 
            : resultsContainer;
        
        this.containerClass = containerClass;
        this.currentRound = 0;
        this.messagesDiv = null;
        this.headerDiv = null;
    }
    
    /**
     * Initialize chat UI
     * Subclasses should override to customize header
     */
    start(headerEmoji = '💬', headerText = 'Starting...', indicatorText = 'Preparing...') {
        this.resultsDiv.innerHTML = `
            <div class="${this.containerClass}">
                <div class="chat-header" id="chatHeader">
                    <h2>${headerEmoji} ${headerText}</h2>
                    <div class="chat-indicator">${indicatorText}</div>
                </div>
                <div class="chat-messages" id="chatMessages"></div>
            </div>
        `;
        
        this.messagesDiv = document.getElementById('chatMessages');
        this.headerDiv = document.getElementById('chatHeader');
    }
    
    /**
     * Handle 'thinking' event
     * Subclasses can override for custom labels
     */
    handleThinking(data) {
        const who = data.who;
        const round = data.round || this.currentRound;
        
        const {emoji, label} = this.getThinkingLabel(who, round);
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="thinking-indicator">
                ${emoji} <em>${label}</em>
            </div>
        `);
        
        this.scrollToBottom();
    }
    
    /**
     * Get thinking indicator emoji and label
     * Override in subclasses for custom labels
     */
    getThinkingLabel(who, round) {
        let emoji = '🤔';
        let label = 'Thinking...';
        
        if (who === 'user' || who === 'attacker') {
            emoji = '💭';
            label = 'Your AI is thinking...';
        } else if (who === 'house' || who === 'defender' || who === 'chad') {
            emoji = '🧠';
            label = 'Chad is thinking...';
        } else if (who === 'judge') {
            emoji = '⚖️';
            label = 'Judge is deliberating...';
        }
        
        return {emoji, label};
    }
    
    /**
     * Render a chat message with original styling (circular avatars, flexbox layout)
     * @param {string} who - 'user' or 'house'
     * @param {string} text - Message text
     * @param {string} speakerLabel - Label like "USER (PRO) - Round 1" or "You"
     * @param {string} extraContent - Additional HTML content (e.g., scoring)
     */
    renderMessage(who, text, speakerLabel = null, extraContent = '') {
        const isUser = who === 'user';
        const messageClass = isUser ? 'user' : 'house';
        const defaultLabel = isUser ? 'You' : 'Chad';
        const label = speakerLabel || defaultLabel;
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="message ${messageClass}">
                <div class="avatar">${isUser ? '👤' : '🤖'}</div>
                <div class="message-content">
                    <span class="speaker-name">${label}</span>
                    <div class="message-text">${this.escapeHtml(text)}</div>
                    ${extraContent}
                </div>
            </div>
        `);
        
        this.scrollToBottom();
    }
    
    /**
     * Remove the last thinking indicator
     */
    removeLastThinkingIndicator() {
        const thinkingIndicators = this.messagesDiv.querySelectorAll('.thinking-indicator');
        if (thinkingIndicators.length > 0) {
            thinkingIndicators[thinkingIndicators.length - 1].remove();
        }
    }
    
    /**
     * Handle 'complete' event
     * Subclasses should override for custom completion messages
     */
    handleComplete(data) {
        const result = data.result;
        
        if (this.headerDiv) {
            const successEmoji = result.success ? '🎉' : '❌';
            const statusText = result.success ? 'Complete!' : 'Ended';
            
            this.headerDiv.innerHTML = `
                <h2>${successEmoji} ${statusText}</h2>
                <div class="chat-indicator">Final Score: ${result.score} points</div>
            `;
        }
        
        this.scrollToBottom();
    }
    
    /**
     * Handle 'error' event
     */
    handleError(data) {
        this.resultsDiv.innerHTML += `
            <div class="error-message">
                <strong>❌ Error:</strong> ${this.escapeHtml(data.message || 'Unknown error')}
            </div>
        `;
    }
    
    /**
     * Update header indicator
     */
    updateHeaderIndicator(text) {
        if (this.headerDiv) {
            const indicator = this.headerDiv.querySelector('.chat-indicator');
            if (indicator) {
                indicator.textContent = text;
            }
        }
    }
    
    /**
     * Scroll to bottom of results
     */
    scrollToBottom() {
        // Find the last message and scroll it into view
        if (this.messagesDiv && this.messagesDiv.lastElementChild) {
            this.messagesDiv.lastElementChild.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest',
                inline: 'nearest'
            });
        }
    }
    
    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
