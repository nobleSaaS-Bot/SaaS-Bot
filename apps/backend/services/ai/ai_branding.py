import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_branding(business_name: str, business_type: str) -> dict:
    prompt = f"""
    Create a complete branding package for:
    Business: {business_name}
    Type: {business_type}

    Return a JSON object with:
    - primary_color: Hex color code (e.g. #3B82F6)
    - secondary_color: Hex color code
    - accent_color: Hex color code
    - font_family: Google Font name
    - logo_style: Description of logo concept
    - brand_voice: One of [friendly, professional, playful, luxury, bold]
    - emoji: A relevant emoji for the brand
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)
