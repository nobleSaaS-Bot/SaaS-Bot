import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_categories(business_type: str, num_categories: int = 4) -> list[dict]:
    prompt = f"""
    Generate {num_categories} product categories for a {business_type} store.

    Return a JSON object with a "categories" array where each item has:
    - name: Category name
    - description: Short description
    - icon: An emoji icon
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    return data.get("categories", [])
