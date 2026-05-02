from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_storefront_content(business_name: str, business_type: str, description: str | None = None) -> dict:
    prompt = f"""
    Generate a complete storefront content package for:
    Business Name: {business_name}
    Business Type: {business_type}
    Description: {description or 'N/A'}

    Return a JSON object with:
    - tagline: A catchy one-line tagline
    - about: A short about section (2-3 sentences)
    - welcome_message: Telegram bot welcome message
    - hero_text: Homepage hero text
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    import json
    return json.loads(response.choices[0].message.content)
