/**
 * Generic Challenge Streaming Client
 * 
 * Handles SSE streaming for any challenge type with event-based handlers.
 * Eliminates 400+ lines of duplicate code across templates.
 */

class ChallengeStreamer {
    /**
     * @param {string} endpoint - API endpoint ('/submit/stream')
     * @param {HTMLElement|string} resultsContainer - Element or ID to display results
     */
    constructor(endpoint, resultsContainer) {
        this.endpoint = endpoint;
        this.resultsDiv = typeof resultsContainer === 'string' 
            ? document.getElementById(resultsContainer) 
            : resultsContainer;
        
        // Event handlers map
        this.handlers = {};
        
        // State
        this.isStreaming = false;
        this.finalResult = null;
    }
    
    /**
     * Register an event handler
     * @param {string} eventType - Event type ('start', 'thinking', 'message', 'complete', etc.)
     * @param {function} handler - Handler function(data)
     */
    on(eventType, handler) {
        this.handlers[eventType] = handler;
        return this; // Allow chaining
    }
    
    /**
     * Start streaming challenge
     * @param {FormData} formData - Form data to submit
     * @returns {Promise<Object>} Final result
     */
    async stream(formData) {
        if (this.isStreaming) {
            throw new Error('Already streaming');
        }
        
        this.isStreaming = true;
        this.finalResult = null;
        
        // Show results section
        if (this.resultsDiv) {
            this.resultsDiv.style.display = 'block';
        }
        
        try {
            // Get fingerprint headers
            const fingerprintHeaders = await getFingerprintHeaders();
            
            const response = await fetch(this.endpoint, {
                method: 'POST',
                body: formData,
                headers: fingerprintHeaders
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Submission failed');
            }
            
            // Process SSE stream
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            
            while (true) {
                const {done, value} = await reader.read();
                
                if (done) break;
                
                // Decode chunk and add to buffer
                buffer += decoder.decode(value, {stream: true});
                
                // Process complete lines
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep incomplete line in buffer
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const jsonStr = line.substring(6).trim();
                        if (jsonStr) {
                            try {
                                const data = JSON.parse(jsonStr);
                                this._handleEvent(data);
                                
                                // Capture final result
                                if (data.type === 'complete') {
                                    this.finalResult = data.result;
                                }
                            } catch (e) {
                                console.error('Failed to parse SSE data:', jsonStr, e);
                            }
                        }
                    }
                }
            }
            
            return this.finalResult;
            
        } catch (error) {
            this._handleEvent({type: 'error', message: error.message});
            throw error;
        } finally {
            this.isStreaming = false;
        }
    }
    
    /**
     * Internal: Handle incoming event
     */
    _handleEvent(data) {
        const handler = this.handlers[data.type];
        
        if (handler) {
            handler(data);
        } else if (data.type === 'error') {
            // Default error handler
            this._defaultErrorHandler(data);
        }
        
        // Always call 'any' handler if registered
        if (this.handlers['any']) {
            this.handlers['any'](data);
        }
    }
    
    /**
     * Default error handler
     */
    _defaultErrorHandler(data) {
        if (this.resultsDiv) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.style.cssText = 'color: #ff4444; padding: 1rem; margin: 1rem 0; background: rgba(255,68,68,0.1); border-radius: 8px;';
            errorDiv.innerHTML = `<strong>❌ Error:</strong> ${data.message || 'Unknown error'}`;
            this.resultsDiv.appendChild(errorDiv);
        }
    }
    
    /**
     * Clear results
     */
    clear() {
        if (this.resultsDiv) {
            this.resultsDiv.innerHTML = '';
            this.resultsDiv.style.display = 'none';
        }
        this.finalResult = null;
    }
}

/**
 * Utility: Build FormData from form element
 * @param {HTMLFormElement} form - Form element
 * @returns {Promise<FormData>}
 */
async function buildChallengeFormData(form) {
    const formData = new FormData();
    
    // Required fields
    formData.append('challenge_name', form.challenge_name.value);
    formData.append('username', form.username.value || '');
    
    // Optional difficulty
    if (form.difficulty) {
        formData.append('difficulty', form.difficulty.value);
    }
    
    // Agent code or file
    const submitMethod = form.querySelector('input[name="submit_method"]:checked')?.value;
    if (submitMethod === 'code' && form.agent_code) {
        formData.append('agent_code', form.agent_code.value);
    } else if (submitMethod === 'file' && form.agent_file?.files[0]) {
        formData.append('agent_file', form.agent_file.files[0]);
    } else if (form.agent_code) {
        // Fallback: Just send agent_code if no radio buttons
        formData.append('agent_code', form.agent_code.value);
    }
    
    return formData;
}

/**
 * Add client fingerprint to fetch headers
 * @returns {Promise<Object>} Headers with fingerprint
 */
async function getFingerprintHeaders() {
    try {
        if (typeof generateClientFingerprint === 'function') {
            const fingerprint = await generateClientFingerprint();
            return { 'X-Client-Fingerprint': fingerprint };
        }
    } catch (e) {
        console.warn('Fingerprint generation failed:', e);
    }
    return {};
}

/**
 * Utility: Disable/enable submit button
 */
function setSubmitButtonState(button, isSubmitting) {
    button.disabled = isSubmitting;
    
    if (isSubmitting) {
        button.dataset.originalText = button.textContent;
        button.textContent = '⏳ Processing...';
    } else {
        button.textContent = button.dataset.originalText || '🚀 Submit';
    }
}
