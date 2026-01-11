"""
Sandbox execution environment for running user-submitted agents safely.

This module provides a restricted Python execution environment that:
- Limits available builtins and imports
- Enforces time limits per step
- Prevents file system and network access
- Safely executes user code with proper error handling
"""
import ast
import time
import signal
from typing import Dict, Any, Callable, Optional, Tuple
from dataclasses import dataclass

from app.core.config import config
from app.challenges.base import BaseChallenge, ChallengeResult, ChallengeStatus


class SandboxSecurityError(Exception):
    """Raised when user code attempts forbidden operations"""
    pass


class SandboxTimeoutError(Exception):
    """Raised when execution exceeds time limit"""
    pass


@dataclass
class ValidationResult:
    """Result of code validation"""
    is_valid: bool
    error_message: Optional[str] = None
    forbidden_items: Optional[list] = None


class CodeValidator:
    """Validates user-submitted code for security issues"""
    
    # Forbidden imports
    FORBIDDEN_IMPORTS = {
        'os', 'sys', 'subprocess', 'socket', 'requests', 'urllib',
        'http', 'ftplib', 'telnetlib', 'asyncio', 'threading',
        'multiprocessing', '__builtin__', '__builtins__', 'builtins',
        'importlib', 'imp', 'pickle', 'shelve', 'marshal', 'eval',
        'exec', 'compile', 'open', 'file', 'input', 'raw_input'
    }
    
    # Forbidden builtin names
    FORBIDDEN_BUILTINS = {
        'eval', 'exec', 'compile', '__import__', 'open', 'file',
        'input', 'raw_input', 'execfile', 'reload', 'vars', 'dir',
        'globals', 'locals'
    }
    
    # Forbidden node types in AST
    FORBIDDEN_AST_NODES = {
        ast.Import,  # We'll check imports separately
        ast.ImportFrom,
    }
    
    def validate(self, code: str) -> ValidationResult:
        """
        Validate user code for security issues.
        
        Args:
            code: The Python code to validate
            
        Returns:
            ValidationResult indicating if code is safe
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Syntax error in code: {str(e)}"
            )
        
        # Check for forbidden constructs
        forbidden_items = []
        
        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.FORBIDDEN_IMPORTS:
                            forbidden_items.append(f"import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module in self.FORBIDDEN_IMPORTS:
                        forbidden_items.append(f"from {node.module} import ...")
            
            # Check for forbidden name usage
            if isinstance(node, ast.Name):
                if node.id in self.FORBIDDEN_BUILTINS:
                    forbidden_items.append(f"builtin '{node.id}'")
        
        # Check if act() function is defined
        has_act_function = any(
            isinstance(node, ast.FunctionDef) and node.name == 'act'
            for node in ast.walk(tree)
        )
        
        if not has_act_function:
            return ValidationResult(
                is_valid=False,
                error_message="Code must define an 'act(observation, memory)' function"
            )
        
        if forbidden_items:
            return ValidationResult(
                is_valid=False,
                error_message=f"Code contains forbidden items: {', '.join(set(forbidden_items))}",
                forbidden_items=forbidden_items
            )
        
        return ValidationResult(is_valid=True)


class SandboxRunner:
    """
    Executes user agents in a restricted sandbox environment.
    """
    
    # Whitelisted imports that agents can use
    ALLOWED_IMPORTS = {
        'json': __import__('json'),
        'math': __import__('math'),
        'random': __import__('random'),
        'dataclasses': __import__('dataclasses'),
        'typing': __import__('typing'),
    }
    
    # Safe builtins
    SAFE_BUILTINS = {
        'abs', 'all', 'any', 'bool', 'chr', 'dict', 'enumerate',
        'filter', 'float', 'int', 'isinstance', 'len', 'list',
        'map', 'max', 'min', 'ord', 'range', 'reversed', 'round',
        'set', 'sorted', 'str', 'sum', 'tuple', 'zip', 'True',
        'False', 'None', 'print'
    }
    
    def __init__(self):
        self.validator = CodeValidator()
    
    def _create_safe_globals(self) -> Dict[str, Any]:
        """Create a restricted global namespace for code execution"""
        safe_globals = {'__builtins__': {}}
        
        # Add safe builtins
        import builtins
        for name in self.SAFE_BUILTINS:
            if hasattr(builtins, name):
                safe_globals['__builtins__'][name] = getattr(builtins, name)
        
        # Add allowed imports
        safe_globals.update(self.ALLOWED_IMPORTS)
        
        return safe_globals
    
    def _execute_with_timeout(self, func: Callable, *args, timeout: float = None) -> Any:
        """
        Execute a function with a timeout.
        
        Args:
            func: Function to execute
            *args: Arguments to pass to function
            timeout: Timeout in seconds (defaults to config value)
            
        Returns:
            Result of function execution
            
        Raises:
            SandboxTimeoutError: If execution exceeds timeout
        """
        if timeout is None:
            timeout = config.MAX_EXECUTION_TIME_PER_STEP
        
        def timeout_handler(signum, frame):
            raise SandboxTimeoutError(f"Execution exceeded {timeout}s timeout")
        
        # Set up timeout (Unix-based systems)
        old_handler = signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout)
        
        try:
            result = func(*args)
            signal.setitimer(signal.ITIMER_REAL, 0)  # Cancel timer
            return result
        except SandboxTimeoutError:
            raise
        finally:
            signal.signal(signal.SIGALRM, old_handler)
    
    def load_agent(self, code: str) -> Tuple[bool, Optional[Callable], Optional[str]]:
        """
        Load and validate user agent code.
        
        Args:
            code: Python code containing act() function
            
        Returns:
            Tuple of (success, act_function, error_message)
        """
        # Validate code
        validation = self.validator.validate(code)
        if not validation.is_valid:
            return False, None, validation.error_message
        
        # Create safe execution environment
        safe_globals = self._create_safe_globals()
        
        try:
            # Execute code to define the act function
            exec(code, safe_globals)
            
            # Extract act function
            if 'act' not in safe_globals:
                return False, None, "Code did not define 'act' function"
            
            act_func = safe_globals['act']
            
            # Verify it's callable
            if not callable(act_func):
                return False, None, "'act' must be a function"
            
            return True, act_func, None
            
        except Exception as e:
            return False, None, f"Error loading agent: {str(e)}"
    
    def run_challenge(self, agent_code: str, challenge: BaseChallenge) -> ChallengeResult:
        """
        Run an agent against a challenge.
        
        Args:
            agent_code: The user's agent code
            challenge: The challenge instance to run
            
        Returns:
            ChallengeResult containing the outcome
        """
        # Load agent
        success, act_func, error = self.load_agent(agent_code)
        if not success:
            return challenge.get_result(
                status=ChallengeStatus.ERROR,
                error_message=f"Failed to load agent: {error}"
            )
        
        # Reset challenge
        try:
            observation = challenge.reset()
        except Exception as e:
            return challenge.get_result(
                status=ChallengeStatus.ERROR,
                error_message=f"Failed to reset challenge: {str(e)}"
            )
        
        # Initialize agent memory
        memory = {}
        
        # Run challenge loop
        for step in range(challenge.max_steps):
            challenge.current_step = step
            
            try:
                # Call agent's act function with timeout
                action, memory = self._execute_with_timeout(
                    act_func,
                    observation,
                    memory
                )
                
                # Validate action type
                if not isinstance(action, str):
                    return challenge.get_result(
                        status=ChallengeStatus.ERROR,
                        error_message=f"Agent returned non-string action: {type(action)}"
                    )
                
                # Validate action is allowed
                is_valid, error_msg = challenge.validate_action(action)
                if not is_valid:
                    return challenge.get_result(
                        status=ChallengeStatus.ERROR,
                        error_message=error_msg
                    )
                
            except SandboxTimeoutError as e:
                return challenge.get_result(
                    status=ChallengeStatus.TIMEOUT,
                    error_message=str(e)
                )
            except Exception as e:
                return challenge.get_result(
                    status=ChallengeStatus.ERROR,
                    error_message=f"Agent error at step {step}: {str(e)}"
                )
            
            # Execute action in challenge
            try:
                step_result = challenge.step(action)
                challenge.total_score += step_result.reward
                challenge.log_step(action, step_result)
                
                # Check if challenge is complete
                if step_result.done:
                    status = ChallengeStatus.SUCCESS if challenge.total_score > 0 else ChallengeStatus.FAILURE
                    return challenge.get_result(status=status)
                
                # Update observation for next step
                observation = step_result.observation
                
            except Exception as e:
                return challenge.get_result(
                    status=ChallengeStatus.ERROR,
                    error_message=f"Challenge error at step {step}: {str(e)}"
                )
        
        # Max steps reached
        return challenge.get_result(status=ChallengeStatus.TIMEOUT)
