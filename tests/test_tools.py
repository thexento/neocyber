"""Tests for cybersecurity validator and tool executor."""
import os
import tempfile
import pytest

from neocyber.engine.tools import SecurityValidator, ToolExecutor


def test_validator_allowed_targets():
    v = SecurityValidator()
    assert v.validate_target("127.0.0.1") is True
    assert v.validate_target("http://127.0.0.1:8080/path") is True
    assert v.validate_target("localhost") is True
    assert v.validate_target("192.168.1.50") is True
    assert v.validate_target("10.0.0.1") is True
    assert v.validate_target("evil.unauthorized.com") is False


def test_validator_dangerous_commands():
    v = SecurityValidator()
    assert v.validate_command("ls -la")[0] is True
    assert v.validate_command("nmap -sT 127.0.0.1")[0] is True
    # Dangerous commands
    assert v.validate_command("rm -rf /")[0] is False
    assert v.validate_command("nmap -sV 0.0.0.0/0")[0] is False


def test_tool_executor_shell():
    with tempfile.TemporaryDirectory() as tmpdir:
        executor = ToolExecutor(tmpdir)
        code, output, duration = executor.execute_shell("echo 'hello neocyber'")
        assert code == 0
        assert "hello neocyber" in output
        assert duration >= 0.0


def test_tool_executor_file_ops_and_diff():
    with tempfile.TemporaryDirectory() as tmpdir:
        executor = ToolExecutor(tmpdir)
        # Write
        ok, msg = executor.write_file("test.txt", "line 1\nline 2\n")
        assert ok is True

        # Read
        ok, content = executor.read_file("test.txt")
        assert ok is True
        assert "line 1" in content

        # Edit with diff
        ok, msg, diff = executor.edit_file("test.txt", "line 2", "line 2 modified")
        assert ok is True
        assert "-line 2" in diff
        assert "+line 2 modified" in diff

        # Verify content
        ok, updated = executor.read_file("test.txt")
        assert "line 2 modified" in updated


def test_tool_executor_record_finding():
    with tempfile.TemporaryDirectory() as tmpdir:
        executor = ToolExecutor(tmpdir)
        finding = executor.record_finding(
            title="SQL Injection",
            severity="CRITICAL",
            asset="127.0.0.1:8080",
            description="Payload confirmed in login param",
            remediation="Use parameterized queries",
        )
        assert finding["title"] == "SQL Injection"
        assert finding["severity"] == "CRITICAL"
        assert os.path.isfile(executor.findings_file)
