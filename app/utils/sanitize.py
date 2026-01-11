"""Output sanitization utilities for XSS prevention"""
import html
import re
from typing import Optional


def sanitize_html(text: Optional[str]) -> str:
    """
    Sanitize text for safe HTML rendering.
    Escapes HTML special characters to prevent XSS.
    
    Args:
        text: Text that may contain HTML/script tags
        
    Returns:
        Escaped text safe for HTML rendering
    """
    if not text:
        return ""
    
    return html.escape(str(text))


def sanitize_llm_output(text: Optional[str]) -> str:
    """
    Sanitize LLM output for safe display.
    
    - Escapes HTML special characters
    - Removes potential script injections
    - Preserves safe formatting (newlines, spaces)
    
    Args:
        text: Raw LLM output
        
    Returns:
        Sanitized text safe for rendering
    """
    if not text:
        return ""
    
    text = str(text)
    
    # First, escape HTML entities
    text = html.escape(text)
    
    # Convert newlines to <br> for display (after escaping)
    # This is safe because we've already escaped everything
    text = text.replace('\n', '<br>')
    
    return text


def sanitize_for_json(text: Optional[str]) -> str:
    """
    Sanitize text for safe JSON embedding.
    
    Args:
        text: Text to embed in JSON
        
    Returns:
        Text safe for JSON strings
    """
    if not text:
        return ""
    
    text = str(text)
    
    # Escape characters that could break JSON or cause XSS when parsed
    replacements = {
        '\\': '\\\\',
        '"': '\\"',
        '\n': '\\n',
        '\r': '\\r',
        '\t': '\\t',
        '<': '\\u003c',  # Prevent </script> breaking out
        '>': '\\u003e',
        '&': '\\u0026',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def strip_dangerous_patterns(text: Optional[str]) -> str:
    """
    Remove potentially dangerous patterns from text.
    Use as additional layer on top of HTML escaping.
    
    Args:
        text: Text to clean
        
    Returns:
        Text with dangerous patterns removed
    """
    if not text:
        return ""
    
    text = str(text)
    
    # Remove script tags and their content (case insensitive)
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    
    # Remove event handlers
    text = re.sub(r'\s+on\w+\s*=\s*["\'][^"\']*["\']', '', text, flags=re.IGNORECASE)
    
    # Remove javascript: URLs
    text = re.sub(r'javascript\s*:', '', text, flags=re.IGNORECASE)
    
    # Remove data: URLs (can contain scripts)
    text = re.sub(r'data\s*:', 'data-blocked:', text, flags=re.IGNORECASE)
    
    return text
