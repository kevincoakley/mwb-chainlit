# AGENTS.md

> Purpose: This file provides context, conventions, and setup instructions for AI agents working on this repository.

## 1. Project Overview
- Description: This is a repository for a Chainlit application focused on metabolomics data analysis. The application will utilize AI agents to assist users in analyzing and interpreting metabolomics datasets.
- Language: Python
- Package Manager: `uv` (Do not use pip or poetry directly)

## 2. Directory Structure

```
.
├── .chainlit                       # Chainlit configuration and assets
├── .gitignore                      # Git ignore file
├── .python-version                 # UV Python version file
├── agent_message_utils.py          # Helpers for translating LangChain/Chainlit message payloads.
├── AGENTS.md                       # This file
├── app.py                          # Chainlit app with a LangChain agents backed by OpenAI-compatible APIs.
├── chainlit.md                     # Chainlit help documentation
├── datatable_cache.py              # Helpers for caching analysis datatables by generated references.
├── Dockerfile                      # Docker configuration file
├── mwb_api.py                      # Functions for interacting with the Metabolomics Workbench API
├── perform_clustered_heatmap_analysis.py # Functions for performing clustered heatmap analysis
├── perform_volcano_plot_analysis.py # Functions for performing volcano plot analysis
├── pyproject.toml                  # UV Project configuration
├── README.md                       # Project description
├── study_summary_formatting.py     # Formatting helpers for user-facing study summary content.
├── study_tool_logic.py             # LangChain agent tool logic used by Chainlit tool entrypoints.
├── tests/                          # Directory for test files
├── uv.lock                         # UV Lock file for dependencies
└── verbose_logging.py              # Verbose logging helpers shared by the Chainlit app
```

## 3. Development Workflow & Commands
Always use `uv` for package management and script execution.

### Setup
- First time setup: `uv sync` (Installs environment based on lockfile)
- Update environment: `uv sync`

### Dependency Management
- Add production dependency: `uv add <package_name>`
- Add dev/test dependency: `uv add <package_name> --group test`
- Remove dependency: `uv remove <package_name>`

### Running Code
- Run script: `uv run python <script_path>`

### Testing
- Install test environment: `uv sync --group test`
- Run all tests: `uv run pytest`
- Write tests for new features.
- Maintain existing test coverage.
- Use pytest fixtures for common setup.
- Create separate test files for each module.
- Create test in a `tests/` directory at the root level.
- Name test files as `test_<module>.py`
- Test coverage: `uv run pytest --cov=.`
- Tests should be minimal and focused on behavior, not implementation details.

## Development Process
1. Write/update tests first (TDD approach)
2. Implement changes
3. Run tests to ensure they pass
4. Format code with Black

## Excluded files
Do not modify the following files or write test for them, unless explicitly asked to do so:
- perform_clustered_heatmap_analysis.py
- perform_volcano_plot_analysis.py

## 4. Coding Conventions & Style

### Design Philosophy: Simplicity First
- Prefer simple, direct solutions over complex or abstract ones.
- Less code is generally better than more code, as long as readability is preserved.
- Avoid clever or overly compact statements that reduce clarity.
- Before adding new code, review the surrounding file and consider whether refactoring existing code can simplify the overall solution.
- When refactoring, aim to reduce duplication, nesting, and indirection rather than introducing new abstractions.
- Do not introduce additional dependencies or patterns unless they provide clear, measurable benefit.

### Formatting
- Formatter: Black
  - Command: `uv run black .`
  - Rule: Always run formatting before declaring a task complete.
- Follow PEP 8 conventions.
- Use type hints where appropriate.
- Write docstrings for functions and classes.

### Commenting
- Use clear and concise comments to explain non-obvious code.
- Use docstrings for all public modules, functions, classes, and methods.

### Type Hinting
- Use standard Python type hints for function arguments and return values.
- Example: `def my_func(name: str) -> int:`

### 5. Deployment
- The website will be deployed using Docker in production.
- The Dockerfile should be simple and efficient, using a lightweight Python base image.
- Don't include unnecessary files in the Docker image (use .dockerignore effectively).
- Update the Dockerfile when changes are made that might affect the production environment (e.g. new dependencies, changes to how the app is run).
- Update the README.md with instructions for running the code in production using Docker.

## 6. Critical Rules for Agents
- Do not update `uv.lock` manually. Use `uv add` or `uv sync`.
- Check `pyproject.toml` to see existing dependencies before adding new ones.
- Run tests after every significant code change to ensure no regressions.
- When multiple valid solutions exist, choose the simplest one that satisfies the requirements and existing design.
- Ensure code is formatted with Black.
- Preserve existing code style and patterns.
- Always update the README.md file with instructions for running the code. Be concise, don't include unnecessary information. Focus on how to run the code for testing (unit tests and dev server) and in production.
- Ask for clarification if requirements are unclear.
