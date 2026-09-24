"""Chainlit application that forwards user messages to a smolagents agent.

This is a minimal integration: Chainlit handles the conversational UI and
each user message is forwarded to a smolagents `CodeAgent`, whose response is
sent back to the user.
"""

import asyncio
import os
import socket

import chainlit as cl
from smolagents import CodeAgent, FinalAnswerTool, OpenAIModel, WebSearchTool

MODEL = os.environ.get("MODEL")
BASE_URL = os.environ.get("BASE_URL")
API_KEY = os.environ.get("API_KEY")


def _free_port() -> int:
    """Find a currently unused TCP port on localhost.

    Returns:
        An available port number.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _build_agent() -> CodeAgent:
    """Create a smolagents agent configured from environment variables.

    Each agent gets its own Docker executor port so multiple chat sessions
    (e.g. concurrent browser tabs, or reloads under `chainlit run -w`) can
    run their containers side by side instead of colliding on port 8888.

    Returns:
        A CodeAgent wired to the configured OpenAI-compatible model.
    """
    model = OpenAIModel(model_id=MODEL, api_base=BASE_URL, api_key=API_KEY)
    return CodeAgent(
        tools=[WebSearchTool()],
        model=model,
        executor_type="docker",
        executor_kwargs={"port": _free_port()},
    )


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Forward the user's message to the session's smolagents agent.

    The agent (and its Docker container) is built lazily on the session's
    first message rather than in `on_chat_start`, so refreshing the page
    doesn't spin up a container until the user actually sends something.

    Args:
        message: The user's message to process.
    """
    agent = cl.user_session.get("agent")
    if agent is None:
        # _build_agent() is blocking (spins up a Docker container), so run
        # it off the event loop, same as agent.run() below.
        agent = await asyncio.to_thread(_build_agent)
        cl.user_session.set("agent", agent)
    # smolagents' RemotePythonExecutor.send_tools() re-patches the final_answer
    # tool's class on every agent.run() call (executor_type="docker" uses this).
    # That patch isn't idempotent: patching an already-patched tool makes its
    # forward/_forward methods call each other recursively, breaking final_answer
    # on the second and later messages of a session (reset=False keeps the same
    # tool instance around). Swap in a fresh tool before each run to avoid it.
    agent.tools["final_answer"] = FinalAnswerTool()
    # agent.run() is blocking, so run it off the event loop.
    response = await asyncio.to_thread(agent.run, message.content, reset=False)
    await cl.Message(content=str(response)).send()


@cl.on_chat_end
async def on_chat_end() -> None:
    """Tear down the session's smolagents agent, if one was created.

    `agent.cleanup()` stops and removes the Docker container backing the
    executor. There may be no agent yet if the session ended before its
    first message (agents are built lazily in `on_message`).
    """
    agent = cl.user_session.get("agent")
    if agent is not None:
        # cleanup() is blocking (talks to the Docker daemon), so run it off
        # the event loop, same as _build_agent() and agent.run() above.
        await asyncio.to_thread(agent.cleanup)
