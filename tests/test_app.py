"""Tests for Textual UI application mounting and keybindings."""
import pytest
from neocyber.app import NeoCyberApp
from neocyber.components.chat import ChatArea
from neocyber.components.input_area import InputArea
from neocyber.components.status_bar import StatusBar


@pytest.mark.asyncio
async def test_app_mount_and_toggle_agent():
    app = NeoCyberApp()
    async with app.run_test() as pilot:
        # Check initial widgets
        assert app.query_one(ChatArea) is not None
        assert app.query_one(InputArea) is not None
        assert app.query_one(StatusBar) is not None

        # Verify initial agent mode
        assert app.agent_mode == "cyber"
        assert app.query_one(StatusBar).agent_mode == "cyber"

        # Press Tab to toggle to plan mode
        await pilot.press("tab")
        assert app.agent_mode == "plan"
        assert app.query_one(StatusBar).agent_mode == "plan"

        # Press Tab again to toggle back to cyber
        await pilot.press("tab")
        assert app.agent_mode == "cyber"
        assert app.query_one(StatusBar).agent_mode == "cyber"


@pytest.mark.asyncio
async def test_app_direct_command():
    app = NeoCyberApp()
    async with app.run_test() as pilot:
        chat = app.query_one(ChatArea)
        # Directly invoke shell command via ! echo test
        app._execute_direct_command("echo test_run")
        await pilot.pause()
        # Ensure chat mounted tool card
        cards = chat.query("ToolExecutionCard")
        assert len(cards) > 0
