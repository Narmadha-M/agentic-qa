"""Tests for utils/claude_client.py — ask_claude."""

import json
import pytest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from io import BytesIO


def _make_response(content: str, status: int = 200):
    body = json.dumps({
        "choices": [{"message": {"content": content}}]
    }).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestAskClaude:
    def test_returns_content_string(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        from utils.claude_client import ask_claude
        with patch("urllib.request.urlopen", return_value=_make_response("Hello")):
            result = ask_claude("Say hello")
        assert result == "Hello"

    def test_uses_openrouter_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from utils.claude_client import ask_claude
        with patch("urllib.request.urlopen", return_value=_make_response("ok")) as mock_open:
            ask_claude("test")
        req = mock_open.call_args[0][0]
        assert b"sk-or-v1-test" in req.get_header("Authorization").encode()

    def test_falls_back_to_anthropic_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        from utils.claude_client import ask_claude
        with patch("urllib.request.urlopen", return_value=_make_response("ok")) as mock_open:
            ask_claude("test")
        req = mock_open.call_args[0][0]
        assert b"sk-ant-test" in req.get_header("Authorization").encode()

    def test_raises_when_no_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        from utils.claude_client import ask_claude
        with pytest.raises(EnvironmentError, match="OPENROUTER_API_KEY"):
            ask_claude("test")

    def test_raises_on_http_error(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "key")
        from utils.claude_client import ask_claude
        http_err = HTTPError(
            url="https://openrouter.ai/api/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=BytesIO(b'{"error":"unauthorized"}'),
        )
        with patch("urllib.request.urlopen", side_effect=http_err):
            with pytest.raises(HTTPError):
                ask_claude("test")

    def test_system_message_included_when_provided(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "key")
        from utils.claude_client import ask_claude
        captured = {}
        def fake_open(req, timeout):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _make_response("ok")
        with patch("urllib.request.urlopen", side_effect=fake_open):
            ask_claude("user msg", system="sys msg")
        messages = captured["body"]["messages"]
        assert any(m["role"] == "system" and m["content"] == "sys msg" for m in messages)

    def test_no_system_message_when_not_provided(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "key")
        from utils.claude_client import ask_claude
        captured = {}
        def fake_open(req, timeout):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _make_response("ok")
        with patch("urllib.request.urlopen", side_effect=fake_open):
            ask_claude("user msg")
        messages = captured["body"]["messages"]
        assert not any(m["role"] == "system" for m in messages)

    def test_request_targets_correct_url(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "key")
        from utils import claude_client
        from utils.claude_client import ask_claude, API_URL
        with patch("urllib.request.urlopen", return_value=_make_response("ok")) as mock_open:
            ask_claude("test")
        req = mock_open.call_args[0][0]
        assert req.full_url == API_URL

    def test_request_method_is_post(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "key")
        from utils.claude_client import ask_claude
        with patch("urllib.request.urlopen", return_value=_make_response("ok")) as mock_open:
            ask_claude("test")
        req = mock_open.call_args[0][0]
        assert req.get_method() == "POST"
