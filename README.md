# mwb-chainlit

Simple Chainlit app that uses a LangChain agent and an OpenAI-compatible model endpoint to answer metabolomics questions and generate volcano plot and clustered heatmap PNGs via `mwb_api.py`, `perform_volcano_plot_analysis.py`, and `perform_clustered_heatmap_analysis.py`.

## Requirements

- Python 3.12+
- `uv`
- OpenAI-compatible API endpoint and model access

## Setup

```bash
uv sync --group test
```

## Run in Development

```bash
export BASE_URL="https://your-openai-compatible-endpoint/v1"
export API_KEY="your-api-key"
export MODEL="gpt-4o-mini"
export VERBOSE_UI_LOGGING="true"  # optional: show tool/LLM debug logs in UI + console
uv run chainlit run app.py -w
```

Then open the Chainlit URL shown in the terminal.
Example prompts:
- `Create a volcano plot analysis from study ST000001`
- `Create a clustered heatmap analysis from study ST000001`
Generated plot images are saved under `generated_plots/` and displayed in the chat with study summary details.

## Run Tests

```bash
uv run pytest
```

Optional coverage:

```bash
uv run pytest --cov=.
```

## Run in Production with Docker

Build image:

```bash
docker build -t mwb-chainlit:latest .
```

Run container:

```bash
docker run \
  --name mwb-chainlit \
  --rm \
  -p 8000:8000 \
  -e BASE_URL="https://your-openai-compatible-endpoint/v1" \
  -e API_KEY="your-api-key" \
  -e MODEL="gpt-4o-mini" \
  -e VERBOSE_UI_LOGGING="true" \
  mwb-chainlit:latest
```
