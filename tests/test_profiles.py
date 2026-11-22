"""Tests for model profiles loading."""
import os
import tempfile
import pytest

from neocyber.models.profile import load_profiles


def test_load_profiles():
    # Test loading from project config
    profiles, default_name = load_profiles("config")
    assert "qwen2.5-coder:7b" in profiles
    assert default_name == "qwen2.5-coder:7b"

    p = profiles["qwen2.5-coder:7b"]
    assert p.param_size == "7B"
    assert p.context_budget == 16384
    assert p.native_tools is True


def test_load_profiles_fallback():
    with tempfile.TemporaryDirectory() as empty_dir:
        profiles, default_name = load_profiles(empty_dir)
        assert "qwen2.5-coder:7b" in profiles
        assert default_name == "qwen2.5-coder:7b"
