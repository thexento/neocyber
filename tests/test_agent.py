"""Behavioral tests for the iterative harness, independent of Ollama."""
import pytest

from neocyber.engine.agent import AgentRunner
from neocyber.models.profile import ModelProfile


class ScriptedOllama:
    def __init__(self, replies):
        self.replies = iter(replies)

    async def stream_chat(self, model, messages, temperature):
        for token in next(self.replies):
            yield token


def profile():
    return ModelProfile(name="test", model_id="ollama/test", ollama_name="test")


@pytest.mark.asyncio
async def test_simple_conversation_does_not_run_commands(tmp_path):
    runner = AgentRunner(str(tmp_path), ScriptedOllama([["Hello! How can I help?"]]))
    final, events, _ = await runner.run_task("cyber", profile(), [], "Hello.", lambda _event: None)
    assert final == "Hello! How can I help?"
    assert not [event for event in events if event.type == "command"]


@pytest.mark.asyncio
async def test_duplicate_command_is_not_executed_twice(tmp_path):
    runner = AgentRunner(str(tmp_path), ScriptedOllama([
        ["```bash\nprintf first\n```"],
        ["```bash\nprintf first\n```"],
    ]))
    final, events, state = await runner.run_task("cyber", profile(), [], "inspect", lambda _event: None)
    commands = [event for event in events if event.type == "command"]
    assert len(commands) == 1
    assert any(event.summary == "Skipped duplicate command" for event in events)
    assert "duplicates" in final


@pytest.mark.asyncio
async def test_real_result_reaches_next_decision(tmp_path):
    runner = AgentRunner(str(tmp_path), ScriptedOllama([
        ["```bash\nprintf observed-value\n```"],
        ["Verified the command returned observed-value."],
    ]))
    final, events, state = await runner.run_task("cyber", profile(), [], "verify", lambda _event: None)
    assert "observed-value" in state.observations[0]
    assert "Verified" in final


@pytest.mark.asyncio
async def test_live_word_by_word_token_streaming(tmp_path):
    streamed_tokens = []
    def on_token(tok):
        streamed_tokens.append(tok)

    runner = AgentRunner(str(tmp_path), ScriptedOllama([
        ["Identifying", " your", " device", " and", " OS", "..."]
    ]))
    final, events, _ = await runner.run_task("cyber", profile(), [], "check os", on_token=on_token)
    assert final == "Identifying your device and OS..."
    assert streamed_tokens == ["Identifying", " your", " device", " and", " OS", "..."]
