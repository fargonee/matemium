"""Local GGUF and Ollama inference runner for the Matemium Offline Agent (v3)."""

from __future__ import annotations

import json
import os
import gc
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

# Global cache for the in-process llama-cpp model instance to prevent double load
_LLAMA_CPP_MODEL: Any = None
_LLAMA_CPP_MODEL_PATH: str | None = None


def unload_cached_model() -> None:
    """Release an in-process GGUF before changing models or context sizing."""
    global _LLAMA_CPP_MODEL, _LLAMA_CPP_MODEL_PATH
    _LLAMA_CPP_MODEL = None
    _LLAMA_CPP_MODEL_PATH = None
    from .llm_worker import shutdown_worker

    shutdown_worker()
    gc.collect()


class LocalInferenceRunner:
    """Orchestrates local/offline LLM generation using Ollama or in-process llama-cpp."""

    def __init__(self, model_path: str | Path | None = None):
        # Resolve model path from parameter, env, or default XDG location
        if model_path is None:
            model_path = os.environ.get("MATEMIUM_LOCAL_LLM_MODEL_PATH", "")

        # Self-healing fallback: auto-detect settings.json and assets.json from local app data on all OSes
        if not model_path:
            import sys
            data_root = None
            if sys.platform.startswith("win"):
                appdata = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
                if appdata:
                    data_root = Path(appdata) / "matemium"
            elif sys.platform.startswith("darwin"):
                data_root = Path.home() / "Library" / "Application Support" / "matemium"
            else:
                data_home = os.environ.get("XDG_DATA_HOME")
                if data_home:
                    data_root = Path(data_home) / "matemium"
                else:
                    data_root = Path.home() / ".local" / "share" / "matemium"

            if data_root:
                settings_path = data_root / "settings.json"
                assets_path = data_root / "assets" / "assets.json"
                
                local_model_id = "llm-qwen-coder-3b-q4"
                if settings_path.is_file():
                    try:
                        with open(settings_path, "r", encoding="utf-8") as f:
                            settings = json.load(f)
                            local_model_id = settings.get("localLlmModel") or settings.get("local_llm_model") or local_model_id
                    except Exception:
                        pass
                
                if assets_path.is_file():
                    try:
                        with open(assets_path, "r", encoding="utf-8") as f:
                            assets_state = json.load(f)
                            for asset in assets_state.get("assets", []):
                                if asset.get("id") == local_model_id:
                                    if asset.get("verified") and asset.get("path"):
                                        model_path = asset.get("path")
                                        break
                    except Exception:
                        pass
        
        self.model_path = Path(model_path) if model_path else None
        self.ollama_url = "http://localhost:11434/api/chat"

    @property
    def model_name(self) -> str:
        """Model identifier shared by local chat and native agent transports."""
        if not self.model_path:
            return "qwen2.5-coder:7b-instruct"
        filename = self.model_path.name.lower()
        if "3b" in filename:
            return "qwen2.5-coder:3b-instruct"
        if "llama" in filename or "8b" in filename:
            return "llama3:8b-instruct"
        return "qwen2.5-coder:7b-instruct"

    @property
    def context_window(self) -> int:
        """Choose a context that fits the selected quantized model in memory.

        The larger 7B/8B models do not need a 32K KV cache for ordinary local
        chat turns. Keeping them at 18K prevents a multi-gigabyte allocation
        spike on typical 16 GB PCs while leaving room for code context.
        """
        override = os.environ.get("MATEMIUM_LOCAL_LLM_CONTEXT_SIZE", "").strip()
        if override:
            try:
                return max(18432, min(32768, int(override)))
            except ValueError:
                pass
        filename = self.model_path.name.lower() if self.model_path else self.model_name.lower()
        if "7b" in filename or "8b" in filename or "llama" in filename:
            return 18432
        return 32768

    def is_ollama_running(self) -> bool:
        """Check if Ollama service is reachable on localhost:11434."""
        try:
            # Send a quick check to Ollama version endpoint
            req = urllib.request.Request(
                "http://localhost:11434/api/version",
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, Exception):
            pass
        return False

    def _generate_via_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """Send chat completion request to local Ollama API."""
        # Detect model from filename or use standard fallback qwen2.5-coder
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "options": {
                "temperature": 0.1,  # Low temperature for highly deterministic math/coding
                "num_ctx": self.context_window,
            },
            "stream": False
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.ollama_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=90.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return str(result["message"]["content"])
        except Exception as e:
            raise RuntimeError(f"Ollama generation request failed: {e}")

    def _generate_via_ollama_messages(self, messages: list[dict[str, str]]) -> str:
        """Send chat completion request with custom conversation history to local Ollama API."""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "options": {
                "temperature": 0.1,
                "num_ctx": self.context_window,
            },
            "stream": False
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.ollama_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=90.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return str(result["message"]["content"])
        except Exception as e:
            raise RuntimeError(f"Ollama generation request failed: {e}")

    def _generate_via_ollama_schema(
        self, system_prompt: str, user_prompt: str, schema: dict[str, Any]
    ) -> str:
        """Use Ollama's JSON-schema output constraint for the v2 protocol."""
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": schema,
            "options": {"temperature": 0.1, "num_ctx": self.context_window},
            "stream": False,
        }
        req = urllib.request.Request(
            self.ollama_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90.0) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return str(result["message"]["content"])
        except Exception as e:
            raise RuntimeError(f"Ollama structured generation request failed: {e}")

    def _generate_via_llama_cpp(self, system_prompt: str, user_prompt: str, *, grammar: str | None = None) -> str:
        """Load and run GGUF in-process using llama-cpp-python."""
        if not self.model_path or not self.model_path.is_file():
            raise FileNotFoundError(
                f"Local GGUF model path not found or invalid: {self.model_path}. "
                "Ensure the model is fully downloaded via Settings."
            )

        from .llm_worker import generate_in_worker

        return generate_in_worker(
            model_path=self.model_path,
            context_window=self.context_window,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            grammar=grammar,
        )

    def generate(self, system_prompt: str, user_prompt: str, *, grammar: str | None = None) -> str:
        """Unified entrypoint: routes automatically to Ollama service (if running) or bundles llama-cpp."""
        if self.is_ollama_running():
            # If JSON grammar is requested, format the Ollama payload with format='json'
            return self._generate_via_ollama(system_prompt, user_prompt)
        return self._generate_via_llama_cpp(system_prompt, user_prompt, grammar=grammar)

    def generate_structured_agent(self, request: Any, *, max_repairs: int = 1) -> Any:
        """Run the Phase 2 local adapter with the same protocol as cloud models."""
        from .model_gateway import LocalStructuredModelGateway

        def transport(prompt: str, schema: dict[str, Any], grammar: str) -> str:
            schema_prompt = (
                "You are the structured model component of Matemium's agent runtime. "
                "Your output is constrained to JSON and will be validated against this schema:\n"
                f"{json.dumps(schema, ensure_ascii=False)}"
            )
            if self.is_ollama_running():
                return self._generate_via_ollama_schema(schema_prompt, prompt, schema)
            return self._generate_via_llama_cpp(schema_prompt, prompt, grammar=grammar)

        return LocalStructuredModelGateway(transport, max_repairs=max_repairs).complete(request)
