# AGENTS.md

> **Mandate:** This file serves as the primary instructional context for AI agents working on the `mwb-chainlit` repository. Adhere to the following guidelines and conventions at all times.

## 1. Project Overview
`mwb-chainlit` is a specialized AI assistant for metabolomics data analysis. It provides a conversational interface via **Chainlit** and employs a **LangChain** agent to interact with the **Metabolomics Workbench API**.

### Key Technologies
- **Language:** Python 3.12+
- **Agent Framework:** LangChain (with LangGraph and OpenAI-compatible Chat Models)
- **Frontend/UI:** Chainlit
- **Package Manager:** `uv` (Do not use pip or poetry directly)
- **Data Analysis:** Pandas, SciPy, Statsmodels, Seaborn, Matplotlib

### Architecture
The application follows a tool-based agent architecture:
- **`app.py`**: Main entry point, defines the Chainlit UI and the LangChain agent.
- **`study_tool_logic.py`** (and other `*_tool_logic.py` files): Core logic for agent tools.
- **`mwb_api.py`**: Wrapper for Metabolomics Workbench API calls.
- **Analysis Modules**: `perform_volcano_plot_analysis.py` and `perform_clustered_heatmap_analysis.py` handle heavy-duty plotting (Note: These are generally treated as read-only).
- **Caching**: `datatable_cache.py` manages transient data references between tool calls.

---

## 2. Directory Structure

```
.
├── .chainlit                       # Chainlit configuration and assets
├── agent_message_utils.py          # Helpers for translating LangChain/Chainlit message payloads.
├── AGENTS.md                       # This file (Instructional context for AI agents)
├── app.py                          # Chainlit app with a LangChain agent.
├── chainlit.md                     # Chainlit help documentation
├── compound_tool_logic.py          # Tool logic for compound context.
├── datatable_cache.py              # Helpers for caching analysis datatables.
├── Dockerfile                      # Docker configuration file
├── gene_protein_tool_logic.py      # Tool logic for gene/protein context.
├── metstat_tool_logic.py           # Tool logic for MetStat context.
├── moverz_tool_logic.py            # Tool logic for MS/moverz context.
├── mwb_api.py                      # Wrapper for Metabolomics Workbench API.
├── perform_clustered_heatmap_analysis.py # Heatmap plotting module.
├── perform_volcano_plot_analysis.py # Volcano plotting module.
├── pyproject.toml                  # UV Project configuration.
├── README.md                       # Project description and user setup.
├── refmet_tool_logic.py            # Tool logic for RefMet context.
├── study_summary_formatter.py      # Formatting helpers for study summaries.
├── study_tool_logic.py             # Tool logic for study context.
├── tests/                          # Directory for test files.
├── uv.lock                         # UV Lock file.
└── verbose_logging.py              # Verbose logging helpers.
```

---

## 3. Development Workflow & Commands

### Environment Configuration
The following environment variables are required for development:
- `BASE_URL`: OpenAI-compatible API endpoint.
- `API_KEY` or `OPENAI_API_KEY`: Your API key.
- `MODEL`: The LLM to use (e.g., `gpt-4o-mini`).
- `VERBOSE_UI_LOGGING`: (Optional) `"true"` to enable debug logs.

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

### Restricted Files
Do **not** modify or write tests for the following files unless explicitly directed:
- `perform_clustered_heatmap_analysis.py`
- `perform_volcano_plot_analysis.py`

---

## 5. Lessons Learned & Hints
- **API Response Handling:** The Metabolomics Workbench REST API often returns data as a list of objects or a single object. Ensure `_get` handles JSON correctly.
- **Tabular Data:** For `datatable` endpoints, use `pandas.read_csv(StringIO(response.text), sep="\t")` as the API returns TSV format.
- **Environment Setup:** Always run `uv sync --group test` before running tests to ensure `pytest` and its plugins are available.
- **Tool Sequence:** The agent's core workflow for analysis is strictly: `get_study_summary` -> `get_study_analysis_information` -> `get_analysis_datatable` -> Analysis Tool.

---

## 6. Common Workflows
- **Fetching Study Data:** `get_study_summary` -> `get_study_analysis_information` -> `get_analysis_datatable`.
- **Generating Plots:** After obtaining a `datatable_ref`, call `create_volcano_plot_analysis` or `create_clustered_heatmap_analysis`.
- **UI Updates:** Modify `app.py` for message handling and `agent_message_utils.py` for payload extraction.
