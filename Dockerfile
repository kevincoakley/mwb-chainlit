FROM python:3.12-slim-trixie

# The installer requires curl (and certificates) to download the release archive
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Copy the project into the image
ADD . /app

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app
RUN uv sync --locked

# Expose port
EXPOSE 8000

# Set environment
ENV BASE_URL="https://localhost/v1"
ENV MCP_NAME="MPC NAME"
ENV MCP_URL="https://mcp.com/mcp"
ENV MODEL="model"
ENV PROMPT_INSTRUCTION="You are a helpful assistant."

# Presuming there is a `my_app` command provided by the project
CMD ["uv", "run", "chainlit", "run", "--host", "0.0.0.0", "--port", "8000", "app.py", "-h"]