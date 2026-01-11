/**
 * Helper to add fingerprint headers to fetch requests
 * Works with all streaming handlers
 */

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
        // Silently fail - fingerprinting is optional
    }
    return {};
}

/**
 * Enhanced fetch with automatic fingerprinting
 * @param {string} url - URL to fetch
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>}
 */
async function fetchWithFingerprint(url, options = {}) {
    const fingerprintHeaders = await getFingerprintHeaders();
    
    options.headers = {
        ...options.headers,
        ...fingerprintHeaders
    };
    
    return fetch(url, options);
}

// Export for use in other scripts
window.getFingerprintHeaders = getFingerprintHeaders;
window.fetchWithFingerprint = fetchWithFingerprint;
