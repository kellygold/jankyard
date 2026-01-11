/**
 * Client-side fingerprinting for Jankyard
 * Collects browser/device data that's hard to spoof
 */

/**
 * Generate comprehensive client fingerprint
 * @returns {string} Base64-encoded fingerprint data
 */
async function generateClientFingerprint() {
    const fp = {
        // Screen & Display
        screen: `${screen.width}x${screen.height}x${screen.colorDepth}`,
        availScreen: `${screen.availWidth}x${screen.availHeight}`,
        
        // Timezone & Locale
        tz: new Date().getTimezoneOffset(),
        tzName: Intl.DateTimeFormat().resolvedOptions().timeZone,
        lang: navigator.language,
        langs: navigator.languages ? navigator.languages.join(',') : '',
        
        // Platform & Hardware
        platform: navigator.platform,
        cores: navigator.hardwareConcurrency || 0,
        memory: navigator.deviceMemory || 0,
        touchPoints: navigator.maxTouchPoints || 0,
        
        // GPU/Graphics Signatures (hardest to fake)
        canvas: getCanvasFingerprint(),
        webgl: getWebGLFingerprint()
    };
    
    // Convert to base64 string
    return btoa(JSON.stringify(fp));
}

/**
 * Generate canvas fingerprint (unique per GPU/driver)
 * @returns {string} Canvas signature hash
 */
function getCanvasFingerprint() {
    try {
        const canvas = document.createElement('canvas');
        canvas.width = 200;
        canvas.height = 50;
        const ctx = canvas.getContext('2d');
        
        // Draw text with specific styling
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillStyle = '#f60';
        ctx.fillRect(0, 0, 200, 50);
        ctx.fillStyle = '#069';
        ctx.fillText('Jankyard.ai 🎪', 2, 2);
        
        // Get data URL and hash last 50 chars (signature)
        const dataUrl = canvas.toDataURL();
        return dataUrl.slice(-50);
    } catch (e) {
        return 'canvas-error';
    }
}

/**
 * Get WebGL renderer info (GPU signature)
 * @returns {string} GPU renderer info
 */
function getWebGLFingerprint() {
    try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        
        if (!gl) return 'no-webgl';
        
        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
        if (!debugInfo) return 'no-debug-info';
        
        const vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
        const renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
        
        return `${vendor}|${renderer}`;
    } catch (e) {
        return 'webgl-error';
    }
}

/**
 * Get audio context fingerprint
 * @returns {Promise<string>} Audio fingerprint
 */
async function getAudioFingerprint() {
    try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        if (!AudioContext) return 'no-audio';
        
        const context = new AudioContext();
        const oscillator = context.createOscillator();
        const analyser = context.createAnalyser();
        const gainNode = context.createGain();
        const scriptProcessor = context.createScriptProcessor(4096, 1, 1);
        
        gainNode.gain.value = 0; // Mute
        oscillator.connect(analyser);
        analyser.connect(scriptProcessor);
        scriptProcessor.connect(gainNode);
        gainNode.connect(context.destination);
        
        oscillator.start(0);
        
        return new Promise((resolve) => {
            scriptProcessor.onaudioprocess = function(event) {
                const output = event.outputBuffer.getChannelData(0);
                let sum = 0;
                for (let i = 0; i < output.length; i++) {
                    sum += Math.abs(output[i]);
                }
                oscillator.stop();
                scriptProcessor.disconnect();
                analyser.disconnect();
                gainNode.disconnect();
                context.close();
                resolve(sum.toFixed(5));
            };
        });
    } catch (e) {
        return 'audio-error';
    }
}

// Export for use in forms
window.generateClientFingerprint = generateClientFingerprint;
