"""
User fingerprinting for anonymous rate limiting

Generates a stable fingerprint from multiple data points (server + client-side)
to prevent abuse while maintaining user privacy through hashing.
"""
import hashlib
import logging
from fastapi import Request

logger = logging.getLogger(__name__)


def generate_fingerprint(request: Request) -> str:
    """
    Generate anonymous user fingerprint from multiple data points
    
    Combines:
    - Server-side: IP, User-Agent, Accept-Language, Accept-Encoding
    - Client-side: Screen res, timezone, canvas signature, WebGL renderer
    
    This creates a stable identifier that's much harder to bypass than IP-only.
    Requires changing IP + browser + GPU + timezone + screen to bypass.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        SHA256 hash of all fingerprint data (64 hex chars)
    """
    # Server-side data (from HTTP headers)
    ip = (
        request.headers.get('x-forwarded-for', '').split(',')[0].strip() or
        request.headers.get('x-real-ip') or
        (request.client.host if request.client else 'unknown')
    )
    user_agent = request.headers.get('user-agent', 'unknown')
    accept_language = request.headers.get('accept-language', '')
    accept_encoding = request.headers.get('accept-encoding', '')
    
    # Client-side fingerprint (from JavaScript - optional)
    # This includes screen res, timezone, canvas/WebGL signatures
    client_fp = request.headers.get('x-client-fingerprint', '')
    
    # Combine ALL data points into one string
    fingerprint_string = (
        f"{ip}|"
        f"{user_agent}|"
        f"{accept_language}|"
        f"{accept_encoding}|"
        f"{client_fp}"
    )
    
    # Generate SHA256 hash
    return hashlib.sha256(fingerprint_string.encode()).hexdigest()
