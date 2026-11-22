"""Model profile loading and dynamic local Ollama model auto-discovery."""
from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class ModelProfile:
    name: str
    model_id: str
    ollama_name: str
    param_size: str = "7B"
    context_budget: int = 16384
    max_output_tokens: int = 4096
    native_tools: bool = False
    structured_output: bool = True
    temperature: float = 0.2
    timeout_sec: int = 60
    max_retries: int = 3
    summarize_threshold_lines: int = 30


def _query_local_ollama_tags() -> List[Dict[str, str]]:
    """Query Ollama API to detect locally installed models."""
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    try:
        req = urllib.request.Request(f"{host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            for m in data.get("models", []):
                name = m.get("name", "")
                size_bytes = m.get("size", 0)
                size_str = f"{round(size_bytes / (1024**3), 1)}GB" if size_bytes else "?"
                results.append({"name": name, "size": size_str})
            return results
    except Exception:
        return []


def load_profiles(config_dir: str) -> Tuple[Dict[str, ModelProfile], str]:
    """Load model profiles from config/profiles.json and auto-detect installed Ollama models.

    Returns (profiles_dict, default_profile_name).
    """
    profiles_file = os.path.join(config_dir, "profiles.json")
    profiles: Dict[str, ModelProfile] = {}
    default_name = "qwen2.5-coder:7b"

    # 1. Load predefined profiles if config file exists
    if os.path.isfile(profiles_file):
        try:
            with open(profiles_file, encoding="utf-8") as fh:
                data = json.load(fh)
            default_name = data.get("default_profile", default_name)
            for name, pdata in data.get("profiles", {}).items():
                profiles[name] = ModelProfile(
                    name=name,
                    model_id=pdata.get("model_id", f"ollama/{name}"),
                    ollama_name=pdata.get("ollama_name", name),
                    param_size=pdata.get("param_size", "7B"),
                    context_budget=pdata.get("context_budget", 16384),
                    max_output_tokens=pdata.get("max_output_tokens", 4096),
                    native_tools=pdata.get("native_tools", False),
                    structured_output=pdata.get("structured_output", True),
                    temperature=pdata.get("temperature", 0.2),
                    timeout_sec=pdata.get("timeout_sec", 60),
                    max_retries=pdata.get("max_retries", 3),
                    summarize_threshold_lines=pdata.get("summarize_threshold_lines", 30),
                )
        except Exception:
            pass

    # 2. Auto-discover locally available models from Ollama (e.g. `ollama list`)
    local_ollama_models = _query_local_ollama_tags()
    for lm in local_ollama_models:
        mname = lm.get("name", "")
        if not mname:
            continue
        if mname not in profiles:
            profiles[mname] = ModelProfile(
                name=mname,
                model_id=f"ollama/{mname}",
                ollama_name=mname,
                param_size=lm.get("size", "Local"),
                context_budget=16384,
            )

    # 3. Determine active default profile
    if default_name not in profiles and profiles:
        default_name = next(iter(profiles.keys()))

    # Fallback when neither config nor ollama is reachable
    if not profiles:
        fallback_name = "qwen2.5-coder:7b"
        profiles[fallback_name] = ModelProfile(
            name=fallback_name,
            model_id="ollama/cyber",
            ollama_name="hf.co/bartowski/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF:Q4_K_M",
        )
        default_name = fallback_name

    return profiles, default_name
