"""Chainlit application integrating OpenAI with Model Context Protocol (MCP) servers.

This application provides a conversational interface for connecting to MCP servers
that expose tools for querying. It handles tool discovery, execution, and response
generation using OpenAI's chat completion API with function calling capabilities.
"""

from typing import Any, Dict, List, Tuple
import json
from contextlib import AsyncExitStack
import os

from openai import AsyncOpenAI
import chainlit as cl

# MCP client imports for connecting to Model Context Protocol servers
from mcp import ClientSession as McpClientSession
from mcp.client.streamable_http import streamablehttp_client


# MCP server connection configuration
# These values should be provided via environment variables
MCP_NAME = os.environ.get("MCP_NAME")  # Display name for the MCP connection
MCP_URL = os.environ.get("MCP_URL")  # URL of the streamable HTTP MCP server

# Initialize OpenAI client with optional custom configuration
# If BASE_URL and API_KEY are provided, use custom endpoint (e.g., for local LLMs)
# Otherwise, use default OpenAI API endpoint
if "BASE_URL" in os.environ and "API_KEY" in os.environ:
    BASE_URL = os.environ.get("BASE_URL")
    API_KEY = os.environ.get("API_KEY")
    client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
else:
    client = AsyncOpenAI()

# Enable Chainlit's OpenAI instrumentation for automatic message streaming
cl.instrument_openai()

# Model configuration - typically GPT-4, GPT-3.5-turbo, or compatible model
MODEL = os.environ.get("MODEL")
settings = {
    "model": MODEL,
}

# Prompt instruction for the LLM
PROMPT_INSTRUCTION = os.environ.get("PROMPT_INSTRUCTION")

# Maximum number of conversation turns to keep in history
# Prevents context window overflow that can cause connection errors
# Each turn = 1 user message + 1 assistant response (possibly with tool calls)
MAX_HISTORY_TURNS = int(os.environ.get("MAX_HISTORY_TURNS", "10"))


def _trim_message_history(messages: List[Dict[str, Any]], max_turns: int) -> List[Dict[str, Any]]:
    """Trim conversation history to prevent context window overflow.
    
    Keeps the system message and the most recent conversation turns,
    where a turn consists of user message, optional assistant tool calls,
    optional tool results, and assistant response.
    
    Args:
        messages: Full conversation history
        max_turns: Maximum number of user-assistant exchange turns to keep
    
    Returns:
        Trimmed message history with system prompt and recent turns
    """
    if not messages:
        return messages
    
    # Separate system message (always at index 0) from conversation
    system_msg = None
    conversation = messages
    if messages[0].get("role") == "system":
        system_msg = messages[0]
        conversation = messages[1:]
    
    # If conversation is short enough, return as-is
    if len(conversation) <= max_turns * 4:  # Rough estimate: user + assistant + tool calls + results
        return messages
    
    # Count turns by counting user messages (each turn starts with user message)
    user_message_indices = [i for i, msg in enumerate(conversation) if msg.get("role") == "user"]
    
    if len(user_message_indices) <= max_turns:
        # We're within the turn limit
        return messages
    
    # Keep only the last max_turns
    cut_index = user_message_indices[-max_turns]
    trimmed_conversation = conversation[cut_index:]
    
    # Reconstruct with system message
    if system_msg:
        return [system_msg] + trimmed_conversation
    return trimmed_conversation


def _get_mcp_tools_state() -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, str]]:
    """Retrieve MCP tools state from the user session.

    Returns:
        Tuple containing:
        - tools_by_connection: Dict mapping connection names to lists of tool definitions
        - tool_name_to_connection: Dict mapping tool names to their source connection
    """
    tools_by_conn = cl.user_session.get("mcp_tools_by_connection", {})
    name_to_conn = cl.user_session.get("mcp_tool_to_connection", {})
    return tools_by_conn, name_to_conn


def _set_mcp_tools_state(
    tools_by_connection: Dict[str, List[Dict[str, Any]]],
    tool_name_to_connection: Dict[str, str],
) -> None:
    """Store MCP tools state in the user session.

    Args:
        tools_by_connection: Dict mapping connection names to lists of tool definitions
        tool_name_to_connection: Dict mapping tool names to their source connection
    """
    cl.user_session.set("mcp_tools_by_connection", tools_by_connection)
    cl.user_session.set("mcp_tool_to_connection", tool_name_to_connection)


def _mcp_tools_to_openai_tools(
    tools_by_connection: Dict[str, List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Convert MCP tool descriptors into OpenAI function calling tool definitions.

    Args:
        tools_by_connection: Dict mapping connection names to lists of MCP tool definitions

    Returns:
        List of OpenAI-compatible tool definitions in function calling format
    """
    openai_tools: List[Dict[str, Any]] = []
    # Iterate through all MCP connections and their tools
    for conn_tools in tools_by_connection.values():
        for t in conn_tools:
            name = t.get("name")
            desc = t.get("description", "")
            # Handle different schema key naming conventions (inputSchema or input_schema)
            params = t.get("inputSchema") or t.get("input_schema") or {}
            # Ensure params is a valid dict (JSON Schema format)
            # MCP tools may return schemas as strings that need parsing
            if isinstance(params, str):
                try:
                    params = json.loads(params)
                except json.JSONDecodeError:
                    params = {}
            # Build OpenAI function calling tool definition
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": desc,
                        "parameters": params if isinstance(params, dict) else {},
                    },
                }
            )
    return openai_tools


@cl.on_chat_start
async def on_chat_start():
    """Chainlit lifecycle hook called when a new chat session starts.

    Automatically establishes connection to the configured MCP server
    to make its tools available for the conversation.
    """
    # Auto-connect to the configured MCP streamable-http server
    await _ensure_mcp_connected()


@cl.on_mcp_connect
async def on_mcp_connect(connection, session):
    """Chainlit lifecycle hook called when an MCP connection is established.

    Discovers available tools from the MCP server and stores them in the user session
    for use in subsequent chat interactions.

    Args:
        connection: The MCP connection object containing connection metadata
        session: The MCP client session for communicating with the server
    """
    try:
        # Query the MCP server for its available tools
        result = await session.list_tools()
        # Normalize returned tools to plain dicts for consistent handling
        # Tools may be returned as Pydantic models or plain dictionaries
        tools: List[Dict[str, Any]] = []
        for tool in getattr(result, "tools", []) or []:
            # Extract tool metadata using both attribute and dict access for compatibility
            name = getattr(tool, "name", None) or tool.get("name")
            desc = getattr(tool, "description", None) or tool.get("description")
            schema = getattr(tool, "inputSchema", None) or tool.get("inputSchema")
            tools.append({"name": name, "description": desc, "inputSchema": schema})

        # Update session state with newly discovered tools
        tools_by_conn, name_to_conn = _get_mcp_tools_state()
        tools_by_conn[connection.name] = tools
        for t in tools:
            if t.get("name"):
                # Map each tool name to its source connection
                # Note: Last-one-wins if duplicate tool names appear across connections
                name_to_conn[t["name"]] = connection.name
        _set_mcp_tools_state(tools_by_conn, name_to_conn)

        if tools:
            tool_names = ", ".join([t["name"] for t in tools if t.get("name")])
            await cl.Message(
                content=(
                    f"MCP '{connection.name}' connected. Tools available: {tool_names}"
                )
            ).send()
        else:
            await cl.Message(
                content=f"MCP '{connection.name}' connected. No tools found."
            ).send()
    except Exception as e:
        await cl.Message(content=f"Failed to initialize MCP: {e}").send()


@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session):
    """Chainlit lifecycle hook called when an MCP connection is closed.

    Removes disconnected connection's tools from the session state to prevent
    attempts to call unavailable tools.

    Args:
        name: Name of the disconnected MCP connection
        session: The MCP client session that was disconnected
    """
    # Retrieve current tool state
    tools_by_conn, name_to_conn = _get_mcp_tools_state()
    # Remove all tools associated with the disconnected connection
    removed = tools_by_conn.pop(name, None)
    if removed:
        # Clean up tool-to-connection mappings for removed tools
        for t in removed:
            tname = t.get("name")
            if tname and name_to_conn.get(tname) == name:
                name_to_conn.pop(tname, None)
    # Persist updated state
    _set_mcp_tools_state(tools_by_conn, name_to_conn)
    await cl.Message(content=f"MCP '{name}' disconnected.").send()


def _find_mcp_for_tool(tool_name: str) -> str:
    """Look up which MCP connection provides a specific tool.

    Args:
        tool_name: Name of the tool to look up

    Returns:
        Name of the MCP connection that provides this tool, or empty string if not found
    """
    _, name_to_conn = _get_mcp_tools_state()
    return name_to_conn.get(tool_name, "")


async def _ensure_mcp_connected():
    """Establish connection to MCP server if not already connected.

    Creates a streamable HTTP connection to the configured MCP server,
    initializes the session, discovers available tools, and registers
    the connection in Chainlit's session management.

    This is idempotent - if already connected, returns immediately.
    """
    # Check if we already have an active connection to this MCP server
    existing = cl.context.session.mcp_sessions.get(MCP_NAME)
    if existing:
        return

    # Use AsyncExitStack for proper cleanup of async resources
    exit_stack = AsyncExitStack()
    try:
        # Establish streamable HTTP connection to MCP server
        # Returns read/write streams for bidirectional communication
        read, write, _ = await exit_stack.enter_async_context(
            streamablehttp_client(MCP_URL)
        )
        # Create MCP client session from the communication streams
        mcp_session = await exit_stack.enter_async_context(
            McpClientSession(read, write)
        )
        # Perform MCP protocol handshake
        await mcp_session.initialize()

        # Register the session in Chainlit for lifecycle management
        # Store both the MCP session and exit stack for proper cleanup
        cl.context.session.mcp_sessions[MCP_NAME] = (mcp_session, exit_stack)

        # Discover available tools from the MCP server
        # This duplicates on_mcp_connect logic since we're manually connecting
        try:
            result = await mcp_session.list_tools()
            # Normalize tool definitions to plain dictionaries
            tools: List[Dict[str, Any]] = []
            for tool in getattr(result, "tools", []) or []:
                name = getattr(tool, "name", None) or tool.get("name")
                desc = getattr(tool, "description", None) or tool.get("description")
                schema = getattr(tool, "inputSchema", None) or tool.get("inputSchema")
                tools.append({"name": name, "description": desc, "inputSchema": schema})

            # Update session state with discovered tools
            tools_by_conn, name_to_conn = _get_mcp_tools_state()
            tools_by_conn[MCP_NAME] = tools
            for t in tools:
                if t.get("name"):
                    name_to_conn[t["name"]] = MCP_NAME
            _set_mcp_tools_state(tools_by_conn, name_to_conn)

            if tools:
                await cl.Message(
                    content=(
                        f"Auto-connected MCP '{MCP_NAME}'. Tools: "
                        + ", ".join([t["name"] for t in tools if t.get("name")])
                    )
                ).send()
            else:
                await cl.Message(
                    content=f"Auto-connected MCP '{MCP_NAME}'. No tools found."
                ).send()
        except Exception as e:
            await cl.Message(
                content=f"MCP connected but listing tools failed: {e}"
            ).send()

    except Exception as e:
        # If any error, ensure resources are cleaned up
        try:
            await exit_stack.aclose()
        except Exception:
            pass
        await cl.Message(content=f"Failed to auto-connect MCP: {e}").send()


@cl.on_message
async def on_message(message: cl.Message):
    """Chainlit message handler - processes user messages and generates responses.

    Implements the function calling pattern with MCP tools:
    1. Sends user message to OpenAI with available MCP tools
    2. If model calls tools, executes them via MCP and sends results back
    3. Generates final response incorporating tool results

    Args:
        message: The user's message to process
    """
    # Retrieve currently available MCP tools and convert to OpenAI format
    tools_by_conn, _ = _get_mcp_tools_state()
    openai_tools = _mcp_tools_to_openai_tools(tools_by_conn) if tools_by_conn else []

    # Retrieve or initialize conversation history from session
    message_history = cl.user_session.get("message_history")
    if message_history is None:
        # First message in conversation - initialize with system prompt
        message_history = [
            {"role": "system", "content": PROMPT_INSTRUCTION}
        ]
    
    # Append the current user message to history
    message_history.append({"role": "user", "content": message.content})

    # Trim history to prevent context window overflow and connection errors
    message_history = _trim_message_history(message_history, MAX_HISTORY_TURNS)

    # Initial model call with function calling capability
    # Provide tool definitions so model can choose to call them if needed
    response = await client.chat.completions.create(
        messages=message_history,
        tools=openai_tools if openai_tools else None,
        tool_choice=(
            "auto" if openai_tools else None
        ),  # Let model decide whether to use tools
        **settings,
    )

    msg = response.choices[0].message

    # Check if the model wants to call any tools
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        # Append the assistant's tool call requests to conversation history
        # This preserves the full context for the second model call
        message_history.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ],
        })

        # Execute each requested tool call via MCP
        tool_results_msgs: List[Dict[str, Any]] = []
        for tc in tool_calls:
            tool_name = tc.function.name
            # Parse the tool arguments (JSON string -> dict)
            try:
                tool_input = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                tool_input = {}

            # Look up which MCP connection provides this tool
            conn_name = _find_mcp_for_tool(tool_name)
            if not conn_name:
                # Tool not found in any connected MCP server
                content = json.dumps(
                    {"error": f"No MCP connection found for tool '{tool_name}'"}
                )
            else:
                # Retrieve the active MCP session for this connection
                mcp_entry = cl.context.session.mcp_sessions.get(conn_name)
                if not mcp_entry:
                    # Connection was registered but session is no longer available
                    content = json.dumps(
                        {"error": f"MCP session for '{conn_name}' is not available"}
                    )
                else:
                    mcp_session, _ = mcp_entry
                    try:
                        # Execute the tool via MCP protocol
                        result = await mcp_session.call_tool(tool_name, tool_input)
                        # Convert result to JSON for passing back to the model
                        # MCP results should be JSON-serializable, but handle edge cases
                        try:
                            content = json.dumps(result)
                        except TypeError:
                            # Fallback for non-serializable results
                            content = json.dumps({"result": str(result)})
                    except Exception as e:
                        # Tool execution failed - return error to model
                        content = json.dumps({"error": str(e)})

            # Append tool result in OpenAI's expected format
            tool_results_msgs.append(
                {"role": "tool", "tool_call_id": tc.id, "content": content}
            )

        # Add all tool results to conversation history
        message_history.extend(tool_results_msgs)

        # Second model call with tool results included
        # Model uses these results to formulate a natural language response
        second = await client.chat.completions.create(
            messages=message_history,
            **settings,
        )
        
        # Add the final assistant response to history
        final_response = second.choices[0].message.content or ""
        message_history.append({"role": "assistant", "content": final_response})
        
        # Save updated conversation history to session
        cl.user_session.set("message_history", message_history)
        
        await cl.Message(content=final_response).send()
        return

    # No tool calls were made - add assistant's direct response to history
    assistant_response = msg.content or ""
    message_history.append({"role": "assistant", "content": assistant_response})
    
    # Save updated conversation history to session
    cl.user_session.set("message_history", message_history)
    
    await cl.Message(content=assistant_response).send()
