# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set the working directory in the container
WORKDIR /app

# Copy the dependency files
COPY pyproject.toml uv.lock ./

# Install the project dependencies
RUN uv sync --frozen --no-install-project

# Copy the rest of the application
COPY . .
RUN uv sync --frozen

# Expose any ports if needed (e.g., for SSE transport, usually 8000)
# EXPOSE 8000

# The base entrypoint runs the server. By default, fastmcp uses 'stdio' mode.
# To run in HTTP mode, pass `--transport streamable-http --host 0.0.0.0` when running the container.
ENTRYPOINT ["uv", "run", "fastmcp", "run", "server.py"]
