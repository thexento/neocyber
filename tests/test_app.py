"""Tests for Textual UI application mounting, keybindings, and prompt submission."""
import pytest
from neocyber.app import NeoCyberApp
from neocyber.components.chat import ChatArea
from neocyber.components.input_area import InputArea, PromptTextArea
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
async def test_app_prompt_submission_on_enter():
    app = NeoCyberApp()
    async with app.run_test() as pilot:
        textarea = app.query_one("#prompt-textarea", PromptTextArea)
        textarea.text = "test security scan"

        # Press Enter without Shift -> should submit
        await pilot.press("enter")
        await pilot.pause()

        # Textarea should be cleared upon submission
        assert textarea.text == ""

        # Chat area should contain user message
        chat = app.query_one(ChatArea)
        user_msgs = [m for m in chat.query("MessageView") if m.role.value == "user"]
        assert len(user_msgs) > 0
        assert any("test security scan" in m.initial_content for m in user_msgs)


@pytest.mark.asyncio
async def test_app_shift_enter_inserts_newline():
    app = NeoCyberApp()
    async with app.run_test() as pilot:
        textarea = app.query_one("#prompt-textarea", PromptTextArea)
        textarea.text = "first line"
        textarea.cursor_location = (0, len("first line"))

        # Press Shift+Enter -> should insert newline, not submit
        await pilot.press("shift+enter")
        await pilot.pause()

        assert "\n" in textarea.text


@pytest.mark.asyncio
async def test_app_command_palette_model_switch():
    app = NeoCyberApp()
    async with app.run_test() as pilot:
        # Open Command Palette via Ctrl+P
        await pilot.press("ctrl+p")
        await pilot.pause()

        # Select direct model switch command
        app._handle_command("/model llama3.2:3b")
        await pilot.pause()

        assert app.active_profile_name == "llama3.2:3b"
        assert app.query_one(StatusBar).model_name == "llama3.2:3b"
