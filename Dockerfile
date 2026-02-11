FROM python:3.12-slim-trixie

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates

ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin/:$PATH"

ADD . /app
WORKDIR /app
RUN uv sync --locked

EXPOSE 8000

# Set environment
ENV BASE_URL="https://localhost/v1"
ENV API_KEY="your_api_key_here"
ENV MODEL="model"

CMD ["uv", "run", "chainlit", "run", "--host", "0.0.0.0", "--port", "8000", "app.py"]
