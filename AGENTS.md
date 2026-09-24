# AGENTS.md

> **Mandate:** This file serves as the primary instructional context for AI agents working on the `mwb-chainlit` repository. Adhere to the following guidelines and conventions at all times.

## 1. Project Overview
`mwb-chainlit` is a specialized AI assistant for metabolomics data analysis. It provides a conversational interface via **Chainlit** and employs a **smolagents** agent to interact with the **Metabolomics Workbench**. The app is being built up incrementally: it currently just forwards chat messages to a smolagents `CodeAgent` and returns its response, with Metabolomics Workbench tools to be added as follow-up features.

### Key Technologies
- **Language:** Python 3.12+
- **Agent Framework:** smolagents (https://github.com/huggingface/smolagents)
- **Frontend/UI:** Chainlit (https://github.com/Chainlit/chainlit)
- **Package Manager:** `uv` (Do not use pip or poetry directly)

### Architecture
The application follows a tool-based agent architecture:
- **`app.py`**: Main entry point, defines the Chainlit UI.

---

## 2. Directory Structure

```
.
├── .chainlit                       # Chainlit configuration and assets
├── AGENTS.md                       # This file (Instructional context for AI agents)
├── app.py                          # Chainlit app that forwards messages to a smolagents agent.
├── chainlit.md                     # Chainlit help documentation
├── Dockerfile                      # Docker configuration file
├── pyproject.toml                  # UV Project configuration.
├── README.md                       # Project description and user setup.
├── tests/                          # Directory for test files.
└── uv.lock                         # UV Lock file.
```

---

## 3. Development Workflow & Commands

### Environment Configuration
The following environment variables are required for development:
- `BASE_URL`: OpenAI-compatible API endpoint.
- `API_KEY`: Your API key.
- `MODEL`: The LLM to use (e.g., `gpt-4o-mini`).

### Key Commands
Always use `uv` for package management and script execution.
- **Setup:** `uv sync --group test`
- **Development Server:** `uv run chainlit run app.py -w`
- **Running Tests:** `uv run pytest`
- **Test Coverage:** `uv run pytest --cov=.`
- **Formatting:** `uv run black .`
- **Dependency Management:** Use `uv add <pkg>` or `uv add <pkg> --group test`.

### Testing Standards
- **TDD:** Write or update tests in the `tests/` directory before implementation.
- **Naming:** Files must follow the `test_<module>.py` pattern.
- **Fixtures:** Use `pytest` fixtures for mocking API calls or shared state.
- **Minimalism:** Tests should focus on behavior, not implementation details.

---

## 4. Coding Conventions & Style

### Design Philosophy: "Simplicity First"
- **Minimalism:** Prefer simple, direct solutions over complex abstractions.
- **Refactoring:** Before adding new code, consider if refactoring existing code can simplify the solution.
- **Docstrings:** Use **Google Style Docstrings** for all modules, classes, and functions.
- **Typing:** Use standard Python type hints for all function arguments and return values.

### Tool-First Implementation
The agent relies on specific tool sequences. When adding new features:
- Encapsulate logic in the appropriate `*_tool_logic.py` file.
- Register tools in `app.py`.
- Ensure tools return JSON-serializable dictionaries or specific result objects.

### Formatting & Style
- **Formatter:** Black (`uv run black .`). Always run before declaring a task complete.
- **Style:** Follow PEP 8 conventions.
- **Commenting:** Use clear and concise comments to explain non-obvious code.

---

## 5. Lessons Learned & Hints
- **Environment Setup:** Always run `uv sync --group test` before running tests to ensure `pytest` and its plugins are available.
- **Testing Chainlit handlers:** `cl.user_session` and `cl.Message` require an active Chainlit context. Use `chainlit.context.init_http_context()` inside an `async` pytest fixture (a sync fixture raises `RuntimeError: no running event loop`, since `ChainlitContext` calls `asyncio.get_running_loop()`). `pytest-asyncio` is configured with `asyncio_mode = "auto"` in `pyproject.toml`, so `async def` tests/fixtures run without needing `@pytest.mark.asyncio`.
- **smolagents multi-turn chat:** `CodeAgent.run(task, reset=False)` continues from the previous conversation state; `reset=True` (the default) wipes memory each call. `app.py` keeps one agent per Chainlit session (via `cl.user_session`) and calls `run` with `reset=False` so context carries across messages. `agent.run()` is blocking — call it via `asyncio.to_thread` from an `async` handler.
- **Agent creation is lazy, on the first message.** `_build_agent()` (and therefore the Docker container it spins up for `executor_type="docker"`) is built inside `on_message` the first time `cl.user_session.get("agent")` is `None`, not in `on_chat_start`. This avoids spinning up a container just from loading/refreshing the Chainlit page — a container is only created once the user actually sends a message. `_build_agent()` is also blocking, so it's called via `asyncio.to_thread` like `agent.run()`.
- **Docker containers must be cleaned up explicitly, since we can't use `with CodeAgent(...) as agent:`.** smolagents' docs show a context-manager pattern that calls `agent.cleanup()` (which stops/removes the container) as soon as `agent.run()` returns, but that only works for a single-shot script — our agent has to stay alive across a whole multi-turn Chainlit session (`reset=False`), so it can't be scoped to one `run()` call. Instead, `app.py`'s `on_chat_end` handler calls `agent.cleanup()` when the Chainlit session ends (skips it if no agent was ever built, since creation is lazy). `cleanup()` is blocking, so it's called via `asyncio.to_thread` too.
- **`uv run pytest` needs `pythonpath`/`testpaths`:** without `pythonpath = ["."]` in `[tool.pytest.ini_options]`, `uv run pytest` (the console script) fails every test module with `ModuleNotFoundError: No module named 'app'` because pytest's default "prepend" import mode never puts the repo root on `sys.path` — only `python -m pytest` did that implicitly. `testpaths = ["tests"]` is also required so pytest doesn't try to collect stray top-level scripts (e.g. `kc-examples/*_test.py`) as test modules, which can otherwise execute live agent calls at import time and abort collection for the whole suite.
- **`executor_type="docker"` spins a real container per `CodeAgent()` construction** (builds/pulls the `jupyter-kernel` image, starts a container bound to a local port). Any test that calls `_build_agent()` will do this for real — it's slow, requires Docker running, and leaves the container behind unless something calls the agent's cleanup, so stray `jupyter-kernel` containers can accumulate across test runs (`docker ps -a` to check, `docker rm -f <id>` to clean up).
- **`DockerExecutor` binds a fixed host port (`8888` by default)** — every `CodeAgent(executor_type="docker")` tries to bind the same port, so a second concurrent chat session (another browser tab, or a `chainlit run -w` reload while a container from the previous run is still up) fails with `Bind for 127.0.0.1:8888 failed: port is already allocated`. `_build_agent()` picks a fresh free port per agent via `_free_port()` and passes it through `CodeAgent(executor_kwargs={"port": ...})` (which forwards to `DockerExecutor.__init__(port=...)`), so each session's container binds its own port.
- **`executor_type="docker"` (or any `RemotePythonExecutor`) breaks `final_answer` on the 2nd+ message of a multi-turn session.** `CodeAgent.run()` calls `self.python_executor.send_tools(...)` on *every* call, and `RemotePythonExecutor._patch_final_answer_with_exception` monkeypatches the `final_answer` tool's `__class__` in place — it is not idempotent. Since `app.py` reuses one agent (and its `tools["final_answer"]` instance) per Chainlit session and calls `run(..., reset=False)`, the second message re-patches an already-patched tool: the new `forward` ends up calling the previous turn's exception-raising `forward` as its `_forward`, and since both are bound via the *current* class at call time, invoking `final_answer(...)` recurses into itself (`RecursionError`) instead of returning. The agent burns many steps retrying and hand-patching around this before it (sometimes) recovers, which is why 15+ step runs with huge token counts show up on the 2nd question in a session, and why the reply can be missing or badly delayed. **Fix:** replace `agent.tools["final_answer"]` with a fresh `FinalAnswerTool()` in `on_message` before every `agent.run()` call, so `send_tools()` always patches a clean instance.

---

## 6. Common Workflows

---

## 7. Always
- Update AGENTS.md with any new information or changes.
