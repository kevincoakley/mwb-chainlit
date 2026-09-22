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

---

## 6. Common Workflows

---

## 7. Always
- Update AGENTS.md with any new information or changes.
