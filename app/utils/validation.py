"""Input validation utilities"""
import re
from typing import Optional, Tuple


# Username constraints
USERNAME_MIN_LENGTH = 2
USERNAME_MAX_LENGTH = 30
USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

# Reserved usernames that shouldn't be allowed
RESERVED_USERNAMES = {
    'admin', 'administrator', 'system', 'root', 'mod', 'moderator',
    'jankyard', 'anonymous', 'null', 'undefined', 'api', 'www'
}


def validate_username(username: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate a username for safety and format.
    
    Args:
        username: The username to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        If valid, error_message is None
    """
    if not username:
        return True, None  # Empty is allowed (will use generated name)
    
    username = username.strip()
    
    # Length check
    if len(username) < USERNAME_MIN_LENGTH:
        return False, f"Username must be at least {USERNAME_MIN_LENGTH} characters"
    
    if len(username) > USERNAME_MAX_LENGTH:
        return False, f"Username must be at most {USERNAME_MAX_LENGTH} characters"
    
    # Pattern check (alphanumeric, underscore, hyphen only)
    if not USERNAME_PATTERN.match(username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    
    # Reserved names check
    if username.lower() in RESERVED_USERNAMES:
        return False, "This username is reserved"
    
    # No leading/trailing special chars
    if username.startswith(('-', '_')) or username.endswith(('-', '_')):
        return False, "Username cannot start or end with special characters"
    
    return True, None


def sanitize_username(username: Optional[str]) -> Optional[str]:
    """
    Sanitize a username by stripping and normalizing.
    Returns None if username is empty after sanitization.
    """
    if not username:
        return None
    
    username = username.strip()
    if not username:
        return None
    
    return username


def validate_and_sanitize_username(username: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """
    Validate and sanitize a username in one call.
    
    Returns:
        Tuple of (sanitized_username, error_message)
        If there's an error, sanitized_username is None
        If username was empty/None, returns (None, None) - use generated name
    """
    sanitized = sanitize_username(username)
    
    if not sanitized:
        return None, None  # Will use generated name
    
    is_valid, error = validate_username(sanitized)
    if not is_valid:
        return None, error
    
    return sanitized, None
