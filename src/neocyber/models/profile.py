"""Model profile loading from config/profiles.json."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Tuple


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


_DEFAULT_PROFILE_NAME = "qwen2.5-coder:7b"
_DEFAULT_OLLAMA_NAME = (
    "hf.co/bartowski/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF:Q4_K_M"
)


def load_profiles(config_dir: str) -> Tuple[Dict[str, ModelProfile], str]:
    """Load model profiles from *config_dir*/profiles.json.

    Returns (profiles_dict, default_profile_name).
    """
    profiles_file = os.path.join(config_dir, "profiles.json")
    profiles: Dict[str, ModelProfile] = {}
    default_name = _DEFAULT_PROFILE_NAME

    if os.path.isfile(profiles_file):
        with open(profiles_file, encoding="utf-8") as fh:
            data = json.load(fh)
        default_name = data.get("default_profile", default_name)
        for name, pdata in data.get("profiles", {}).items():
            profiles[name] = ModelProfile(
                name=name,
                model_id=pdata.get("model_id", f"ollama/{name}"),
                ollama_name=pdata.get("ollama_name", name),
                param_size=pdata.get("param_size", "?"),
                context_budget=pdata.get("context_budget", 16384),
                max_output_tokens=pdata.get("max_output_tokens", 4096),
                native_tools=pdata.get("native_tools", False),
                structured_output=pdata.get("structured_output", True),
                temperature=pdata.get("temperature", 0.2),
                timeout_sec=pdata.get("timeout_sec", 60),
                max_retries=pdata.get("max_retries", 3),
                summarize_threshold_lines=pdata.get(
                    "summarize_threshold_lines", 30
                ),
            )

    # Fallback when no profiles file exists
    if not profiles:
        profiles[default_name] = ModelProfile(
            name=default_name,
            model_id="ollama/cyber",
            ollama_name=_DEFAULT_OLLAMA_NAME,
        )

    return profiles, default_name
