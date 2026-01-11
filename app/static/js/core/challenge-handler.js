/**
 * Generic Challenge Handler Base Class
 * 
 * All challenge-specific handlers extend this class to get:
 * - Form data building
 * - Fingerprint headers
 * - SSE streaming
 * - Event routing
 * - Error handling
 * 
 * Usage:
 *   class MyHandler extends ChallengeHandler {
 *       constructor(resultsContainer) {
 *           super('my_challenge', resultsContainer);
 *           
 *           // Register event handlers
 *           this.on('custom_event', (data) => this.handleCustom(data));
 *       }
 *       
 *       handleCustom(data) {
 *           // Your unique logic here
 *       }
 *   }
 */

class ChallengeHandler {
    /**
     * @param {string} challengeName - Name of the challenge
     * @param {string|HTMLElement} resultsContainer - Results container element or ID
     * @param {object} options - Additional options
     */
    constructor(challengeName, resultsContainer, options = {}) {
        this.challengeName = challengeName;
        this.resultsDiv = typeof resultsContainer === 'string'
            ? document.getElementById(resultsContainer)
            : resultsContainer;
        
        if (!this.resultsDiv) {
            throw new Error(`Results container not found: ${resultsContainer}`);
        }
        
        this.options = {
            autoScroll: true,
            showThinking: true,
            endpoint: '/submit/stream',
            ...options
        };
        
        // Event handlers registry
        this.eventHandlers = {};
        
        // State
        this.isStreaming = false;
        this.abortController = null;
        
        // Register default event handlers
        this._registerDefaultHandlers();
    }
    
    /**
     * Register default event handlers that most challenges need
     */
    _registerDefaultHandlers() {
        // These can be overridden by calling this.on() in subclass constructor
        this.on('error', (data) => this.handleError(data));
        this.on('complete', (data) => this.handleComplete(data));
    }
    
    /**
     * Register an event handler
     * 
     * @param {string} eventType - Event type from SSE
     * @param {function} handler - Handler function(data)
     * @returns {ChallengeHandler} - For chaining
     */
    on(eventType, handler) {
        this.eventHandlers[eventType] = handler;
        return this;
    }
    
    /**
     * Stream a challenge submission
     * 
     * @param {string|object} actionData - User action (prompt text or action object)
     * @param {string} difficulty - Optional difficulty level
     * @param {object} extraData - Additional form data
     */
    async stream(actionData, difficulty = null, extraData = {}) {
        if (this.isStreaming) {
            console.warn('Already streaming, ignoring request');
            return;
        }
        
        this.isStreaming = true;
        this.showResults();
        
        try {
            // Build form data
            const formData = this.buildFormData(actionData, difficulty, extraData);
            
            // Get fingerprint headers
            const headers = await this.getFingerprintHeaders();
            
            // Create abort controller for cancellation
            this.abortController = new AbortController();
            
            // Make request
            const response = await fetch(this.options.endpoint, {
                method: 'POST',
                body: formData,
                headers: headers,
                signal: this.abortController.signal
            });
            
            if (!response.ok) {
                const error = await response.json().catch(() => ({ error: 'Request failed' }));
                throw new Error(error.error || `HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Process SSE stream
            await this.processSSE(response);
            
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Stream aborted');
            } else {
                console.error('Stream error:', error);
                this.handleError({ message: error.message });
            }
        } finally {
            this.isStreaming = false;
            this.abortController = null;
        }
    }
    
    /**
     * Stop current stream
     */
    abort() {
        if (this.abortController) {
            this.abortController.abort();
        }
    }
    
    /**
     * Build form data for submission
     * Override this if you need custom form fields
     * 
     * @param {string|object} actionData - User action
     * @param {string} difficulty - Difficulty level
     * @param {object} extraData - Additional fields
     * @returns {FormData}
     */
    buildFormData(actionData, difficulty, extraData) {
        const formData = new FormData();
        
        // Required fields
        formData.append('challenge_name', this.challengeName);
        formData.append('agent_type', 'prompt');
        
        // Action data
        if (typeof actionData === 'string') {
            formData.append('agent_code', actionData);
        } else if (typeof actionData === 'object') {
            formData.append('agent_code', JSON.stringify(actionData));
        }
        
        // Optional difficulty
        if (difficulty) {
            formData.append('difficulty', difficulty);
        }
        
        // Username (from form or localStorage)
        const username = document.getElementById('username')?.value || 
                        localStorage.getItem('jankyard_username');
        if (username) {
            formData.append('username', username);
        }
        
        // Any extra data
        for (const [key, value] of Object.entries(extraData)) {
            formData.append(key, value);
        }
        
        return formData;
    }
    
    /**
     * Get fingerprint headers
     * Uses the global getFingerprintHeaders() if available
     * 
     * @returns {object} Headers object
     */
    async getFingerprintHeaders() {
        try {
            if (typeof getFingerprintHeaders === 'function') {
                return await getFingerprintHeaders();
            }
        } catch (e) {
            console.warn('Fingerprinting failed:', e);
        }
        return {};
    }
    
    /**
     * Process Server-Sent Events stream
     * 
     * @param {Response} response - Fetch response
     */
    async processSSE(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const {done, value} = await reader.read();
            
            if (done) {
                // Process any remaining data in buffer
                if (buffer.trim()) {
                    this._processSSELine(buffer);
                }
                break;
            }
            
            // Decode chunk
            buffer += decoder.decode(value, {stream: true});
            
            // Process complete lines
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer
            
            for (const line of lines) {
                this._processSSELine(line);
            }
        }
    }
    
    /**
     * Process a single SSE line
     * @private
     */
    _processSSELine(line) {
        if (line.startsWith('data: ')) {
            try {
                const data = JSON.parse(line.slice(6));
                this.handleEvent(data);
            } catch (e) {
                console.error('Failed to parse SSE data:', line, e);
            }
        }
    }
    
    /**
     * Route event to appropriate handler
     * 
     * @param {object} data - Event data
     */
    handleEvent(data) {
        const eventType = data.type || data.event || 'unknown';
        
        console.log(`🔔 ChallengeHandler.handleEvent: type="${eventType}", has handler=${!!this.eventHandlers[eventType]}`, data);
        
        // Call registered handler if exists
        if (this.eventHandlers[eventType]) {
            try {
                console.log(`  ➡️  Calling handler for "${eventType}"`);
                this.eventHandlers[eventType](data);
            } catch (e) {
                console.error(`Error in ${eventType} handler:`, e);
            }
        } else {
            // No handler registered
            console.warn('Unhandled event:', eventType, data);
        }
    }
    
    /**
     * Default error handler
     * Override this or register custom handler with: this.on('error', ...)
     * 
     * Supports both legacy and standardized event formats:
     * - Legacy: {type: 'error', message: '...'}
     * - Standard: {type: 'error', agent: 'system', data: {message: '...'}, metadata: {}}
     */
    handleError(data) {
        // Support both old and new format
        const message = data.data?.message || data.message || data.error || 'Unknown error occurred';
        this.resultsDiv.innerHTML += `
            <div class="error-message" style="background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); padding: 1rem; border-radius: 8px; margin: 1rem 0;">
                <strong>❌ Error:</strong> ${this.escapeHtml(message)}
            </div>
        `;
        
        if (this.options.autoScroll) {
            this.scrollToBottom();
        }
    }
    
    /**
     * Default completion handler
     * Override this or register custom handler with: this.on('complete', ...)
     * 
     * Supports both legacy and standardized event formats:
     * - Legacy: {type: 'complete', result: {...}}
     * - Standard: {type: 'complete', agent: 'system', data: {result: {...}}, metadata: {}}
     */
    handleComplete(data) {
        console.log('Challenge complete:', data);
        
        // Support both old and new format
        const result = data.data?.result || data.result || data.data || data;
        const score = result.score || 0;
        const success = result.success || false;
        
        this.resultsDiv.innerHTML += `
            <div class="completion-message" style="background: rgba(${success ? '34,197,94' : '156,163,175'},0.1); border: 1px solid rgba(${success ? '34,197,94' : '156,163,175'},0.3); padding: 1.5rem; border-radius: 8px; margin: 1rem 0; text-align: center;">
                <h3 style="margin: 0 0 0.5rem 0;">${success ? '🎉 Success!' : '💭 Challenge Complete'}</h3>
                <div style="font-size: 1.5rem; font-weight: bold;">Score: ${score}</div>
            </div>
        `;
        
        if (this.options.autoScroll) {
            this.scrollToBottom();
        }
    }
    
    /**
     * Show results container
     */
    showResults() {
        if (this.resultsDiv) {
            this.resultsDiv.style.display = 'block';
        }
    }
    
    /**
     * Hide results container
     */
    hideResults() {
        if (this.resultsDiv) {
            this.resultsDiv.style.display = 'none';
        }
    }
    
    /**
     * Clear results
     */
    clearResults() {
        if (this.resultsDiv) {
            this.resultsDiv.innerHTML = '';
        }
    }
    
    /**
     * Scroll to bottom of results
     */
    scrollToBottom() {
        if (this.resultsDiv && this.resultsDiv.lastElementChild) {
            this.resultsDiv.lastElementChild.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
                inline: 'nearest'
            });
        }
    }
    
    /**
     * Escape HTML for safe display
     * 
     * @param {string} text - Text to escape
     * @returns {string} - Escaped HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Utility: Disable submit button
     * 
     * @param {string|HTMLElement} button - Button element or ID
     * @param {string} text - Optional text to show while disabled
     */
    disableButton(button, text = null) {
        const btn = typeof button === 'string' ? document.getElementById(button) : button;
        if (btn) {
            btn.disabled = true;
            if (text) {
                btn.dataset.originalText = btn.textContent;
                btn.textContent = text;
            }
        }
    }
    
    /**
     * Utility: Enable submit button
     * 
     * @param {string|HTMLElement} button - Button element or ID
     */
    enableButton(button) {
        const btn = typeof button === 'string' ? document.getElementById(button) : button;
        if (btn) {
            btn.disabled = false;
            if (btn.dataset.originalText) {
                btn.textContent = btn.dataset.originalText;
                delete btn.dataset.originalText;
            }
        }
    }
    
    /**
     * Generic utility to check unlocked levels from database
     * Can be used by any multi-level challenge
     * 
     * @param {string} challengeName - Name of the challenge
     * @returns {Promise<number[]>} Array of unlocked level numbers
     * 
     * @example
     * const unlockedLevels = await ChallengeHandler.checkUnlockedLevels('telephone_game');
     * console.log('Unlocked:', unlockedLevels); // [1, 2]
     */
    static async checkUnlockedLevels(challengeName) {
        try {
            const token = localStorage.getItem('access_token');
            const storedUsername = localStorage.getItem('jankyard_username');
            
            // Build URL with username param for anonymous users
            let url = `/leaderboard/${challengeName}/progress`;
            if (!token && storedUsername) {
                url += `?username=${encodeURIComponent(storedUsername)}`;
            }
            
            // Build headers
            const headers = {};
            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }
            
            // Get progress from API
            const progressResponse = await fetch(url, { headers });
            
            if (progressResponse.ok) {
                const progressData = await progressResponse.json();
                return progressData.unlocked_levels || [1];
            }
            
            return [1];
        } catch (error) {
            console.error(`Failed to check unlocked levels for ${challengeName}:`, error);
            return [1];
        }
    }
    
    /**
     * Generic utility to update level tab states based on unlocked levels
     * Can be used by any multi-level challenge
     * 
     * @param {number[]} unlockedLevels - Array of unlocked level numbers
     * @param {number} maxLevel - Maximum level number
     * 
     * @example
     * ChallengeHandler.updateLevelTabs([1, 2], 3);
     */
    static updateLevelTabs(unlockedLevels, maxLevel = 3) {
        for (let level = 1; level <= maxLevel; level++) {
            const tab = document.querySelector(`.level-tab[data-level="${level}"]`);
            if (tab) {
                const isUnlocked = unlockedLevels.includes(level);
                tab.disabled = !isUnlocked;
                
                if (!isUnlocked) {
                    tab.classList.add('locked');
                } else {
                    tab.classList.remove('locked');
                }
            }
        }
    }
    
    /**
     * Standardized challenge initialization
     * Handles: auth check, unlocked levels, username prefill, tab updates, logging
     * 
     * @param {Object} config - Configuration object
     * @param {string} config.challengeName - Name of the challenge (e.g., 'firewall', 'giga_chad')
     * @param {number} [config.maxLevel=3] - Maximum level number
     * @param {boolean} [config.prefillUsername=true] - Whether to pre-fill username field
     * @param {boolean} [config.verbose=true] - Enable detailed logging
     * @returns {Promise<Object>} - {unlockedLevels, username, isAuthenticated, token}
     * 
     * @example
     * const {unlockedLevels, username} = await ChallengeHandler.init({
     *     challengeName: 'firewall',
     *     maxLevel: 3,
     *     prefillUsername: true,
     *     verbose: true
     * });
     */
    static async init(config) {
        const {
            challengeName,
            maxLevel = 3,
            prefillUsername = true,
            verbose = true
        } = config;
        
        if (verbose) console.log(`🚀 Initializing ${challengeName}...`);
        
        const token = localStorage.getItem('access_token');
        const isAuthenticated = !!token;
        
        if (verbose) console.log(`🔑 Auth status: ${isAuthenticated ? 'Logged in' : 'Guest mode'}`);
        
        let username = null;
        let unlockedLevels = [1];
        
        if (isAuthenticated) {
            // Fetch user info and pre-fill username
            if (prefillUsername) {
                try {
                    const userResponse = await fetch('/auth/me', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (userResponse.ok) {
                        const userData = await userResponse.json();
                        username = userData.username;
                        
                        // Auto-fill username field if it exists
                        const usernameField = document.getElementById('username');
                        if (usernameField) {
                            usernameField.value = username;
                            usernameField.readOnly = true;
                            usernameField.style.opacity = '0.7';
                            usernameField.style.cursor = 'not-allowed';
                        }
                        
                        if (verbose) console.log(`👤 User: ${username}`);
                    }
                } catch (error) {
                    console.warn('⚠️ Failed to fetch user info:', error);
                }
            }
            
            // Fetch unlocked levels
            unlockedLevels = await ChallengeHandler.checkUnlockedLevels(challengeName);
            if (verbose) console.log(`📊 Unlocked levels: [${unlockedLevels.join(', ')}]`);
        } else {
            // Guest mode - check for stored username and fetch progress
            const storedUsername = localStorage.getItem('jankyard_username');
            if (storedUsername) {
                username = storedUsername;
                if (verbose) console.log(`👤 Guest with stored username: ${username}`);
                
                // Pre-fill username field
                const usernameField = document.getElementById('username');
                if (usernameField && prefillUsername) {
                    usernameField.value = username;
                }
                
                // Fetch unlocked levels for this username
                unlockedLevels = await ChallengeHandler.checkUnlockedLevels(challengeName);
                if (verbose) console.log(`📊 Unlocked levels: [${unlockedLevels.join(', ')}]`);
            } else {
                if (verbose) console.log(`📊 Guest mode: Level 1 only`);
            }
        }
        
        // Update level tabs
        ChallengeHandler.updateLevelTabs(unlockedLevels, maxLevel);
        
        if (verbose) console.log(`✅ ${challengeName} initialized successfully`);
        
        return {
            unlockedLevels,
            username,
            isAuthenticated,
            token
        };
    }
    
    /**
     * Handle level completion - unlocks next level and syncs with server
     * Call this from handleComplete() or custom modal logic
     * 
     * @param {Object} config - Configuration object
     * @param {ChallengeHandler} config.handler - The challenge handler instance
     * @param {Object} config.result - The completion result from backend
     * @param {number} config.maxLevel - Maximum level for this challenge
     * @param {string} config.challengeName - Name of the challenge
     * @returns {Promise<Object>} - {unlockedLevels, nextLevel, hasNextLevel, shouldShowNextButton}
     */
    static async handleLevelCompletion(config) {
        const { handler, result, maxLevel, challengeName } = config;
        
        const currentLevel = handler.currentLevel || 1;
        const nextLevel = currentLevel + 1;
        const hasNextLevel = nextLevel <= maxLevel;
        
        // Initialize unlockedLevels if not present
        if (!handler.unlockedLevels) {
            handler.unlockedLevels = [1];
        }
        
        // Step 1: Optimistically unlock next level locally if success
        let locallyUnlocked = false;
        if (result.success && hasNextLevel && !handler.unlockedLevels.includes(nextLevel)) {
            handler.unlockedLevels.push(nextLevel);
            locallyUnlocked = true;
            console.log(`🔓 Locally unlocked level ${nextLevel}`);
        }
        
        // Step 2: Update UI immediately
        ChallengeHandler.updateLevelTabs(handler.unlockedLevels, maxLevel);
        
        // Step 3: Sync with server (async, don't block)
        try {
            const serverLevels = await ChallengeHandler.checkUnlockedLevels(challengeName);
            
            // Merge local and server (keep any locally unlocked that server hasn't saved yet)
            const mergedLevels = [...new Set([...handler.unlockedLevels, ...serverLevels])];
            handler.unlockedLevels = mergedLevels;
            
            // Update UI with merged state
            ChallengeHandler.updateLevelTabs(mergedLevels, maxLevel);
            console.log(`📊 Synced levels: [${mergedLevels.join(', ')}]`);
        } catch (error) {
            console.warn('⚠️ Server sync failed, using local state:', error);
        }
        
        // Step 4: Determine if next button should show
        const shouldShowNextButton = result.success && hasNextLevel && handler.unlockedLevels.includes(nextLevel);
        
        return {
            unlockedLevels: handler.unlockedLevels,
            currentLevel,
            nextLevel,
            hasNextLevel,
            shouldShowNextButton,
            locallyUnlocked
        };
    }
    
    /**
     * Wire up a next level button with standard behavior
     * 
     * @param {HTMLElement|string} button - Button element or ID
     * @param {number} nextLevel - Level number to switch to
     * @param {Function} closeModalFn - Function to close the modal
     * @param {Function} selectLevelFn - Function to select a level (receives level number)
     */
    static wireNextLevelButton(button, nextLevel, closeModalFn, selectLevelFn) {
        const btn = typeof button === 'string' ? document.getElementById(button) : button;
        if (!btn) return;
        
        btn.style.display = 'block';
        btn.onclick = () => {
            if (closeModalFn) closeModalFn();
            if (selectLevelFn) selectLevelFn(nextLevel);
        };
    }
}

// Export to global scope
window.ChallengeHandler = ChallengeHandler;
