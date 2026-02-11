"""Helpers for translating LangChain/Chainlit message payloads."""

from __future__ import annotations

import ast
import json
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage


def _collect_analysis_ids(payload: Any) -> list[str]:
    """Recursively collect analysis IDs from nested dict/list payloads."""
    analysis_ids: list[str] = []

    if isinstance(payload, dict):
        for key, value in payload.items():
            if key == "analysis_id":
                if isinstance(value, str) and value:
                    analysis_ids.append(value)
                elif isinstance(value, list):
                    analysis_ids.extend(
                        [item for item in value if isinstance(item, str) and item]
                    )
            analysis_ids.extend(_collect_analysis_ids(value))
    elif isinstance(payload, list):
        for item in payload:
            analysis_ids.extend(_collect_analysis_ids(item))

    return analysis_ids


def extract_first_analysis_id(payload: Any) -> str | None:
    """Return the first discovered analysis ID from a payload."""
    analysis_ids = _collect_analysis_ids(payload)
    return analysis_ids[0] if analysis_ids else None


def _parse_tool_content(content: Any) -> dict[str, Any] | None:
    """Parse tool output content into a dictionary."""
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(content)
                return parsed if isinstance(parsed, dict) else None
            except (ValueError, SyntaxError):
                return None
    return None


def extract_tool_payload(
    result: dict[str, Any], tool_name: str
) -> dict[str, Any] | None:
    """Extract structured payload for a tool message by tool name."""
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, ToolMessage) and message.name == tool_name:
            parsed = _parse_tool_content(message.content)
            if parsed is not None:
                return parsed
    return None


def extract_volcano_plot_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    """Extract structured payload from create_volcano_plot_analysis tool output."""
    return extract_tool_payload(result, "create_volcano_plot_analysis")


def extract_clustered_heatmap_payload(
    result: dict[str, Any],
) -> dict[str, Any] | None:
    """Extract structured payload from create_clustered_heatmap_analysis output."""
    return extract_tool_payload(result, "create_clustered_heatmap_analysis")


def extract_tool_call_logs(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract tool call details from LangChain result messages."""
    messages = result.get("messages", [])
    tool_logs: list[dict[str, Any]] = []
    for message in messages:
        if isinstance(message, ToolMessage):
            parsed_content = _parse_tool_content(message.content)
            tool_logs.append(
                {
                    "tool_name": message.name,
                    "content": (
                        parsed_content
                        if parsed_content is not None
                        else str(message.content)
                    ),
                }
            )
    return tool_logs


def _extract_reasoning_from_ai_message(message: AIMessage) -> Any:
    """Best-effort extraction of model reasoning traces when exposed by provider."""
    additional_kwargs = (
        message.additional_kwargs if isinstance(message.additional_kwargs, dict) else {}
    )
    for key in ("reasoning", "thinking", "reasoning_content", "reasoning_summary"):
        if key in additional_kwargs:
            return additional_kwargs[key]

    if isinstance(message.content, list):
        reasoning_blocks = []
        for item in message.content:
            if (
                isinstance(item, dict)
                and item.get("type") in {"reasoning", "thinking", "summary"}
                and "text" in item
            ):
                reasoning_blocks.append(item.get("text"))
        if reasoning_blocks:
            return reasoning_blocks

    return None


def extract_llm_response_log(result: dict[str, Any]) -> dict[str, Any]:
    """Extract the last AI response plus optional reasoning/tool call details."""
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return {
                "content": message.content,
                "tool_calls": message.tool_calls,
                "reasoning": _extract_reasoning_from_ai_message(message),
                "response_metadata": message.response_metadata,
            }
    return {"content": None, "tool_calls": [], "reasoning": None}


def build_agent_messages(
    chat_history: list[dict[str, Any]], latest_user_message: str
) -> list[tuple[str, str]]:
    """Build agent-ready conversation history from Chainlit chat context."""
    messages: list[tuple[str, str]] = []
    for item in chat_history:
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"} or not isinstance(content, str):
            continue
        normalized_content = content.strip()
        if not normalized_content:
            continue
        messages.append((role, normalized_content))

    latest = latest_user_message.strip()
    if latest and (not messages or messages[-1] != ("user", latest)):
        messages.append(("user", latest))

    return messages


def extract_agent_reply(result: dict[str, Any]) -> str:
    """Extract a user-facing text reply from agent state output."""
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return (
                message.content
                if isinstance(message.content, str)
                else str(message.content)
            )
        if isinstance(message, BaseMessage) and message.type == "ai":
            return str(message.content)
    return "I could not produce a response."
