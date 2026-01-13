"""
Ollama client wrapper for local LLM inference.
Uses uncensored models (dolphin-mistral) for red team attack generation.
"""
import subprocess
from typing import Optional
from dataclasses import dataclass


@dataclass
class OllamaResponse:
    content: str
    model: str
    tokens_used: int


class OllamaClient:
    """Local LLM client using Ollama for uncensored generation"""
    
    DEFAULT_MODEL = "dolphin-mistral"
    FALLBACK_MODELS = ["mistral", "llama2"]
    
    def __init__(self, model: str = None):
        self.model = model or self.DEFAULT_MODEL
        self._ollama_lib = None
        self._verify_installation()
    
    def _verify_installation(self):
        """Check Ollama is installed and model is available"""
        try:
            result = subprocess.run(
                ["ollama", "list"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise RuntimeError(f"Ollama error: {result.stderr}")
            
            if self.model not in result.stdout:
                print(f"⚠️  Model {self.model} not found locally.")
                print(f"   Run: ollama pull {self.model}")
                
                # Try fallback models
                for fallback in self.FALLBACK_MODELS:
                    if fallback in result.stdout:
                        print(f"   Using fallback: {fallback}")
                        self.model = fallback
                        return
                
                raise RuntimeError(
                    f"Model {self.model} not available. "
                    f"Run: ollama pull {self.model}"
                )
                
        except FileNotFoundError:
            raise RuntimeError(
                "Ollama not installed.\n"
                "Install with: brew install ollama\n"
                "Then run: ollama serve"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Ollama not responding. Run: ollama serve")
    
    def _get_ollama_lib(self):
        """Lazy load ollama library"""
        if self._ollama_lib is None:
            try:
                import ollama
                self._ollama_lib = ollama
            except ImportError:
                self._ollama_lib = False
        return self._ollama_lib
    
    def generate(
        self, 
        prompt: str, 
        system: str = None,
        temperature: float = 0.9,
        max_tokens: int = 2000,
        verbose: bool = True,
        json_mode: bool = False
    ) -> OllamaResponse:
        """Generate completion using local model"""
        
        if verbose:
            print(f"   🧠 Calling {self.model}...")
            print(f"   📝 Prompt length: {len(prompt)} chars")
        
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        ollama_lib = self._get_ollama_lib()
        
        import time
        start_time = time.time()
        
        if ollama_lib:
            # Use ollama Python library
            if verbose:
                mode_str = " (JSON mode)" if json_mode else ""
                print(f"   ⏳ Generating{mode_str} (30-90 seconds)...", flush=True)
            
            chat_kwargs = {
                "model": self.model,
                "messages": messages,
                "options": {
                    "temperature": temperature, 
                    "num_predict": max_tokens
                }
            }
            
            # Add JSON format enforcement
            if json_mode:
                chat_kwargs["format"] = "json"
            
            response = ollama_lib.chat(**chat_kwargs)
            
            elapsed = time.time() - start_time
            if verbose:
                print(f"   ✅ Response received in {elapsed:.1f}s")
                print(f"   📊 Tokens: {response.get('eval_count', 'N/A')}")
            
            return OllamaResponse(
                content=response['message']['content'],
                model=self.model,
                tokens_used=response.get('eval_count', 0)
            )
        else:
            # Fallback to HTTP API
            import requests
            if verbose:
                mode_str = " (JSON mode)" if json_mode else ""
                print(f"   ⏳ Generating via HTTP{mode_str} (30-90 seconds)...", flush=True)
            
            request_json = {
                "model": self.model, 
                "messages": messages, 
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            if json_mode:
                request_json["format"] = "json"
            
            try:
                resp = requests.post(
                    "http://localhost:11434/api/chat",
                    json=request_json,
                    timeout=180
                )
                resp.raise_for_status()
                data = resp.json()
                
                elapsed = time.time() - start_time
                if verbose:
                    print(f"   ✅ Response received in {elapsed:.1f}s")
                
                return OllamaResponse(
                    content=data['message']['content'],
                    model=self.model,
                    tokens_used=data.get('eval_count', 0)
                )
            except requests.exceptions.ConnectionError:
                raise RuntimeError(
                    "Cannot connect to Ollama. "
                    "Make sure it's running: ollama serve"
                )


def check_ollama_ready(model: str = "dolphin-mistral") -> bool:
    """Quick check if Ollama is ready for red team generation"""
    try:
        client = OllamaClient(model)
        response = client.generate(
            prompt="Say 'ready' if you can help with security testing.",
            temperature=0.1,
            max_tokens=50
        )
        return "ready" in response.content.lower()
    except Exception as e:
        print(f"❌ Ollama not ready: {e}")
        return False


if __name__ == "__main__":
    # Quick test
    print("🔴 Testing Ollama client...")
    
    if check_ollama_ready():
        print("✅ Ollama ready for red team generation")
        
        client = OllamaClient()
        response = client.generate(
            prompt="Generate one prompt injection attack to bypass a keyword filter.",
            system="You are a security researcher. Be direct and creative.",
            temperature=0.9
        )
        print(f"\nTest attack:\n{response.content[:500]}")
    else:
        print("❌ Ollama not ready. Setup instructions:")
        print("   1. brew install ollama")
        print("   2. ollama serve")
        print("   3. ollama pull dolphin-mistral")
