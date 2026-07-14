"""Local GGUF and Ollama inference runner for the Matemium Offline Agent (v3)."""

from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

# Global cache for the in-process llama-cpp model instance to prevent double load
_LLAMA_CPP_MODEL: Any = None


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
        model_name = "qwen2.5-coder:7b-instruct"
        if self.model_path:
            filename = self.model_path.name.lower()
            if "3b" in filename:
                model_name = "qwen2.5-coder:3b-instruct"
            elif "llama" in filename or "8b" in filename:
                model_name = "llama3:8b-instruct"

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "options": {
                "temperature": 0.1,  # Low temperature for highly deterministic math/coding
                "num_ctx": 8192,     # Generous context window for code retrieval injection
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
        model_name = "qwen2.5-coder:7b-instruct"
        if self.model_path:
            filename = self.model_path.name.lower()
            if "3b" in filename:
                model_name = "qwen2.5-coder:3b-instruct"
            elif "llama" in filename or "8b" in filename:
                model_name = "llama3:8b-instruct"

        payload = {
            "model": model_name,
            "messages": messages,
            "options": {
                "temperature": 0.1,
                "num_ctx": 8192,
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

    def _generate_via_llama_cpp(self, system_prompt: str, user_prompt: str, *, grammar: str | None = None) -> str:
        """Load and run GGUF in-process using llama-cpp-python."""
        global _LLAMA_CPP_MODEL

        if not self.model_path or not self.model_path.is_file():
            raise FileNotFoundError(
                f"Local GGUF model path not found or invalid: {self.model_path}. "
                "Ensure the model is fully downloaded via Settings."
            )

        # Lazy loading llama-cpp-python to keep startup fast and avoid compilation blocks
        try:
            from llama_cpp import Llama
        except ImportError:
            raise ImportError(
                "The 'llama-cpp-python' library is not installed in the sidecar venv. "
                "Ensure local dependencies are fully configured."
            )

        # Cache the in-process model to avoid painful disk load latency on every request
        if _LLAMA_CPP_MODEL is None:
            # Auto-detect offloading: use GPU (n_gpu_layers=-1) if CUDA/Metal is available
            _LLAMA_CPP_MODEL = Llama(
                model_path=str(self.model_path),
                n_ctx=8192,
                n_gpu_layers=-1,  # -1 means auto-offload all layers to GPU if possible
                verbose=False
            )

        # Construct simple chat template payload for local instruct models
        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
        
        # Compile GBNF grammar if requested and supported
        llama_grammar = None
        if grammar:
            try:
                from llama_cpp import LlamaGrammar
                llama_grammar = LlamaGrammar.from_string(grammar)
                print(f"[Local Runner] successfully compiled GBNF grammar constraint.")
            except Exception as e:
                print(f"[Local Runner Warning] Failed to compile GBNF grammar, falling back to unconstrained: {e}")

        try:
            kwargs = {
                "max_tokens": 2048,
                "temperature": 0.1,
                "stop": ["<|im_end|>", "<|im_start|>", "system", "user", "assistant", "###"],
                "echo": False
            }
            if llama_grammar is not None:
                kwargs["grammar"] = llama_grammar

            output = _LLAMA_CPP_MODEL(prompt, **kwargs)
            return str(output["choices"][0]["text"])
        except Exception as e:
            raise RuntimeError(f"Direct GGUF llama-cpp generation failed: {e}")

    def generate(self, system_prompt: str, user_prompt: str, *, grammar: str | None = None) -> str:
        """Unified entrypoint: routes automatically to Ollama service (if running) or bundles llama-cpp."""
        if self.is_ollama_running():
            # If JSON grammar is requested, format the Ollama payload with format='json'
            return self._generate_via_ollama(system_prompt, user_prompt)
        return self._generate_via_llama_cpp(system_prompt, user_prompt, grammar=grammar)
