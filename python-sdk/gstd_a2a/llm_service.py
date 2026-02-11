import requests
import json
import os
from .constants import SOVEREIGN_MODELS, DEFAULT_MODEL

class LLMService:
    """Sovereign LLM service — routes to local Ollama or GSTD Gateway."""

    def __init__(self, api_url=None):
        self.api_url = api_url or os.getenv("OLLAMA_URL", "http://ollama:11434")

    def _resolve_model(self, model: str) -> str:
        """Resolve sovereign alias (gstd-fast) to engine ID, or pass through."""
        return SOVEREIGN_MODELS.get(model, model)

    def generate(self, prompt, model=DEFAULT_MODEL, system_prompt=None):
        """Generates a response using the local Ollama instance."""
        engine_model = self._resolve_model(model)
        url = f"{self.api_url}/api/generate"
        payload = {
            "model": engine_model,
            "prompt": prompt,
            "stream": False
        }
        if system_prompt:
            payload["system"] = system_prompt
            
        try:
            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("response")
            return f"Error: {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"Error connecting to Ollama: {str(e)}"

    def chat(self, messages, model=DEFAULT_MODEL):
        """Chat completion using local Ollama."""
        engine_model = self._resolve_model(model)
        url = f"{self.api_url}/api/chat"
        payload = {
            "model": engine_model,
            "messages": messages,
            "stream": False
        }
        try:
            resp = requests.post(url, json=payload, timeout=120)
            if resp.status_code == 200:
                return resp.json().get("message", {}).get("content")
            return f"Error: {resp.status_code} - {resp.text}"
        except Exception as e:
            return f"Error connecting to Ollama: {str(e)}"
