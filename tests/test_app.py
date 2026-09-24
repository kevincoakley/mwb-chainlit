"""Tests for the Chainlit <-> smolagents integration in app.py."""

import socket
from unittest.mock import MagicMock

import pytest
from chainlit.context import init_http_context
from smolagents import FinalAnswerTool

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


def test_build_agent_uses_bing_for_web_search():
    agent = app._build_agent()

    assert agent.tools["web_search"].engine == "bing"


def test_free_port_returns_a_currently_bindable_port():
    port = app._free_port()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", port))


def test_build_agent_uses_a_distinct_docker_port_per_agent(monkeypatch):
    """Guards against the Docker executor's fixed default port (8888): with a
    shared port, a second chat session's container collides with the first
    and fails to start ("port is already allocated"). Each agent must request
    its own free port instead.
    """
    captured_kwargs = []

    class _FakeCodeAgent:
        def __init__(self, **kwargs):
            captured_kwargs.append(kwargs)

    monkeypatch.setattr(app, "CodeAgent", _FakeCodeAgent)
    monkeypatch.setattr(app, "OpenAIModel", MagicMock())

    app._build_agent()
    app._build_agent()

    ports = [kwargs["executor_kwargs"]["port"] for kwargs in captured_kwargs]
    assert len(ports) == 2
    assert ports[0] != ports[1]
    assert all(isinstance(port, int) for port in ports)


@pytest.mark.asyncio
async def test_on_message_builds_and_stores_the_agent_lazily_on_first_message(
    monkeypatch,
):
    """The agent (and its Docker container) should be created on the first
    message of a session, not up front in on_chat_start, so refreshing the
    page without sending anything doesn't spin up a container.
    """
    fake_agent = MagicMock()
    fake_agent.run.return_value = "42"
    monkeypatch.setattr(app, "_build_agent", MagicMock(return_value=fake_agent))
    monkeypatch.setattr(app.cl, "Message", FakeMessage)

    assert app.cl.user_session.get("agent") is None

    message = MagicMock()
    message.content = "What is 6 * 7?"

    await app.on_message(message)

    app._build_agent.assert_called_once_with()
    assert app.cl.user_session.get("agent") is fake_agent
    assert FakeMessage.sent == ["42"]


@pytest.mark.asyncio
async def test_on_message_reuses_the_stored_agent_on_later_messages(monkeypatch):
    fake_agent = MagicMock()
    fake_agent.run.return_value = "42"
    build_agent = MagicMock(
        side_effect=AssertionError("_build_agent should not be called again")
    )
    monkeypatch.setattr(app, "_build_agent", build_agent)
    app.cl.user_session.set("agent", fake_agent)
    monkeypatch.setattr(app.cl, "Message", FakeMessage)

    message = MagicMock()
    message.content = "And the follow-up question?"

    await app.on_message(message)

    build_agent.assert_not_called()
    assert FakeMessage.sent == ["42"]


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


@pytest.mark.asyncio
async def test_on_message_replaces_final_answer_tool_with_a_fresh_instance(monkeypatch):
    """Guards against a smolagents bug: RemotePythonExecutor.send_tools() re-patches
    the final_answer tool's class on every agent.run() call, and that patch isn't
    idempotent -- patching an already-patched tool makes its forward/_forward methods
    call each other recursively. Since app.py reuses one agent (and its tools dict)
    per session across messages, a stale patched-from-a-previous-turn tool must be
    swapped out before each run.
    """

    class _PatchedFinalAnswerTool(FinalAnswerTool):
        """Stands in for a final_answer tool mutated by a previous turn."""

    fake_agent = MagicMock()
    fake_agent.run.return_value = "42"
    fake_agent.tools = {"final_answer": _PatchedFinalAnswerTool()}
    app.cl.user_session.set("agent", fake_agent)
    monkeypatch.setattr(app.cl, "Message", FakeMessage)

    message = MagicMock()
    message.content = "And the follow-up question?"

    await app.on_message(message)

    assert type(fake_agent.tools["final_answer"]) is FinalAnswerTool


@pytest.mark.asyncio
async def test_on_chat_end_cleans_up_the_stored_agent():
    """agent.cleanup() stops and removes the Docker container, so it must run
    when the chat session ends -- otherwise every session leaves its
    container running.
    """
    fake_agent = MagicMock()
    app.cl.user_session.set("agent", fake_agent)

    await app.on_chat_end()

    fake_agent.cleanup.assert_called_once_with()


@pytest.mark.asyncio
async def test_on_chat_end_does_nothing_without_an_agent():
    """A session that ends before its first message never built an agent
    (agents are created lazily); on_chat_end must not error in that case.
    """
    assert app.cl.user_session.get("agent") is None

    await app.on_chat_end()
