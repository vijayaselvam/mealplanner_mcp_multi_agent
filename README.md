# 🍽️ MealPlanner MCP Multi-Agent

A **multimodal meal planning agent** built using [FastMCP](https://gofastmcp.com/) (Model Context Protocol). It demonstrates how to build an MCP server with **image analysis** (via Google Gemini Vision), **tools**, **resources**, and **prompts**.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    MCP Client (client.py)                 │
│  Connects to server, calls tools, reads resources        │
└─────────────────────────┬────────────────────────────────┘
                          │  MCP Protocol (stdio)
┌─────────────────────────▼────────────────────────────────┐
│               MCP Server (server.py)                      │
│                                                           │
│  🔧 Tools:                                               │
│    • identify_ingredients(image) → Gemini Vision API     │
│    • suggest_recipes(ingredients, diet)                   │
│    • get_nutrition(recipe_name)                           │
│    • get_meal_plan(ingredients, meals, diet)              │
│                                                           │
│  📦 Resources:                                           │
│    • recipes://all → Full recipe database                │
│    • recipes://{id} → Single recipe details              │
│    • dietary://profiles → Dietary restrictions           │
│                                                           │
│  💬 Prompts:                                             │
│    • analyze_fridge → Image analysis workflow            │
│    • weekly_meal_prep → Meal prep planning               │
│                                                           │
│  🧠 External API:                                        │
│    • Google Gemini 2.0 Flash (Vision/Multimodal)         │
└──────────────────────────────────────────────────────────┘
```

---

## 🔄 End-to-End Workflow

### High-Level Sequence

```
 ┌────────┐        ┌────────────┐       ┌────────────┐       ┌────────────┐
 │  User  │        │ MCP Client │       │ MCP Server │       │  Gemini    │
 │        │        │ (client.py)│       │ (server.py)│       │  Vision    │
 └───┬────┘        └─────┬──────┘       └─────┬──────┘       └─────┬──────┘
     │                   │                    │                     │
     │  1. Run client    │                    │                     │
     │  with --image     │                    │                     │
     │──────────────────>│                    │                     │
     │                   │                    │                     │
     │                   │ 2. Connect via     │                     │
     │                   │    stdio transport │                     │
     │                   │───────────────────>│                     │
     │                   │                    │                     │
     │                   │ 3. list_tools()    │                     │
     │                   │    list_resources()│                     │
     │                   │    list_prompts()  │                     │
     │                   │───────────────────>│                     │
     │                   │<──────────────────-│                     │
     │                   │  (capabilities)    │                     │
     │                   │                    │                     │
     │                   │ 4. read_resource   │                     │
     │                   │  ("recipes://all") │                     │
     │                   │───────────────────>│                     │
     │                   │<──────────────────-│                     │
     │                   │   (8 recipes)      │                     │
     │                   │                    │                     │
     │                   │ 5. call_tool       │                     │
     │                   │  identify_         │                     │
     │                   │  ingredients(img)  │                     │
     │                   │───────────────────>│  6. Send image     │
     │                   │                    │     + prompt        │
     │                   │                    │────────────────────>│
     │                   │                    │<────────────────────│
     │                   │                    │  7. Ingredients JSON│
     │                   │<──────────────────-│                     │
     │                   │  (ingredients list)│                     │
     │                   │                    │                     │
     │                   │ 8. call_tool       │                     │
     │                   │  suggest_recipes() │                     │
     │                   │───────────────────>│                     │
     │                   │<──────────────────-│                     │
     │                   │ (matched recipes)  │                     │
     │                   │                    │                     │
     │                   │ 9. call_tool       │                     │
     │                   │  get_nutrition()   │                     │
     │                   │───────────────────>│                     │
     │                   │<──────────────────-│                     │
     │                   │  (nutrition info)  │                     │
     │                   │                    │                     │
     │                   │ 10. call_tool      │                     │
     │                   │  get_meal_plan()   │                     │
     │                   │───────────────────>│                     │
     │                   │<──────────────────-│                     │
     │                   │   (daily plan)     │                     │
     │                   │                    │                     │
     │  11. Print results│                    │                     │
     │<──────────────────│                    │                     │
     │  (formatted output)                   │                     │
```

### Step-by-Step Data Flow

---

#### Step 1: Client Connects to Server

```python
# client.py — The client starts the server as a subprocess via stdio
client = Client("server.py")

async with client:
    # Connection is established using MCP protocol over stdio
    # FastMCP auto-handles: handshake, capability negotiation, lifecycle
```

**What happens internally:**
- `Client("server.py")` tells FastMCP to launch `server.py` as a **subprocess**
- Communication happens over **stdin/stdout** (stdio transport)
- MCP protocol handshake occurs automatically
- Client discovers server name: `"MealPlanner"`

---

#### Step 2: Discover Server Capabilities

```python
# client.py — Ask the server what it can do
tools = await client.list_tools()           # → 4 tools
resources = await client.list_resources()    # → 2 static resources
templates = await client.list_resource_templates()  # → 1 template
prompts = await client.list_prompts()        # → 2 prompts
```

**Server responds with:**

| Type | Name | Description |
|------|------|-------------|
| 🔧 Tool | `identify_ingredients` | Analyze fridge photo → ingredients (multimodal) |
| 🔧 Tool | `suggest_recipes` | Match ingredients → recipes |
| 🔧 Tool | `get_nutrition` | Recipe → nutritional info |
| 🔧 Tool | `get_meal_plan` | Ingredients → daily meal plan |
| 📦 Resource | `recipes://all` | Full recipe database (8 recipes) |
| 📦 Resource | `dietary://profiles` | 4 dietary profiles |
| 📄 Template | `recipes://{recipe_id}` | Lookup single recipe by ID |
| 💬 Prompt | `analyze_fridge` | Guided fridge analysis workflow |
| 💬 Prompt | `weekly_meal_prep` | Weekly planning template |

---

#### Step 3: Read Resources (Recipe Database & Dietary Profiles)

```python
# client.py — Read the recipe database
recipes = await client.read_resource("recipes://all")
```

**Server processing (server.py):**
```python
@mcp.resource("recipes://all")
def get_all_recipes() -> str:
    # Iterates RECIPE_DATABASE dict → returns JSON summary of 8 recipes
    # Each recipe has: id, name, cuisine, prep_time, difficulty, ingredients
```

**Data returned:**
```json
[
  {"id": "pasta_primavera", "name": "Pasta Primavera", "cuisine": "Italian", ...},
  {"id": "chicken_stir_fry", "name": "Chicken Stir Fry", "cuisine": "Asian", ...},
  {"id": "vegetable_omelette", "name": "Vegetable Omelette", ...},
  // ... 8 recipes total
]
```

---

#### Step 4: Multimodal — Identify Ingredients from Fridge Photo 📸

This is the **core multimodal step** where an image is analyzed.

```python
# client.py — Send fridge image for analysis
result = await client.call_tool(
    "identify_ingredients",
    {"image_path": "/path/to/fridge_photo.jpg"}
)
```

**Server processing (server.py) — 4 sub-steps:**

```
┌─────────────────────────────────────────────────────────────────┐
│                 identify_ingredients(image_path)                 │
│                                                                  │
│  Step A: Read image file from disk                              │
│          image_bytes = Path(image_path).read_bytes()             │
│                                                                  │
│  Step B: Encode to base64                                       │
│          image_base64 = base64.b64encode(image_bytes)            │
│          Detect MIME type: .jpg → "image/jpeg"                  │
│                                                                  │
│  Step C: Send to Google Gemini Vision API                       │
│          gemini_client.models.generate_content(                  │
│              model="gemini-2.0-flash",                          │
│              contents=[text_prompt + inline_image_data]          │
│          )                                                       │
│                                                                  │
│  Step D: Parse & return structured JSON                         │
│          Clean markdown code blocks from response               │
│          Return ingredients list as JSON string                  │
└─────────────────────────────────────────────────────────────────┘
```

**The prompt sent to Gemini:**
```
Analyze this image of a fridge or pantry. Identify ALL visible food ingredients.
Return a JSON object with this structure:
{
    "ingredients": [
        {"name": "...", "category": "produce|dairy|protein|...", "quantity": "..."}
    ],
    "total_count": <number>,
    "freshness_notes": "..."
}
```

**Example response from Gemini:**
```json
{
  "ingredients": [
    {"name": "eggs", "category": "protein", "quantity": "6 eggs"},
    {"name": "milk", "category": "dairy", "quantity": "1 carton"},
    {"name": "tomato", "category": "produce", "quantity": "3 pieces"},
    {"name": "cheese", "category": "dairy", "quantity": "1 block"},
    {"name": "butter", "category": "dairy", "quantity": "1 stick"}
  ],
  "total_count": 5,
  "freshness_notes": "All items appear fresh and well-stored"
}
```

---

#### Step 5: Suggest Recipes Based on Ingredients

```python
# client.py — Pass identified ingredients to recipe matcher
result = await client.call_tool(
    "suggest_recipes",
    {"ingredients": ["eggs", "milk", "tomato", "cheese", "butter"],
     "dietary_preference": "none"}
)
```

**Server processing (server.py):**

```
┌─────────────────────────────────────────────────────────────────┐
│          suggest_recipes(ingredients, dietary_preference)         │
│                                                                  │
│  1. Normalize ingredients → lowercase                           │
│                                                                  │
│  2. Load dietary profile                                        │
│     "none" → no excluded ingredients                            │
│     "vegan" → excludes eggs, cheese, milk, butter, etc.         │
│                                                                  │
│  3. For EACH recipe in RECIPE_DATABASE (8 recipes):             │
│     a. Skip if recipe has excluded ingredients                  │
│     b. Count how many recipe ingredients are available          │
│     c. Calculate match % = available / total × 100              │
│     d. Include if match ≥ 40%                                   │
│                                                                  │
│  4. Sort by match_percentage (highest first)                    │
│                                                                  │
│  5. Return: recipe name, match %, available & missing items     │
└─────────────────────────────────────────────────────────────────┘
```

**Example output:**
```json
{
  "dietary_preference": "No Restrictions",
  "total_matches": 4,
  "recipes": [
    {
      "name": "Vegetable Omelette",
      "match_percentage": 66.7,
      "available_ingredients": ["eggs", "cheese", "butter"],
      "missing_ingredients": ["bell pepper", "onion", "mushroom"]
    },
    {
      "name": "Grilled Cheese Sandwich",
      "match_percentage": 66.7,
      "available_ingredients": ["cheese", "butter"],
      "missing_ingredients": ["bread"]
    }
  ]
}
```

---

#### Step 6: Get Nutrition Info for Top Recipe

```python
# client.py — Get nutrition for the best match
result = await client.call_tool(
    "get_nutrition",
    {"recipe_name": "vegetable_omelette"}
)
```

**Server processing (server.py):**

```
┌─────────────────────────────────────────────────────────────────┐
│                  get_nutrition(recipe_name)                       │
│                                                                  │
│  1. Search RECIPE_DATABASE by ID or name (case-insensitive)     │
│  2. If not found → fuzzy match (partial string match)           │
│  3. Return full recipe details:                                 │
│     - Ingredients list                                          │
│     - Step-by-step cooking instructions                         │
│     - Nutrition: calories, protein, carbs, fat, fiber           │
│     - Auto-generated health tips based on values                │
└─────────────────────────────────────────────────────────────────┘
```

**Example output:**
```json
{
  "recipe": "Vegetable Omelette",
  "nutrition": {
    "calories": 320,
    "protein": "22g",
    "carbs": "8g",
    "fat": "24g",
    "fiber": "2g"
  },
  "instructions": [
    "Whisk eggs with a splash of milk.",
    "Melt butter in a non-stick pan over medium heat.",
    "Sauté diced vegetables for 2-3 minutes.",
    "Pour in egg mixture and cook until edges set.",
    "Add cheese, fold, and serve."
  ],
  "health_tips": [
    "💪 Good protein content — great for muscle recovery!",
    "💧 Remember to stay hydrated throughout the day!"
  ]
}
```

---

#### Step 7: Generate Daily Meal Plan

```python
# client.py — Create a full day's meal plan
result = await client.call_tool(
    "get_meal_plan",
    {"ingredients": ingredient_names, "meals_per_day": 3, "dietary_preference": "none"}
)
```

**Server processing (server.py):**

```
┌─────────────────────────────────────────────────────────────────┐
│      get_meal_plan(ingredients, meals_per_day, diet)             │
│                                                                  │
│  1. Internally calls suggest_recipes() to get matched recipes   │
│  2. Assigns recipes to meal slots:                              │
│     - Meal 1 → "Breakfast" (best match recipe)                 │
│     - Meal 2 → "Lunch" (2nd best match)                        │
│     - Meal 3 → "Dinner" (3rd best match)                       │
│  3. Calculates total estimated calories                         │
│  4. Returns structured meal plan                                │
└─────────────────────────────────────────────────────────────────┘
```

**Example output:**
```json
{
  "meal_plan": [
    {"meal": "Breakfast", "recipe": "Vegetable Omelette", "match": "66.7%"},
    {"meal": "Lunch", "recipe": "Grilled Cheese Sandwich", "match": "66.7%"},
    {"meal": "Dinner", "recipe": "Classic Tomato Soup", "match": "50.0%"}
  ],
  "estimated_total_calories": 920,
  "note": "This is a suggestion based on available ingredients. Adjust portions as needed!"
}
```

---

#### Step 8: Client Prints Formatted Results

The client formats all JSON responses into a **user-friendly terminal output** with emojis, colors, and clear sections.

---

### Complete Data Flow Diagram

```
    📸 Fridge Photo
         │
         ▼
  ┌──────────────┐     base64 + prompt     ┌──────────────┐
  │  MCP Server  │ ─────────────────────── │ Google Gemini │
  │  Tool:       │                          │ Vision API   │
  │  identify_   │ <─── JSON ingredients ── │ (2.0 Flash)  │
  │  ingredients │                          └──────────────┘
  └──────┬───────┘
         │ ["eggs", "tomato", "cheese", ...]
         ▼
  ┌──────────────┐
  │  MCP Server  │     Compares against
  │  Tool:       │ ──▶ RECIPE_DATABASE (8 recipes)
  │  suggest_    │ ──▶ DIETARY_PROFILES (4 profiles)
  │  recipes     │
  └──────┬───────┘
         │ [{name: "Omelette", match: 83%}, ...]
         ▼
  ┌──────────────┐
  │  MCP Server  │     Looks up recipe details
  │  Tool:       │ ──▶ Full instructions
  │  get_        │ ──▶ Nutrition data
  │  nutrition   │ ──▶ Health tips (auto-generated)
  └──────┬───────┘
         │ {calories: 320, protein: "22g", ...}
         ▼
  ┌──────────────┐
  │  MCP Server  │     Combines top recipes into
  │  Tool:       │ ──▶ Breakfast / Lunch / Dinner
  │  get_        │ ──▶ Calculates total calories
  │  meal_plan   │
  └──────┬───────┘
         │
         ▼
    📋 Complete Meal Plan
       with Nutrition Info
```

### Demo Mode vs Image Mode

| Aspect | Demo Mode (`python3 client.py`) | Image Mode (`python3 client.py --image photo.jpg`) |
|--------|------|------|
| Image analysis | ❌ Skipped | ✅ Calls Gemini Vision API |
| Ingredients | Hardcoded sample list (10 items) | Extracted from image by AI |
| API key needed | ❌ No (server loads but tool not called) | ✅ Yes (GOOGLE_API_KEY in .env) |
| Recipe matching | ✅ Works | ✅ Works |
| Nutrition info | ✅ Works | ✅ Works |
| Meal plan | ✅ Works | ✅ Works |

---

## 📁 Project Structure

```
mealplanner_mcp_multi_agent/
├── server.py          # MCP Server — tools, resources, prompts
├── client.py          # MCP Client — demo script (connects via HTTP)
├── pyproject.toml     # Project config & dependencies (uv)
├── uv.lock            # Locked dependency versions
├── .env.example       # Environment variable template
├── .python-version    # Python version pin
└── README.md          # This file
```

## 🚀 Setup

### 1. Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install dependencies

```bash
uv sync
```

This creates a `.venv` virtual environment and installs all dependencies from `pyproject.toml`.

### 3. Get a Google Gemini API key

- Visit [Google AI Studio](https://aistudio.google.com/apikey)
- Create a free API key
- Copy `.env.example` to `.env` and paste your key:

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

### 4. Start the MCP Server (Terminal 1)

```bash
uv run python3 server.py
```

The server starts at `http://127.0.0.1:8000/mcp` using **Streamable HTTP** transport.

### 5. Run the Client (Terminal 2)

```bash
# Demo mode (uses sample ingredients)
uv run python3 client.py

# With a real fridge photo (multimodal!)
uv run python3 client.py --image path/to/fridge_photo.jpg

# Connect to a custom server URL
uv run python3 client.py --url http://your-server:8000/mcp
```

### 6. Test with MCP Inspector

```bash
uv run fastmcp dev server.py
```

This opens a web UI where you can interactively test all tools, resources, and prompts.

## 🔧 MCP Concepts Demonstrated

| Concept | What It Does | Example in This Project |
|---------|-------------|------------------------|
| **Tools** | Functions the LLM can call | `identify_ingredients()` — sends image to Gemini |
| **Resources** | Read-only data for the LLM | `recipes://all` — browse recipe database |
| **Resource Templates** | Dynamic resources with parameters | `recipes://{recipe_id}` — get specific recipe |
| **Prompts** | Reusable prompt templates | `analyze_fridge` — guided fridge analysis workflow |

## 🖼️ Multimodal Feature

The `identify_ingredients` tool is the **multimodal** component:

1. Accepts an **image file path** (JPG, PNG, WebP)
2. Encodes the image to **base64**
3. Sends it to **Google Gemini 2.0 Flash** with a structured prompt
4. Returns a **JSON list** of identified ingredients with categories

This demonstrates how MCP tools can handle non-text inputs (images) alongside text.

## 📝 Example Output

```
============================================================
🍽️  Meal Planner MCP Client
============================================================

📋 Discovering server capabilities...

🔧 Available Tools:
   • identify_ingredients: Analyze a photo of a fridge or pantry...
   • suggest_recipes: Suggest recipes based on available ingredients...
   • get_nutrition: Get detailed nutritional information...
   • get_meal_plan: Generate a simple daily meal plan...

📦 Available Resources:
   • recipes://all: Recipe Database
   • dietary://profiles: Dietary Profiles

👨‍🍳 Suggesting Recipes:

   🟢 Vegetable Omelette (83.3% match)
   🟢 Caprese Salad (80.0% match)
   🟡 Classic Tomato Soup (66.7% match)
   🟡 Pasta Primavera (57.1% match)
   🟡 Grilled Cheese Sandwich (66.7% match)
```

## 🔑 Key Learning Points

1. **FastMCP simplifies MCP server creation** — just use `@mcp.tool()`, `@mcp.resource()`, `@mcp.prompt()` decorators
2. **Multimodal = image + text** — the server handles image encoding and sends to a vision API
3. **Tools vs Resources** — Tools perform actions (with side effects); Resources provide read-only data
4. **Prompts** — Reusable templates that guide the LLM through multi-step workflows
5. **Client connects via stdio** — FastMCP handles all the MCP protocol details automatically
