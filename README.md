# mwb-chainlit

This project is a Chainlit application that integrates with a Model Control Plane (MCP) to provide AI-powered functionalities. The application is containerized using Docker for easy deployment.

## Environment Variables

- `BASE_URL`: The base URL for the OpenAI-compatible API endpoint.
- `API_KEY`: The API key for authenticating with the OpenAI-compatible API.
- `MCP_NAME`: The display name for the MCP connection.
- `MCP_URL`: The URL of the streamable HTTP MCP server.
- `MODEL`: The model to use for chat completions (e.g., "gpt-4", "gpt-3.5-turbo").
- `PROMPT_INSTRUCTION`: The instruction to use for the LLM prompt.

## Build Docker Image
To build the Docker image for the application, run the following command in the terminal:

```bash
docker build -t mwb-chainlit:latest .
```

## Run Docker Container
To run the Docker container, use the following command, replacing the environment variable values as needed:

```bash
docker run \
  --name mwb-chainlit \
  --rm \
  -p 8000:8000 \
  -e BASE_URL="" \
  -e API_KEY="" \
  -e MCP_NAME="" \
  -e MCP_URL="" \
  -e MODEL="" \
  -e PROMPT_INSTRUCTION="You are a helpful assistant." \
  mwb-chainlit:latest
```

## Run Development Server

To run the development server locally witho ut Docker, use the following command:

```bash
uv run chainlit run app.py -w 
```

## Upgrade Chainlit

To upgrade Chainlit to the latest version, use the following command:

```bash
uv lock --upgrade-package chainlit
```