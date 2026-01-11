/**
 * Arena Combat Handler
 * 
 * Handles turn-based tactical combat with HP tracking and judge rulings
 */

class ArenaHandler extends BaseChatHandler {
    constructor(containerId) {
        super(containerId);
        this.playerHp = 100;
        this.gladiatorHp = 100;
        this.currentTurn = 0;
        this.maxTurns = 7;
        this.combatActive = false;
    }
    
    start() {
        // Initialize arena UI
        this.resultsDiv.innerHTML = `
            <div class="arena-container">
                <div class="arena-header">
                    <h2>⚔️ Preparing the arena<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span></h2>
                    <div class="hp-bars" style="display:none;">
                        <div class="hp-bar-container">
                            <div class="hp-label">
                                <span>🛡️ You</span>
                                <span id="playerHpText">100/100 HP</span>
                            </div>
                            <div class="hp-bar-bg">
                                <div id="playerHpBar" class="hp-bar-fill player" style="width: 100%;"></div>
                            </div>
                            <div class="status-effects" id="playerStatus"></div>
                        </div>
                        <div class="hp-bar-container">
                            <div class="hp-label">
                                <span>🔱 Gladiator</span>
                                <span id="gladiatorHpText">100/100 HP</span>
                            </div>
                            <div class="hp-bar-bg">
                                <div id="gladiatorHpBar" class="hp-bar-fill gladiator" style="width: 100%;"></div>
                            </div>
                            <div class="status-effects" id="gladiatorStatus"></div>
                        </div>
                    </div>
                </div>
                <div class="combat-messages" id="combatMessages">
                    <div class="thinking-indicator">
                        🎭 The crowd gathers... Combat will begin shortly!
                    </div>
                </div>
            </div>
        `;
        
        this.messagesDiv = document.getElementById('combatMessages');
    }
    
    handleCombatStart(data) {
        // Show HP bars
        document.querySelector('.hp-bars').style.display = 'grid';
        document.querySelector('.arena-header h2').textContent = '⚔️ Combat Begins!';
        
        this.combatActive = true;
        this.playerHp = data.state?.player_hp || 100;
        this.gladiatorHp = data.state?.gladiator_hp || 100;
        this.maxTurns = data.state?.max_turns || 7;
        
        this.updateHpBars();
        
        this.messagesDiv.innerHTML = `
            <div class="thinking-indicator">
                ⚔️ Turn ${this.currentTurn + 1} of ${this.maxTurns} - The battle begins!
            </div>
        `;
    }
    
    handleThinking(data) {
        const who = data.who;
        let thinkingText = '';
        
        if (who === 'player') {
            thinkingText = '🛡️ Your fighter considers tactics<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        } else if (who === 'gladiator') {
            thinkingText = '🔱 Gladiator analyzes the situation<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        } else if (who === 'judge') {
            thinkingText = '⚖️ Judge evaluates the exchange<span class="typing-dots"><span>.</span><span>.</span><span>.</span></span>';
        }
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="thinking-indicator">${thinkingText}</div>
        `);
        this.scrollToBottom();
    }
    
    handlePlayerMove(data) {
        // Remove last thinking indicator
        const lastThinking = this.messagesDiv.querySelector('.thinking-indicator:last-child');
        if (lastThinking) lastThinking.remove();
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="combat-move player">
                <div class="move-label">🛡️ Your Fighter:</div>
                <div>${this.escapeHtml(data.move)}</div>
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleGladiatorMove(data) {
        // Remove last thinking indicator
        const lastThinking = this.messagesDiv.querySelector('.thinking-indicator:last-child');
        if (lastThinking) lastThinking.remove();
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="combat-move gladiator">
                <div class="move-label">🔱 Gladiator's Response:</div>
                <div>${this.escapeHtml(data.move)}</div>
            </div>
        `);
        this.scrollToBottom();
    }
    
    handleJudgeRuling(data) {
        // Remove last thinking indicator
        const lastThinking = this.messagesDiv.querySelector('.thinking-indicator:last-child');
        if (lastThinking) lastThinking.remove();
        
        this.currentTurn = data.turn;
        this.playerHp = data.player_hp;
        this.gladiatorHp = data.gladiator_hp;
        
        // Add judge ruling
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="judge-ruling">
                <div class="move-label">⚖️ Judge's Ruling:</div>
                <div>${this.escapeHtml(data.ruling)}</div>
                <div class="damage-report">
                    <span>🛡️ You took ${data.player_damage} damage</span>
                    <span>🔱 Gladiator took ${data.gladiator_damage} damage</span>
                </div>
            </div>
        `);
        
        // Update HP bars
        this.updateHpBars();
        
        // Show status effects if any
        this.updateStatusEffects(data.player_status, data.gladiator_status);
        
        this.scrollToBottom();
    }
    
    handleNextTurn(data) {
        this.currentTurn = data.turn;
        this.playerHp = data.player_hp;
        this.gladiatorHp = data.gladiator_hp;
        
        // Update header
        document.querySelector('.arena-header h2').textContent = 
            `⚔️ Turn ${this.currentTurn} of ${data.max_turns}`;
        
        this.updateHpBars();
        
        // Add turn separator
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <hr style="margin: 2rem 0; border: none; border-top: 2px solid rgba(255,255,255,0.1);">
            <div class="thinking-indicator" style="opacity: 1; font-weight: bold;">
                ⚔️ Turn ${this.currentTurn} - Continue fighting!
            </div>
        `);
        
        this.scrollToBottom();
    }
    
    handleComplete(data) {
        this.combatActive = false;
        const result = data.result;
        const outcome = data.outcome;
        
        // Update final HP
        if (data.final_state) {
            this.playerHp = data.final_state.player_hp;
            this.gladiatorHp = data.final_state.gladiator_hp;
            this.updateHpBars();
        }
        
        // Determine victory/defeat
        const isVictory = outcome === 'victory';
        const summaryClass = isVictory ? 'victory' : 'defeat';
        const emoji = isVictory ? '🏆' : '💀';
        const message = isVictory ? 'VICTORY!' : 'DEFEAT!';
        
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div class="combat-summary ${summaryClass}">
                <h3>${emoji} ${message}</h3>
                <p style="font-size: 1.2rem; margin: 1rem 0;">
                    Final Score: <strong>${result.score}</strong> points
                </p>
                <div style="margin-top: 1.5rem; opacity: 0.9;">
                    <p>Combat lasted ${result.steps} turns</p>
                    <p>Final HP - You: ${this.playerHp} | Gladiator: ${this.gladiatorHp}</p>
                </div>
            </div>
        `);
        
        // Update header
        document.querySelector('.arena-header h2').textContent = 
            isVictory ? '🏆 Victory!' : '💀 Defeat!';
        
        this.scrollToBottom();
    }
    
    handleError(data) {
        this.messagesDiv.insertAdjacentHTML('beforeend', `
            <div style="color: #ff4444; padding: 1rem; margin: 1rem 0; background: rgba(255,68,68,0.1); border-radius: 8px;">
                <strong>❌ Error:</strong> ${this.escapeHtml(data.message || 'Unknown error')}
            </div>
        `);
        this.scrollToBottom();
    }
    
    updateHpBars() {
        // Update player HP
        const playerPercent = Math.max(0, (this.playerHp / 100) * 100);
        const playerBar = document.getElementById('playerHpBar');
        const playerText = document.getElementById('playerHpText');
        
        if (playerBar) {
            playerBar.style.width = `${playerPercent}%`;
            // Change color based on HP
            if (playerPercent <= 25) {
                playerBar.style.background = 'linear-gradient(90deg, #ff4444 0%, #cc0000 100%)';
            } else if (playerPercent <= 50) {
                playerBar.style.background = 'linear-gradient(90deg, #ffa502 0%, #ff6348 100%)';
            }
        }
        
        if (playerText) {
            playerText.textContent = `${this.playerHp}/100 HP`;
        }
        
        // Update gladiator HP
        const gladiatorPercent = Math.max(0, (this.gladiatorHp / 100) * 100);
        const gladiatorBar = document.getElementById('gladiatorHpBar');
        const gladiatorText = document.getElementById('gladiatorHpText');
        
        if (gladiatorBar) {
            gladiatorBar.style.width = `${gladiatorPercent}%`;
            // Change color based on HP
            if (gladiatorPercent <= 25) {
                gladiatorBar.style.background = 'linear-gradient(90deg, #ff4444 0%, #cc0000 100%)';
            } else if (gladiatorPercent <= 50) {
                gladiatorBar.style.background = 'linear-gradient(90deg, #ffa502 0%, #ff6348 100%)';
            }
        }
        
        if (gladiatorText) {
            gladiatorText.textContent = `${this.gladiatorHp}/100 HP`;
        }
    }
    
    updateStatusEffects(playerStatus, gladiatorStatus) {
        const playerStatusEl = document.getElementById('playerStatus');
        const gladiatorStatusEl = document.getElementById('gladiatorStatus');
        
        if (playerStatusEl) {
            if (playerStatus && playerStatus.length > 0) {
                const statusText = playerStatus.map(s => {
                    if (s === 'NETTED') return '🕸️ NETTED';
                    if (s === 'STUNNED') return '⭐ STUNNED';
                    if (s === 'BLEEDING') return '🩸 BLEEDING';
                    return s;
                }).join(' ');
                playerStatusEl.textContent = statusText;
            } else {
                playerStatusEl.textContent = '';
            }
        }
        
        if (gladiatorStatusEl) {
            if (gladiatorStatus && gladiatorStatus.length > 0) {
                const statusText = gladiatorStatus.map(s => {
                    if (s === 'NETTED') return '🕸️ NETTED';
                    if (s === 'STUNNED') return '⭐ STUNNED';
                    if (s === 'BLEEDING') return '🩸 BLEEDING';
                    return s;
                }).join(' ');
                gladiatorStatusEl.textContent = statusText;
            } else {
                gladiatorStatusEl.textContent = '';
            }
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
