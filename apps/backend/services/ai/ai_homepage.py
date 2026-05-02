import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_homepage_content(
    business_name: str,
    business_type: str,
    products: list[dict],
) -> dict:
    product_names = [p.get("name", "") for p in products[:5]]

    prompt = f"""
    Create homepage content for:
    Business: {business_name}
    Type: {business_type}
    Featured products: {', '.join(product_names)}

    Return a JSON object with:
    - hero_headline: Bold, attention-grabbing headline
    - hero_subheadline: Supporting subheadline
    - cta_text: Call-to-action button text
    - features: Array of 3 feature highlights, each with title and description
    - testimonial: A realistic customer testimonial with name and text
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)
