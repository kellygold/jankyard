"""
Enhanced Challenge Registry with Auto-Discovery

Automatically discovers and registers all challenge classes in the challenges/ directory.
No manual imports needed - just drop in a new challenge file and it's registered!
"""
import os
import importlib
import inspect
from pathlib import Path
from typing import Dict, Type, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ChallengeRegistry:
    """
    Registry for challenge classes with auto-discovery
    
    Usage:
        1. Decorate your challenge with @ChallengeRegistry.register (optional)
        2. Or just inherit from BaseChallenge - auto-discovered!
        3. Access via ChallengeRegistry.get('challenge_name')
    """
    
    _challenges: Dict[str, Type] = {}
    _auto_discovered = False
    
    @classmethod
    def register(cls, challenge_class: Type):
        """
        Decorator to explicitly register a challenge
        
        Usage:
            @ChallengeRegistry.register
            class MyChallenge(BaseChallenge):
                ...
        """
        # Get challenge name from class
        if hasattr(challenge_class, 'name'):
            # Use the name property if available
            try:
                temp_instance = challenge_class()
                name = temp_instance.name
            except Exception:
                # Fallback to class name if instantiation fails
                name = challenge_class.__name__.replace('Challenge', '').lower()
        else:
            name = challenge_class.__name__.replace('Challenge', '').lower()
        
        cls._challenges[name] = challenge_class
        logger.debug(f"Registered challenge: {name} -> {challenge_class.__name__}")
        return challenge_class
    
    @classmethod
    def auto_discover(cls):
        """
        Auto-discover and register all challenges in the challenges/ directory
        
        Scans for all .py files (except those starting with _) and finds classes
        that inherit from BaseChallenge.
        """
        if cls._auto_discovered:
            return
        
        # Import BaseChallenge to check inheritance
        from app.challenges.base import BaseChallenge
        
        # Get challenges directory
        challenges_dir = Path(__file__).parent
        
        logger.info("🔍 Auto-discovering challenges...")
        discovered_count = 0
        
        # Scan all Python files
        for filepath in sorted(challenges_dir.iterdir()):
            if filepath.is_dir() and not (filepath / '__init__.py').exists():
                continue
            if filepath.is_file() and filepath.suffix != '.py':
                continue
            # Skip special files
            if filepath.stem.startswith('_') or filepath.stem in ['base', 'registry', 'prompt_game']:
                continue
            
            try:
                # Import the module
                module_name = f'app.challenges.{filepath.stem}'
                module = importlib.import_module(module_name)
                
                # Find all classes in the module
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if it's a Challenge class (inherits from BaseChallenge but not BaseChallenge itself)
                    if (issubclass(obj, BaseChallenge) and 
                        obj != BaseChallenge and
                        not name.startswith('_') and not inspect.isabstract(obj) and
                        obj.__module__.startswith(module_name)):
                        
                        # Get challenge name
                        try:
                            temp_instance = obj()
                            challenge_name = temp_instance.name
                        except Exception as e:
                            # Fallback: derive from filename
                            challenge_name = filepath.stem
                            logger.warning(f"Could not instantiate {name} to get name, using filename: {challenge_name}")
                        
                        # Register if not already registered
                        if challenge_name not in cls._challenges:
                            cls._challenges[challenge_name] = obj
                            discovered_count += 1
                            logger.info(f"  ✅ Discovered: {challenge_name} ({obj.__name__})")
            
            except Exception as e:
                logger.error(f"  ❌ Failed to import {filepath.stem}: {e}")
        
        cls._auto_discovered = True
        logger.info(f"🎉 Auto-discovery complete! Registered {discovered_count} challenges")
    
    @classmethod
    def get(cls, name: str) -> Optional[Type]:
        """
        Get a challenge class by name
        
        Args:
            name: Challenge name (e.g., 'glitch', 'arena')
            
        Returns:
            Challenge class or None if not found
        """
        if not cls._auto_discovered:
            cls.auto_discover()
        
        return cls._challenges.get(name)
    
    @classmethod
    def get_challenge(cls, name: str, config: Optional[Dict[str, Any]] = None):
        """
        Get a challenge instance by name
        
        Args:
            name: Challenge name
            config: Optional configuration dictionary
            
        Returns:
            Challenge instance or None if not found
        """
        challenge_class = cls.get(name)
        if challenge_class:
            return challenge_class(config)
        return None
    
    @classmethod
    def get_all(cls) -> Dict[str, Type]:
        """
        Get all registered challenges
        
        Returns:
            Dictionary mapping challenge names to classes
        """
        if not cls._auto_discovered:
            cls.auto_discover()
        
        return cls._challenges.copy()
    
    @classmethod
    def list_challenges(cls, include_hidden=False):
        """
        List all challenges with metadata
        
        Args:
            include_hidden: If True, include hidden challenges (default: False)
        
        Returns:
            List of dicts with challenge metadata
        """
        if not cls._auto_discovered:
            cls.auto_discover()
        
        challenges = []
        for name, challenge_class in cls._challenges.items():
            try:
                temp = challenge_class()
                # Skip hidden challenges unless explicitly requested
                if not include_hidden and getattr(temp, 'hidden', False):
                    continue
                challenges.append({
                    "name": temp.name,
                    "display_name": temp.display_name,
                    "description": temp.description,
                    "max_steps": temp.max_steps
                })
            except Exception as e:
                logger.error(f"Error listing challenge {name}: {e}")
        
        return challenges
    
    @classmethod
    def exists(cls, name: str) -> bool:
        """Check if a challenge is registered"""
        if not cls._auto_discovered:
            cls.auto_discover()
        
        return name in cls._challenges
    
    @classmethod
    def clear(cls):
        """Clear all registered challenges (useful for testing)"""
        cls._challenges = {}
        cls._auto_discovered = False
