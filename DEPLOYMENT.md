# 🚀 MealPlanner MCP Deployment Guide

This guide provides simple, step-by-step instructions to deploy the MealPlanner MCP server using Docker.

## 1. 🐳 Docker Deployment (Start the Server)

1. **Set up your environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env to add your GOOGLE_API_KEY and GEMINI_MODEL (e.g., gemini-3.1-pro)
   ```

2. **Build and start the container:**
   ```bash
   docker build -t mealplanner-mcp .
   docker run -p 8000:8000 --rm --env-file .env mealplanner-mcp --transport streamable-http --host 0.0.0.0
   ```
   *The server is now running on `http://localhost:8000/mcp`.*

---

## 2. 🔌 Access Server/Client

Once the Docker server is running, open a **new terminal tab** and use the client script to connect to it.

```bash
# Demo mode
uv run python3 client.py

# Multimodal mode (analyze a real image)
uv run python3 client.py --image path/to/fridge_photo.jpg
```
*Note: The client connects via HTTP to the Docker container automatically.*

---

## 3. 📦 How Deployment Works & Details

* **Docker Image**: The `Dockerfile` starts with a lightweight `python:3.12-slim` image. It uses `uv` (a fast Python package manager) to quickly cache and install dependencies.
* **Environment Variables**: The `docker-compose.yml` automatically passes your `.env` variables (like your Google API key and chosen Gemini model) securely into the container.
* **Server Port**: The server runs on port 8000 using HTTP (`--transport streamable-http`). We expose this port using `-p 8000:8000` so external clients (like `client.py` or web apps) can access it.
* **Troubleshooting**: If you get a `429 RESOURCE_EXHAUSTED` error, you've hit the Gemini free tier limit. You can fix this by setting `GEMINI_MODEL=gemini-1.5-pro` (or `3.1-pro`) in your `.env` file and rebuilding the container.
