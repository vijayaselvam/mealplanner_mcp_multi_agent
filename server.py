"""
🍽️ Meal Planner MCP Server - A Multimodal Agent using FastMCP

This MCP server provides tools to:
1. Analyze fridge/pantry images to identify ingredients (multimodal - image input)
2. Suggest recipes based on available ingredients
3. Get nutritional information for recipes

It demonstrates the MCP concepts of:
- Tools: Functions the LLM can call
- Resources: Read-only data the LLM can access
- Prompts: Reusable prompt templates

Uses Google Gemini for vision (image understanding) capabilities.
"""

import base64
import json
import logging
import os
import signal
import sys
import threading
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import FastMCP
from google import genai

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY not found. "
        "Copy .env.example to .env and add your key from https://aistudio.google.com/apikey"
    )

gemini_client = genai.Client(api_key=GOOGLE_API_KEY)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash") 

mcp = FastMCP(
    "MealPlanner",
    instructions=(
        "You are a helpful meal planning assistant. "
        "Use the available tools to analyze fridge photos, suggest recipes, "
        "and provide nutrition information. Always be encouraging and helpful!"
    ),
)

# In-memory recipe database
RECIPE_DATABASE = {
    "pasta_primavera": {
        "name": "Pasta Primavera",
        "ingredients": ["pasta", "bell pepper", "zucchini", "tomato", "garlic", "olive oil", "parmesan"],
        "cuisine": "Italian",
        "prep_time": "25 mins",
        "difficulty": "Easy",
        "instructions": [
            "Cook pasta according to package directions.",
            "Sauté garlic in olive oil for 1 minute.",
            "Add chopped vegetables and cook for 5-7 minutes.",
            "Toss with drained pasta and top with parmesan.",
        ],
        "nutrition": {
            "calories": 420,
            "protein": "14g",
            "carbs": "62g",
            "fat": "12g",
            "fiber": "5g",
        },
    },
    "chicken_stir_fry": {
        "name": "Chicken Stir Fry",
        "ingredients": ["chicken", "broccoli", "soy sauce", "garlic", "ginger", "rice", "sesame oil"],
        "cuisine": "Asian",
        "prep_time": "20 mins",
        "difficulty": "Easy",
        "instructions": [
            "Cook rice according to package directions.",
            "Slice chicken into thin strips and stir-fry in sesame oil.",
            "Add minced garlic and ginger, cook 1 minute.",
            "Add broccoli florets and soy sauce, cook until tender-crisp.",
            "Serve over rice.",
        ],
        "nutrition": {
            "calories": 480,
            "protein": "35g",
            "carbs": "52g",
            "fat": "14g",
            "fiber": "4g",
        },
    },
    "vegetable_omelette": {
        "name": "Vegetable Omelette",
        "ingredients": ["eggs", "bell pepper", "onion", "cheese", "mushroom", "butter"],
        "cuisine": "American",
        "prep_time": "10 mins",
        "difficulty": "Easy",
        "instructions": [
            "Whisk eggs with a splash of milk.",
            "Melt butter in a non-stick pan over medium heat.",
            "Sauté diced vegetables for 2-3 minutes.",
            "Pour in egg mixture and cook until edges set.",
            "Add cheese, fold, and serve.",
        ],
        "nutrition": {
            "calories": 320,
            "protein": "22g",
            "carbs": "8g",
            "fat": "24g",
            "fiber": "2g",
        },
    },
    "tomato_soup": {
        "name": "Classic Tomato Soup",
        "ingredients": ["tomato", "onion", "garlic", "basil", "cream", "olive oil"],
        "cuisine": "American",
        "prep_time": "30 mins",
        "difficulty": "Easy",
        "instructions": [
            "Sauté diced onion and garlic in olive oil until soft.",
            "Add chopped tomatoes and cook for 15 minutes.",
            "Blend until smooth using an immersion blender.",
            "Stir in cream and fresh basil.",
            "Season with salt and pepper to taste.",
        ],
        "nutrition": {
            "calories": 220,
            "protein": "5g",
            "carbs": "18g",
            "fat": "15g",
            "fiber": "3g",
        },
    },
    "banana_smoothie": {
        "name": "Banana Protein Smoothie",
        "ingredients": ["banana", "milk", "yogurt", "honey", "ice"],
        "cuisine": "Global",
        "prep_time": "5 mins",
        "difficulty": "Easy",
        "instructions": [
            "Peel and slice banana.",
            "Add banana, milk, yogurt, and honey to a blender.",
            "Add a handful of ice cubes.",
            "Blend until smooth and creamy.",
            "Pour into a glass and enjoy!",
        ],
        "nutrition": {
            "calories": 280,
            "protein": "12g",
            "carbs": "48g",
            "fat": "5g",
            "fiber": "3g",
        },
    },
    "grilled_cheese": {
        "name": "Grilled Cheese Sandwich",
        "ingredients": ["bread", "cheese", "butter"],
        "cuisine": "American",
        "prep_time": "10 mins",
        "difficulty": "Easy",
        "instructions": [
            "Butter one side of each bread slice.",
            "Place cheese between the unbuttered sides.",
            "Cook in a pan over medium heat until golden on each side.",
            "Slice diagonally and serve warm.",
        ],
        "nutrition": {
            "calories": 380,
            "protein": "15g",
            "carbs": "30g",
            "fat": "22g",
            "fiber": "1g",
        },
    },
    "fried_rice": {
        "name": "Egg Fried Rice",
        "ingredients": ["rice", "eggs", "soy sauce", "garlic", "green onion", "carrot", "sesame oil"],
        "cuisine": "Asian",
        "prep_time": "15 mins",
        "difficulty": "Easy",
        "instructions": [
            "Use day-old cooked rice for best results.",
            "Scramble eggs in sesame oil, set aside.",
            "Stir-fry diced carrots and garlic for 2 minutes.",
            "Add rice and soy sauce, toss until heated through.",
            "Mix in scrambled eggs and top with sliced green onions.",
        ],
        "nutrition": {
            "calories": 390,
            "protein": "14g",
            "carbs": "55g",
            "fat": "12g",
            "fiber": "2g",
        },
    },
    "caprese_salad": {
        "name": "Caprese Salad",
        "ingredients": ["tomato", "mozzarella", "basil", "olive oil", "balsamic vinegar"],
        "cuisine": "Italian",
        "prep_time": "10 mins",
        "difficulty": "Easy",
        "instructions": [
            "Slice tomatoes and mozzarella into even rounds.",
            "Arrange alternating on a plate with basil leaves.",
            "Drizzle with olive oil and balsamic vinegar.",
            "Season with salt and pepper.",
        ],
        "nutrition": {
            "calories": 280,
            "protein": "14g",
            "carbs": "8g",
            "fat": "22g",
            "fiber": "1g",
        },
    },
}

# Dietary profiles
DIETARY_PROFILES = {
    "vegetarian": {
        "name": "Vegetarian",
        "description": "No meat or fish",
        "excluded_ingredients": ["chicken", "beef", "pork", "fish", "shrimp", "lamb"],
    },
    "vegan": {
        "name": "Vegan",
        "description": "No animal products",
        "excluded_ingredients": [
            "chicken", "beef", "pork", "fish", "shrimp", "lamb",
            "eggs", "cheese", "milk", "cream", "butter", "yogurt",
            "honey", "mozzarella", "parmesan",
        ],
    },
    "low_carb": {
        "name": "Low Carb",
        "description": "Limited carbohydrates",
        "excluded_ingredients": ["pasta", "rice", "bread", "potato"],
    },
    "none": {
        "name": "No Restrictions",
        "description": "All foods allowed",
        "excluded_ingredients": [],
    },
}


@mcp.tool()
def identify_ingredients(image_path: str) -> str:
    """Analyze a photo of a fridge or pantry to identify visible food ingredients.

    This is the MULTIMODAL tool — it sends an image to Google Gemini's
    vision model and gets back a structured list of ingredients.

    Args:
        image_path: Absolute or relative path to the fridge/pantry image file.

    Returns:
        A JSON string containing the list of identified ingredients and their
        categories (produce, dairy, protein, pantry, etc.).
    """
    logging.info(f"Identifying ingredients from image: {image_path}")
    path = Path(image_path)
    if not path.exists():
        logging.error(f"Image not found: {image_path}")
        return json.dumps({"error": f"Image file not found: {image_path}"})

    # Read and encode the image
    image_bytes = path.read_bytes()
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    # Determine MIME type
    suffix = path.suffix.lower()
    mime_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/jpeg")

    # Call Gemini Vision API
    prompt = """Analyze this image of a fridge or pantry. Identify ALL visible food ingredients.

Return a JSON object with this exact structure:
{
    "ingredients": [
        {"name": "ingredient name", "category": "produce|dairy|protein|pantry|beverage|condiment|frozen", "quantity": "estimated quantity"}
    ],
    "total_count": <number>,
    "freshness_notes": "any observations about freshness or storage"
}

Be thorough and identify every visible food item. Use simple, common ingredient names."""

    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": mime_type, "data": image_base64}},
                ]
            }
        ],
    )

    # Clean the response (Gemini sometimes wraps JSON in markdown code blocks)
    result_text = response.text.strip()
    if result_text.startswith("```"):
        result_text = result_text.split("\n", 1)[1]  # Remove first line
        result_text = result_text.rsplit("```", 1)[0]  # Remove last ```

    return result_text


@mcp.tool()
def suggest_recipes(ingredients: list[str], dietary_preference: str = "none") -> str:
    """Suggest recipes based on available ingredients and dietary preferences.

    Matches the provided ingredients against a built-in recipe database and
    returns recipes that can be made (fully or partially) with what's available.

    Args:
        ingredients: List of ingredient names (e.g., ["eggs", "cheese", "tomato"]).
        dietary_preference: One of "none", "vegetarian", "vegan", or "low_carb".

    Returns:
        A JSON string with matched recipes, showing match percentage and
        any missing ingredients.
    """
    logging.info(f"Suggesting recipes for ingredients: {ingredients} with diet: {dietary_preference}")
    ingredients_lower = [i.lower().strip() for i in ingredients]

    # Get dietary restrictions
    profile = DIETARY_PROFILES.get(dietary_preference, DIETARY_PROFILES["none"])
    excluded = set(profile["excluded_ingredients"])

    matched_recipes = []

    for recipe_id, recipe in RECIPE_DATABASE.items():
        # Skip recipes that contain excluded ingredients
        recipe_ingredients = set(recipe["ingredients"])
        if recipe_ingredients & excluded:
            continue

        # Calculate match score (using partial/fuzzy matching)
        available = []
        missing = []
        for req_ing in recipe["ingredients"]:
            req_lower = req_ing.lower()
            if any(req_lower in fridge_ing or fridge_ing in req_lower for fridge_ing in ingredients_lower):
                available.append(req_ing)
            else:
                missing.append(req_ing)
                
        match_pct = len(available) / len(recipe["ingredients"]) * 100

        if match_pct >= 40:  # At least 40% ingredient match
            matched_recipes.append({
                "recipe_id": recipe_id,
                "name": recipe["name"],
                "cuisine": recipe["cuisine"],
                "prep_time": recipe["prep_time"],
                "difficulty": recipe["difficulty"],
                "match_percentage": round(match_pct, 1),
                "available_ingredients": available,
                "missing_ingredients": missing,
            })

    # Sort by match percentage (best matches first)
    matched_recipes.sort(key=lambda x: x["match_percentage"], reverse=True)

    result = {
        "dietary_preference": profile["name"],
        "total_matches": len(matched_recipes),
        "recipes": matched_recipes,
        "tip": "Recipes are sorted by how well they match your available ingredients.",
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def get_nutrition(recipe_name: str) -> str:
    """Get detailed nutritional information for a specific recipe.

    Args:
        recipe_name: The recipe ID or name (e.g., "pasta_primavera" or "Pasta Primavera").

    Returns:
        A JSON string with nutritional details, full instructions, and health tips.
    """
    logging.info(f"Fetching nutrition for recipe: {recipe_name}")
    recipe = None
    search = recipe_name.lower().strip()

    for recipe_id, r in RECIPE_DATABASE.items():
        if search == recipe_id or search == r["name"].lower():
            recipe = r
            break

    if not recipe:
        # Fuzzy match: check if the search term is contained in any recipe name
        for recipe_id, r in RECIPE_DATABASE.items():
            if search in r["name"].lower() or search in recipe_id:
                recipe = r
                break

    if not recipe:
        return json.dumps({
            "error": f"Recipe '{recipe_name}' not found.",
            "available_recipes": [r["name"] for r in RECIPE_DATABASE.values()],
        })

    result = {
        "recipe": recipe["name"],
        "cuisine": recipe["cuisine"],
        "prep_time": recipe["prep_time"],
        "difficulty": recipe["difficulty"],
        "ingredients": recipe["ingredients"],
        "instructions": recipe["instructions"],
        "nutrition": recipe["nutrition"],
        "health_tips": _generate_health_tips(recipe["nutrition"]),
    }

    return json.dumps(result, indent=2)


@mcp.tool()
def get_meal_plan(ingredients: list[str], meals_per_day: int = 3, dietary_preference: str = "none") -> str:
    """Generate a simple daily meal plan based on available ingredients.

    Args:
        ingredients: List of available ingredient names.
        meals_per_day: Number of meals to plan (1-5, default 3).
        dietary_preference: Dietary restriction ("none", "vegetarian", "vegan", "low_carb").

    Returns:
        A JSON string with a suggested daily meal plan.
    """
    logging.info(f"Generating meal plan for {meals_per_day} meals")
    meals_per_day = max(1, min(5, meals_per_day))

    # Get matching recipes
    recipes_json = suggest_recipes(ingredients, dietary_preference)
    recipes_data = json.loads(recipes_json)

    available_recipes = recipes_data.get("recipes", [])

    meal_labels = ["Breakfast", "Lunch", "Snack", "Dinner", "Late Snack"]
    plan = []

    for i in range(meals_per_day):
        label = meal_labels[i] if i < len(meal_labels) else f"Meal {i + 1}"

        if i < len(available_recipes):
            recipe = available_recipes[i]
            plan.append({
                "meal": label,
                "recipe": recipe["name"],
                "match": f"{recipe['match_percentage']}%",
                "missing": recipe["missing_ingredients"],
            })
        else:
            plan.append({
                "meal": label,
                "recipe": "No matching recipe found",
                "suggestion": "Consider adding more ingredients to your pantry!",
            })

    total_calories = 0
    for p in plan:
        recipe_name = p.get("recipe", "")
        for r in RECIPE_DATABASE.values():
            if r["name"] == recipe_name:
                total_calories += r["nutrition"]["calories"]
                break

    result = {
        "meal_plan": plan,
        "estimated_total_calories": total_calories,
        "dietary_preference": dietary_preference,
        "note": "This is a suggestion based on available ingredients. Adjust portions as needed!",
    }

    return json.dumps(result, indent=2)


@mcp.resource("recipes://all")
def get_all_recipes() -> str:
    """Get the complete recipe database with all available recipes."""
    recipes_summary = []
    for recipe_id, recipe in RECIPE_DATABASE.items():
        recipes_summary.append({
            "id": recipe_id,
            "name": recipe["name"],
            "cuisine": recipe["cuisine"],
            "prep_time": recipe["prep_time"],
            "difficulty": recipe["difficulty"],
            "ingredients": recipe["ingredients"],
        })
    return json.dumps(recipes_summary, indent=2)


@mcp.resource("dietary://profiles")
def get_dietary_profiles() -> str:
    """Get all available dietary profiles and their restrictions."""
    return json.dumps(DIETARY_PROFILES, indent=2)


@mcp.resource("recipes://{recipe_id}")
def get_recipe_by_id(recipe_id: str) -> str:
    """Get details for a specific recipe by its ID.

    Args:
        recipe_id: The recipe identifier (e.g., "pasta_primavera").
    """
    recipe = RECIPE_DATABASE.get(recipe_id)
    if recipe:
        return json.dumps(recipe, indent=2)
    return json.dumps({"error": f"Recipe '{recipe_id}' not found"})


@mcp.prompt()
def analyze_fridge(image_path: str) -> str:
    """Create a prompt for analyzing a fridge photo and suggesting meals.

    Args:
        image_path: Path to the fridge image to analyze.
    """
    return f"""Please help me plan meals based on what's in my fridge!

Steps to follow:
1. First, use the `identify_ingredients` tool with the image at: {image_path}
2. Then, use `suggest_recipes` with the identified ingredients
3. Finally, use `get_nutrition` for the top recipe suggestion

Present the results in a friendly, organized way with emojis!"""


@mcp.prompt()
def weekly_meal_prep(dietary_preference: str = "none") -> str:
    """Create a prompt for weekly meal prep planning.

    Args:
        dietary_preference: Dietary restriction to follow.
    """
    return f"""Help me plan a week of meals with a {dietary_preference} diet!

1. First, check available recipes using the `recipes://all` resource
2. Review dietary restrictions from `dietary://profiles`
3. Suggest a variety of meals covering different cuisines
4. Provide nutrition information for each suggested meal

Make it fun and include tips for meal prepping efficiently! 🍳"""


def _generate_health_tips(nutrition: dict) -> list[str]:
    """Generate simple health tips based on nutritional values."""
    tips = []
    calories = nutrition.get("calories", 0)
    protein = int(nutrition.get("protein", "0g").replace("g", ""))
    fiber = int(nutrition.get("fiber", "0g").replace("g", ""))

    if calories < 300:
        tips.append("🟢 Low-calorie option — great for weight management!")
    elif calories > 500:
        tips.append("🟡 Higher calorie meal — consider a lighter next meal.")

    if protein >= 20:
        tips.append("💪 Good protein content — great for muscle recovery!")

    if fiber >= 4:
        tips.append("🌿 High in fiber — supports digestive health!")

    tips.append("💧 Remember to stay hydrated throughout the day!")

    return tips


def _listen_for_exit():
    """Wait for user to type 'exit' to gracefully shut down the server."""
    while True:
        try:
            if input().strip().lower() == "exit":
                logging.info("Exit command received. Shutting down...")
                os.kill(os.getpid(), signal.SIGINT)
                break
        except (EOFError, KeyboardInterrupt):
            break

if __name__ == "__main__":
    logging.info("Starting server. Type 'exit' and press Enter to stop.")
    
    # Start background thread to listen for 'exit'
    exit_thread = threading.Thread(target=_listen_for_exit, daemon=True)
    exit_thread.start()
    
    try:
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=8000,
        )
    except KeyboardInterrupt:
        # Suppress the traceback that occurs when we send SIGINT
        pass
