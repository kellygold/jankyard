/**
 * Arena Combat Handler
 * 
 * Handles turn-based tactical combat with HP tracking and judge rulings
 * Extends ChallengeHandler base class for streaming and event handling
 */

class ArenaHandler extends ChallengeHandler {
    constructor(resultsContainer) {
        super('arena', resultsContainer);
        
        // Arena-specific state
        this.playerHp = 100;
        this.gladiatorHp = 100;
        this.currentTurn = 0;
        this.maxTurns = 7;
        this.combatActive = false;
        this.currentLevel = 1;  // Track current level for next level unlock
        
        // Set messagesDiv immediately - chat interface is already in HTML
        this.messagesDiv = this.resultsDiv;
        
        // Register event handlers for new orchestrator pattern
        this.on('start', (data) => this.handleStart(data));
        this.on('update', (data) => this.handleUpdate(data));
        this.on('thinking', (data) => this.handleThinking(data));
        this.on('attack', (data) => this.handleAttack(data));
        this.on('response', (data) => this.handleResponse(data));
        this.on('judgment', (data) => this.handleJudgment(data));
        this.on('summary', (data) => this.handleSummary(data));
        this.on('complete', (data) => this.handleComplete(data));
        this.on('error', (data) => this.handleError(data));
    }
    
    /**
     * Initialize arena UI
     */
    start() {
        // messagesDiv is already set in constructor
        this.showResults();
    }
    
    // Event Handlers
    
    handleStart(data) {
        this.combatActive = true;
        this.showResults();
    }
    
    handleUpdate(data) {
        // Extract from nested structure
        const eventData = data.data || data;
        const metadata = data.metadata || {};  // Metadata is at TOP LEVEL
        
        this.playerHp = metadata.player_hp || this.playerHp;
        this.gladiatorHp = metadata.gladiator_hp || this.gladiatorHp;
        this.currentTurn = metadata.turn || this.currentTurn;
        this.maxTurns = metadata.max_turns || this.maxTurns;
        
        // Show HP bars on first update
        const hpBarsContainer = document.getElementById('hpBarsContainer');
        if (hpBarsContainer) {
            hpBarsContainer.style.display = 'grid';
        }
        
        this.updateHpBars();
        
        // Show combat message if provided
        const message = eventData.message || data.message;
        if (message) {
            this.messagesDiv.insertAdjacentHTML('beforeend', `
                <div class="turn-separator">
                    ${this.escapeHtml(message)}
                </div>
            `);
            this.scrollToBottom();
        }
    }
    
    handleThinking(data) {
        // Extract from nested structure
        const agent = data.agent || 'system';
        let thinkingText = '';
        
        if (agent === 'player') {
            thinkingText = '🛡️ Your fighter considers tactics<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        } else if (agent === 'gladiator') {
            thinkingText = '🔱 Gladiator analyzes the situation<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        } else if (agent === 'judge') {
            thinkingText = '⚖️ Judge evaluates the exchange<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        }
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="thinking-indicator">${thinkingText}</div>
        `);
        this.scrollToBottom();
    }
    
    handleAttack(data) {
        // Extract from nested structure
        const eventData = data.data || data;
        const message = eventData.message || data.message || '';
        
        this.removeLastThinking();
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="combat-move player">
                <strong>🛡️ Your Fighter:</strong> ${this.escapeHtml(message)}
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleResponse(data) {
        // Extract from nested structure
        const eventData = data.data || data;
        const message = eventData.message || data.message || '';
        
        this.removeLastThinking();
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="combat-move gladiator">
                <strong>🔱 Gladiator:</strong> ${this.escapeHtml(message)}
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleJudgment(data) {
        // Extract from nested structure (CRITICAL for HP bars!)
        const eventData = data.data || data;
        const metadata = data.metadata || {};  // Metadata is at TOP LEVEL
        const message = eventData.message || data.message || '';
        
        this.removeLastThinking();
        
        // Extract damage values
        const playerDamage = metadata.player_damage ?? eventData.player_damage ?? 0;
        const gladiatorDamage = metadata.gladiator_damage ?? eventData.gladiator_damage ?? 0;
        
        // Update HP from judge ruling metadata
        this.playerHp = metadata.player_hp ?? eventData.player_hp ?? this.playerHp;
        this.gladiatorHp = metadata.gladiator_hp ?? eventData.gladiator_hp ?? this.gladiatorHp;
        
        this.updateHpBars();
        
        // Build damage display
        let damageHtml = '<div class="damage-summary">';
        
        if (playerDamage > 0) {
            damageHtml += `<div class="damage player-damage">💔 <strong>You: -${playerDamage} HP</strong> → ${this.playerHp}/100</div>`;
        } else {
            damageHtml += `<div class="damage player-damage" style="opacity: 0.6;">🛡️ <strong>You: No damage</strong></div>`;
        }
        
        if (gladiatorDamage > 0) {
            damageHtml += `<div class="damage gladiator-damage">⚔️ <strong>Gladiator: -${gladiatorDamage} HP</strong> → ${this.gladiatorHp}/100</div>`;
        } else {
            damageHtml += `<div class="damage gladiator-damage" style="opacity: 0.6;">🛡️ <strong>Gladiator: No damage</strong></div>`;
        }
        
        damageHtml += '</div>';
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="judge-ruling">
                <strong>⚖️ Judge Rules:</strong>
                <div class="ruling-text">${this.escapeHtml(message)}</div>
                ${damageHtml}
            </div>
        `);
        
        this.scrollToBottom();
    }
    
    handleSummary(data) {
        // Extract from nested structure
        const eventData = data.data || data;
        const message = eventData.message || data.message || '';
        const metadata = data.metadata || {};  // Metadata is at TOP LEVEL
        
        this.removeLastThinking();
        
        // Final HP update
        if (metadata.player_hp !== undefined) {
            this.playerHp = metadata.player_hp;
            this.gladiatorHp = metadata.gladiator_hp;
            this.updateHpBars();
        }
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="summary-message">
                <pre style="white-space: pre-wrap; font-family: inherit; margin: 0;">${this.escapeHtml(message)}</pre>
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleComplete(data) {
        this.combatActive = false;
        
        // Extract from nested structure
        const eventData = data.data || data;
        const result = eventData.result || data.result;
        
        // Get outcome from result or previous summary
        const outcome = result.success ? 'victory' : 'defeat';
        
        let resultClass = '';
        let resultIcon = '';
        let resultText = '';
        
        if (outcome === 'victory') {
            resultClass = 'victory';
            resultIcon = '🏆';
            resultText = 'VICTORY!';
        } else if (outcome === 'defeat') {
            resultClass = 'defeat';
            resultIcon = '💀';
            resultText = 'DEFEAT';
        } else {
            resultClass = 'draw';
            resultIcon = '🤝';
            resultText = 'DRAW';
        }
        
        // Old inline result banner removed - now using modal
        this.scrollToBottom();
        
        // Determine next level availability
        const nextLevel = this.currentLevel + 1;
        const hasNextLevel = nextLevel <= 2;  // Arena has 2 levels (normal/hard)
        
        // Show appropriate modal based on outcome after delay so user can read the final result
        setTimeout(() => {
            if (outcome === 'victory') {
                if (typeof showCompletionModal === 'function') {
                    showCompletionModal({
                        ...result,
                        outcome: outcome,
                        message: result.message || 'You emerged victorious from the arena!',
                        player_hp: this.playerHp,
                        gladiator_hp: this.gladiatorHp,
                        stat1Label: 'YOUR HP',
                        stat1Value: `${this.playerHp}/100`,
                        stat2Label: 'ARENA',
                        stat2Value: `${this.currentLevel}/2`,
                        stat3Label: 'SCORE',
                        stat3Value: result.score || '-',
                        unlocked_next_level: hasNextLevel,
                        next_level: hasNextLevel ? nextLevel : null,
                        next_level_text: '⚔️ Next Arena'
                    });
                }
            } else {
                // Defeat or draw - show defeat modal
                if (typeof showDefeatModal === 'function') {
                    showDefeatModal({
                        ...result,
                        outcome: outcome,
                        message: result.message || (outcome === 'defeat' ? 'The gladiator was victorious.' : 'The battle ended in a draw.'),
                        player_hp: this.playerHp,
                        gladiator_hp: this.gladiatorHp,
                        stat1Label: 'YOUR HP',
                        stat1Value: `${this.playerHp}/100`,
                        stat2Label: 'ARENA',
                        stat2Value: `${this.currentLevel}/2`,
                        stat3Label: 'SCORE',
                        stat3Value: result.score || '0'
                    });
                }
            }
        }, 2000); // 2 second delay to read result
    }
    
    handleError(data) {
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="error-message">
                <strong>❌ Error:</strong> ${this.escapeHtml(data.message || 'Unknown error')}
            </div>
        `);
        this.scrollToBottom();
    }
    
    // Helper methods
    
    updateHpBars() {
        const playerPercent = Math.max(0, (this.playerHp / 100) * 100);
        const gladiatorPercent = Math.max(0, (this.gladiatorHp / 100) * 100);
        
        const playerBar = document.getElementById('playerHpBar');
        const gladiatorBar = document.getElementById('gladiatorHpBar');
        const playerText = document.getElementById('playerHpText');
        const gladiatorText = document.getElementById('gladiatorHpText');
        
        if (playerBar) {
            playerBar.style.width = playerPercent + '%';
            // Add flash effect for damage
            if (playerPercent < 100) {
                playerBar.style.filter = 'brightness(1.3)';
                setTimeout(() => { if (playerBar) playerBar.style.filter = 'brightness(1)'; }, 300);
            }
        }
        if (gladiatorBar) {
            gladiatorBar.style.width = gladiatorPercent + '%';
            // Add flash effect for damage
            if (gladiatorPercent < 100) {
                gladiatorBar.style.filter = 'brightness(1.3)';
                setTimeout(() => { if (gladiatorBar) gladiatorBar.style.filter = 'brightness(1)'; }, 300);
            }
        }
        if (playerText) playerText.textContent = `${this.playerHp}/100 HP`;
        if (gladiatorText) gladiatorText.textContent = `${this.gladiatorHp}/100 HP`;
        
        // Color changes based on HP
        if (playerBar) {
            if (this.playerHp <= 20) {
                playerBar.style.background = 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)';
            } else if (this.playerHp <= 50) {
                playerBar.style.background = 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)';
            } else {
                playerBar.style.background = 'linear-gradient(90deg, #00b894 0%, #00cec9 100%)';
            }
        }
        
        if (gladiatorBar) {
            if (this.gladiatorHp <= 20) {
                gladiatorBar.style.background = 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)';
            } else if (this.gladiatorHp <= 50) {
                gladiatorBar.style.background = 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)';
            } else {
                gladiatorBar.style.background = 'linear-gradient(90deg, #e63946 0%, #c1121f 100%)';
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
window.ArenaHandler = ArenaHandler;
