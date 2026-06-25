"""
🍽️ Meal Planner MCP Client — Connects via Streamable HTTP

This client connects to the Meal Planner MCP server over HTTP and demonstrates:
1. Listing available tools, resources, and prompts
2. Calling the multimodal identify_ingredients tool with an image
3. Suggesting recipes based on identified ingredients
4. Getting nutrition information for a recipe
5. Generating a meal plan

Usage:
    # First, start the server in a separate terminal:
    python3 server.py

    # Then run the client:
    python3 client.py                          # Demo with sample ingredients
    python3 client.py --image path/to/photo    # Analyze a real fridge photo
    python3 client.py --url http://host:port/mcp  # Custom server URL
"""

import argparse
import asyncio
import json
import logging
import sys

from fastmcp import Client

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Default server URL (streamable-http endpoint)
DEFAULT_SERVER_URL = "http://127.0.0.1:8000/mcp"


async def main(image_path: str | None = None, server_url: str = DEFAULT_SERVER_URL):
    """Connect to the MCP server over HTTP and demonstrate all capabilities."""

    # Connect to the server using streamable-http transport
    client = Client(server_url)

    async with client:
        print("=" * 60)
        print("🍽️  Meal Planner MCP Client (Streamable HTTP)")
        print(f"🌐 Connected to: {server_url}")
        print("=" * 60)

        logging.info("Discovering server capabilities...")
        print("\n📋 Discovering server capabilities...\n")

        tools = await client.list_tools()
        print("🔧 Available Tools:")
        for tool in tools:
            print(f"   • {tool.name}: {tool.description[:80]}...")

        resources = await client.list_resources()
        print(f"\n📦 Available Resources:")
        for resource in resources:
            print(f"   • {resource.uri}: {resource.name}")

        resource_templates = await client.list_resource_templates()
        print(f"\n📄 Resource Templates:")
        for template in resource_templates:
            print(f"   • {template.uriTemplate}: {template.name}")

        prompts = await client.list_prompts()
        print(f"\n💬 Available Prompts:")
        for prompt in prompts:
            print(f"   • {prompt.name}: {prompt.description[:80]}...")

        logging.info("Reading resources from server...")
        print("\n" + "=" * 60)
        print("📖 Reading Resources")
        print("=" * 60)

        # Read all recipes
        recipes_resource = await client.read_resource("recipes://all")
        recipes_data = json.loads(recipes_resource[0].text)
        print(f"\n📚 Recipe Database ({len(recipes_data)} recipes):")
        for r in recipes_data:
            print(f"   🍴 {r['name']} ({r['cuisine']}) - {r['prep_time']}")

        # Read dietary profiles
        dietary_resource = await client.read_resource("dietary://profiles")
        dietary_data = json.loads(dietary_resource[0].text)
        print(f"\n🥗 Dietary Profiles:")
        for key, profile in dietary_data.items():
            print(f"   • {profile['name']}: {profile['description']}")

        if image_path:
            logging.info(f"Analyzing fridge image: {image_path}")
            print("\n" + "=" * 60)
            print("📸 Analyzing Fridge Image (Multimodal)")
            print("=" * 60)
            print(f"\n🔍 Sending image to Gemini Vision: {image_path}")

            result = await client.call_tool(
                "identify_ingredients",
                {"image_path": image_path},
            )
            ingredients_text = result.content[0].text
            print(f"\n✅ Identified Ingredients:\n{ingredients_text}")

            # Try to parse ingredients for recipe matching
            try:
                ingredients_data = json.loads(ingredients_text)
                ingredient_names = [
                    ing["name"] for ing in ingredients_data.get("ingredients", [])
                ]
            except (json.JSONDecodeError, KeyError):
                print("\n⚠️  Could not parse ingredients, using sample list instead.")
                ingredient_names = ["tomato", "cheese", "eggs", "bread", "butter"]
        else:
            print("\n" + "=" * 60)
            print("🧪 Demo Mode (no image provided)")
            print("=" * 60)
            ingredient_names = [
                "eggs", "cheese", "tomato", "bread", "butter",
                "onion", "garlic", "olive oil", "bell pepper", "basil",
            ]
            print(f"\n📝 Using sample ingredients: {', '.join(ingredient_names)}")

        logging.info("Calling suggest_recipes tool...")
        print("\n" + "=" * 60)
        print("👨‍🍳 Suggesting Recipes")
        print("=" * 60)

        result = await client.call_tool(
            "suggest_recipes",
            {"ingredients": ingredient_names, "dietary_preference": "none"},
        )
        recipes_text = result.content[0].text
        recipes_result = json.loads(recipes_text)

        print(f"\n🎯 Found {recipes_result['total_matches']} matching recipes:\n")
        for recipe in recipes_result.get("recipes", []):
            match_emoji = "🟢" if recipe["match_percentage"] >= 80 else "🟡" if recipe["match_percentage"] >= 60 else "🟠"
            print(f"   {match_emoji} {recipe['name']} ({recipe['match_percentage']}% match)")
            print(f"      Cuisine: {recipe['cuisine']} | Time: {recipe['prep_time']}")
            if recipe["missing_ingredients"]:
                print(f"      Missing: {', '.join(recipe['missing_ingredients'])}")
            print()

        if recipes_result.get("recipes"):
            top_recipe = recipes_result["recipes"][0]
            logging.info(f"Getting nutrition for recipe: {top_recipe['name']}")
            print("=" * 60)
            print(f"🥗 Nutrition Info: {top_recipe['name']}")
            print("=" * 60)

            result = await client.call_tool(
                "get_nutrition",
                {"recipe_name": top_recipe["recipe_id"]},
            )
            nutrition_text = result.content[0].text
            nutrition_data = json.loads(nutrition_text)

            print(f"\n📊 Nutritional Breakdown:")
            nutrition = nutrition_data.get("nutrition", {})
            print(f"   🔥 Calories: {nutrition.get('calories', 'N/A')}")
            print(f"   💪 Protein:  {nutrition.get('protein', 'N/A')}")
            print(f"   🍞 Carbs:    {nutrition.get('carbs', 'N/A')}")
            print(f"   🧈 Fat:      {nutrition.get('fat', 'N/A')}")
            print(f"   🌿 Fiber:    {nutrition.get('fiber', 'N/A')}")

            print(f"\n📝 Instructions:")
            for i, step in enumerate(nutrition_data.get("instructions", []), 1):
                print(f"   {i}. {step}")

            print(f"\n💡 Health Tips:")
            for tip in nutrition_data.get("health_tips", []):
                print(f"   {tip}")

        logging.info("Calling get_meal_plan tool...")
        print("\n" + "=" * 60)
        print("📅 Daily Meal Plan")
        print("=" * 60)

        result = await client.call_tool(
            "get_meal_plan",
            {
                "ingredients": ingredient_names,
                "meals_per_day": 3,
                "dietary_preference": "none",
            },
        )
        plan_text = result.content[0].text
        plan_data = json.loads(plan_text)

        print()
        for meal in plan_data.get("meal_plan", []):
            print(f"   🕐 {meal['meal']}: {meal['recipe']}")
            if meal.get("missing"):
                print(f"      📝 Need: {', '.join(meal['missing'])}")

        print(f"\n   🔥 Estimated Total Calories: {plan_data.get('estimated_total_calories', 'N/A')}")
        print(f"\n   💡 {plan_data.get('note', '')}")

        logging.info("Fetching prompt templates...")
        print("\n" + "=" * 60)
        print("💬 Prompt Templates")
        print("=" * 60)

        prompt_result = await client.get_prompt(
            "analyze_fridge",
            arguments={"image_path": image_path or "/path/to/fridge.jpg"},
        )
        print(f"\n📝 'analyze_fridge' prompt:")
        for msg in prompt_result.messages:
            print(f"   {msg.content.text}")

        print("\n" + "=" * 60)
        print("✅ Demo complete! ")
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meal Planner MCP Client (Streamable HTTP)")
    parser.add_argument(
        "--image",
        type=str,
        help="Path to a fridge/pantry image for multimodal analysis",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=DEFAULT_SERVER_URL,
        help=f"MCP server URL (default: {DEFAULT_SERVER_URL})",
    )
    args = parser.parse_args()

    asyncio.run(main(image_path=args.image, server_url=args.url))
