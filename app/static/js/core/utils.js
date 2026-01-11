/**
 * Shared Utility Functions for Challenges
 */

/**
 * Format a score with commas
 * @param {number} score - Score to format
 * @returns {string} - Formatted score
 */
function formatScore(score) {
    return score.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * Create a message element
 * @param {string} who - 'user' or 'house'
 * @param {string} text - Message text
 * @param {string} label - Speaker label
 * @returns {string} - HTML string
 */
function createMessage(who, text, label = null) {
    const isUser = who === 'user';
    const messageClass = isUser ? 'user' : 'house';
    const defaultLabel = isUser ? 'You' : 'AI';
    const speakerLabel = label || defaultLabel;
    const avatar = isUser ? '👤' : '🤖';
    
    return `
        <div class="message ${messageClass}">
            <div class="avatar">${avatar}</div>
            <div class="message-content">
                <span class="speaker-name">${speakerLabel}</span>
                <div class="message-text">${escapeHtml(text)}</div>
            </div>
        </div>
    `;
}

/**
 * Escape HTML
 * @param {string} text - Text to escape
 * @returns {string} - Escaped HTML
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Show a thinking indicator
 * @param {string} label - Label text
 * @param {string} emoji - Emoji to show
 * @returns {string} - HTML string
 */
function createThinkingIndicator(label = 'Thinking...', emoji = '🤔') {
    return `
        <div class="thinking-indicator">
            ${emoji} <em>${label}</em>
        </div>
    `;
}

/**
 * Remove last thinking indicator from container
 * @param {HTMLElement} container - Container element
 */
function removeLastThinking(container) {
    const indicators = container.querySelectorAll('.thinking-indicator');
    if (indicators.length > 0) {
        indicators[indicators.length - 1].remove();
    }
}

/**
 * Scroll element into view smoothly
 * @param {HTMLElement} element - Element to scroll to
 */
function scrollToElement(element) {
    if (element) {
        element.scrollIntoView({
            behavior: 'smooth',
            block: 'nearest',
            inline: 'nearest'
        });
    }
}

/**
 * Get form value safely
 * @param {string} id - Element ID
 * @param {any} defaultValue - Default value if not found
 * @returns {any} - Form value or default
 */
function getFormValue(id, defaultValue = '') {
    const element = document.getElementById(id);
    return element ? element.value : defaultValue;
}

/**
 * Set form value safely
 * @param {string} id - Element ID
 * @param {any} value - Value to set
 */
function setFormValue(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.value = value;
    }
}

/**
 * Show/hide element
 * @param {string|HTMLElement} element - Element or ID
 * @param {boolean} show - True to show, false to hide
 */
function toggleElement(element, show) {
    const el = typeof element === 'string' ? document.getElementById(element) : element;
    if (el) {
        el.style.display = show ? 'block' : 'none';
    }
}

/**
 * Create a progress bar
 * @param {number} current - Current value
 * @param {number} max - Maximum value
 * @param {string} color - Bar color
 * @returns {string} - HTML string
 */
function createProgressBar(current, max, color = '#22c55e') {
    const percentage = Math.min(100, Math.max(0, (current / max) * 100));
    return `
        <div style="width: 100%; height: 24px; background: rgba(255,255,255,0.1); border-radius: 12px; overflow: hidden;">
            <div style="width: ${percentage}%; height: 100%; background: ${color}; transition: width 0.3s ease; display: flex; align-items: center; justify-content: center; color: white; font-size: 0.85rem; font-weight: bold;">
                ${current} / ${max}
            </div>
        </div>
    `;
}

/**
 * Create a badge/pill
 * @param {string} text - Badge text
 * @param {string} color - Badge color
 * @returns {string} - HTML string
 */
function createBadge(text, color = 'rgba(59,130,246,0.2)') {
    return `
        <span style="display: inline-block; padding: 0.25rem 0.75rem; background: ${color}; border-radius: 12px; font-size: 0.85rem; font-weight: 500;">
            ${text}
        </span>
    `;
}

// Export to global scope
window.JankyardUtils = {
    formatScore,
    createMessage,
    escapeHtml,
    createThinkingIndicator,
    removeLastThinking,
    scrollToElement,
    getFormValue,
    setFormValue,
    toggleElement,
    createProgressBar,
    createBadge
};
