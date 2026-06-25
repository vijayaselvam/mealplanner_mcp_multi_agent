# 🚀 MealPlanner MCP Deployment Guide

This guide explains how to configure, deploy, run, and access the MealPlanner MCP Multi-Agent server using Docker.

## 🛠️ Step 1: Configure the Environment

The server requires a Google Gemini API key to run multimodal vision tasks (like identifying ingredients from a fridge photo).

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Open the `.env` file and add your Google API key:
   ```env
   GOOGLE_API_KEY=your_actual_api_key_here
   ```
   *(You can get an API key from [Google AI Studio](https://aistudio.google.com/apikey))*

---

## 🐳 Step 2: Build the Docker Image

You can build the Docker image using either standard Docker commands or Docker Compose.

**Option A: Using Docker Compose (Recommended)**
```bash
docker-compose build
```

**Option B: Using standard Docker**
```bash
docker build -t mealplanner-mcp .
```

---

## 🏃 Step 3: Run the MCP Server

MCP servers can run in two different modes. Choose the one that fits your use case.

### Mode A: Standard I/O (stdio) - Best for Desktop Clients
This is the default mode. It's used when you want a desktop app (like Claude Desktop) or a local script to use this agent as a tool. Communication happens over standard input/output.

**Run with Docker Compose:**
```bash
docker-compose run -i mcp-server
```

**Run with standard Docker:**
```bash
docker run -i --rm --env-file .env mealplanner-mcp
```
*Note: The terminal will appear to hang because it is silently waiting for JSON-RPC messages via standard input. This is normal.*

### Mode B: Server-Sent Events (SSE) - Best for Web / Remote Access
Use this mode if you want to deploy the agent to the cloud (e.g., AWS, Render) or access it over a network via HTTP.

**Run with standard Docker:**
```bash
docker run -p 8000:8000 --rm --env-file .env mealplanner-mcp --transport streamable-http --host 0.0.0.0
```
*(The `--host 0.0.0.0` flag is required so the server accepts connections from outside the Docker container!)*

---

## 🔌 Step 4: Access the MCP Server

Once the server is running, here is how you can connect to it.

### 1. Accessing via Claude Desktop (stdio mode)
To add this Dockerized MCP server to your Claude Desktop configuration, edit your Claude config file (usually located at `~/Library/Application Support/Claude/claude_desktop_config.json` on Mac) and add:

```json
{
  "mcpServers": {
    "MealPlanner": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "--env-file",
        "/absolute/path/to/mealplanner_mcp_multi_agent/.env",
        "mealplanner-mcp"
      ]
    }
  }
}
```
*Make sure to replace `/absolute/path/to/...` with the actual path to your `.env` file.*

### 2. Accessing via the Python Client (stdio mode)
You can modify the included `client.py` to point to the Docker container instead of the raw python script. In your `client.py`, update the `Client` connection:

```python
# Change this:
# client = Client("server.py")

# To this:
client = Client("docker run -i --rm --env-file .env mealplanner-mcp")
```

### 3. Accessing via HTTP (SSE mode)
If you started the server in SSE mode (on port 8000), external clients and HTTP inspectors can connect to it at:
```text
http://localhost:8000/sse
```
Clients supporting the MCP SSE transport can negotiate connections and call tools remotely through this URL. You can also run the provided python client script locally to connect to this server:
```bash
uv run client.py
```

---

## 📦 How the Docker Deployment Works (Step-by-Step)

The containerization of this application is optimized for speed and size using `uv`. Here is how the Docker deployment works under the hood:

1. **Base Environment (`FROM python:3.12-slim`)**: The image uses a slimmed-down Debian Linux base with Python 3.12 pre-installed to minimize the container's final size.
2. **Package Manager (`uv`)**: Rather than installing `pip`, it pulls the ultra-fast `uv` package manager directly from its official image (`ghcr.io/astral-sh/uv`).
3. **Layer Caching**: It copies *only* `pyproject.toml` and `uv.lock` first, then installs dependencies (`uv sync --no-install-project`). This creates a cached Docker layer. If you only modify your application code, Docker skips redownloading dependencies on the next build!
4. **Application Code**: The actual application files are copied into the `/app` directory, and a final `uv sync` installs the project itself.
5. **Entrypoint (`ENTRYPOINT ["uv", "run", "fastmcp", "run", "server.py"]`)**: The container is locked to run the MCP server. When you pass additional arguments (like `--transport streamable-http`), they are seamlessly appended to this underlying command.
6. **Orchestration (`docker-compose.yml`)**: Docker Compose automates the injection of your local `.env` variables (like `GOOGLE_API_KEY`) directly into the container, so you don't have to manually specify them on the command line every time.

---

## 🧠 How It Works (End-to-End Workflow)

When you run `uv run client.py` against your Docker server, here is the exact step-by-step process of what happens under the hood:

### 1. Connection & Discovery
* **Handshake**: The client connects to the Docker container over HTTP (port 8000). The MCP protocol handles capability negotiation behind the scenes.
* **Discovery**: The client asks the server what it can do. The server responds with a list of its:
   * **Tools** (e.g., `identify_ingredients`, `suggest_recipes`)
   * **Resources** (e.g., the local recipe database and dietary profiles)
   * **Prompts** (e.g., `analyze_fridge`)

### 2. Reading Context (Resources)
The client reads the `recipes://all` and `dietary://profiles` resources. This pulls the static JSON database of recipes from the Docker container so the client knows what meals are available to suggest.

### 3. Image Analysis (Multimodal AI)
* If you pass an image to the client, it reads the image file from your local computer and converts it into a Base64 string.
* The client calls the `identify_ingredients` tool on the Docker server, passing the Base64 image.
* The server sends the image and a strict system prompt to the **Google Gemini 2.0 Flash** API.
* Gemini analyzes the photo and returns a structured JSON list of visible ingredients (e.g., "eggs", "milk", "tomato").

### 4. Recipe Matching & Meal Planning
* The client takes the extracted ingredients from Gemini and passes them into the `suggest_recipes` tool.
* The server matches the available ingredients against its internal recipe database, calculating match percentages.
* Next, the client calls `get_nutrition` for the top suggested recipe.
* Finally, it calls `get_meal_plan` to generate a full daily eating schedule using the available foods.

### 5. Formatted Output
The client formats all this data nicely in your terminal, showing you exactly what it found in the fridge, what you can make, and the nutritional value!

---

## 🚑 Troubleshooting

- **`Client failed to connect` when using HTTP mode**: Ensure you included `--host 0.0.0.0` when running the Docker container. FastMCP binds to `127.0.0.1` inside the container by default, which blocks external connections.
- **`429 RESOURCE_EXHAUSTED` (Gemini API Error)**: If you are using a free-tier Google API key, you may hit rate limits (e.g., when analyzing multiple fridge photos or running the client script multiple times in quick succession). Wait a minute and try again, or upgrade your API tier.
- **`error: Failed to spawn: meal-server`**: If you see this when running the container, ensure you have rebuilt the image (`docker build -t mealplanner-mcp .`) after pulling the latest code, as the entrypoint has been updated to use the `fastmcp` CLI directly.
