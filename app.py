"""Chainlit application that forwards user messages to a smolagents agent.

This is a minimal integration: Chainlit handles the conversational UI and
each user message is forwarded to a smolagents `CodeAgent`, whose response is
sent back to the user.
"""

import asyncio
import os

import chainlit as cl
from smolagents import CodeAgent, OpenAIModel, WebSearchTool

MODEL = os.environ.get("MODEL")
BASE_URL = os.environ.get("BASE_URL")
API_KEY = os.environ.get("API_KEY")


def _build_agent() -> CodeAgent:
    """Create a smolagents agent configured from environment variables.

    Returns:
        A CodeAgent wired to the configured OpenAI-compatible model.
    """
    model = OpenAIModel(model_id=MODEL, api_base=BASE_URL, api_key=API_KEY)
    return CodeAgent(tools=[WebSearchTool()], model=model)


@cl.on_chat_start
async def on_chat_start() -> None:
    """Create a fresh smolagents agent for this chat session."""
    cl.user_session.set("agent", _build_agent())


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Forward the user's message to the session's smolagents agent.

    Args:
        message: The user's message to process.
    """
    agent = cl.user_session.get("agent")
    # agent.run() is blocking, so run it off the event loop.
    response = await asyncio.to_thread(agent.run, message.content, reset=False)
    await cl.Message(content=str(response)).send()
