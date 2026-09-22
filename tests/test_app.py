"""Tests for the Chainlit <-> smolagents integration in app.py."""

from unittest.mock import MagicMock

import pytest
from chainlit.context import init_http_context

import app


class FakeMessage:
    """Stand-in for cl.Message that records what would be sent to the UI."""

    sent: list[str] = []

    def __init__(self, content: str) -> None:
        self.content = content

    async def send(self) -> None:
        FakeMessage.sent.append(self.content)


@pytest.fixture(autouse=True)
async def chainlit_context():
    """Ensure each test has a fresh Chainlit context and user session."""
    init_http_context()
    FakeMessage.sent = []
    yield


@pytest.mark.asyncio
async def test_on_chat_start_creates_and_stores_an_agent(monkeypatch):
    fake_agent = object()
    monkeypatch.setattr(app, "_build_agent", lambda: fake_agent)

    await app.on_chat_start()

    assert app.cl.user_session.get("agent") is fake_agent


@pytest.mark.asyncio
async def test_on_message_forwards_input_to_agent_and_returns_response(monkeypatch):
    fake_agent = MagicMock()
    fake_agent.run.return_value = "42"
    app.cl.user_session.set("agent", fake_agent)
    monkeypatch.setattr(app.cl, "Message", FakeMessage)

    message = MagicMock()
    message.content = "What is 6 * 7?"

    await app.on_message(message)

    fake_agent.run.assert_called_once_with("What is 6 * 7?", reset=False)
    assert FakeMessage.sent == ["42"]
