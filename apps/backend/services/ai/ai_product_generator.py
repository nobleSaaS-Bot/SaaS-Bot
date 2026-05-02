import json
from openai import AsyncOpenAI
from app.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def generate_products_for_store(
    store_id: str,
    category: str,
    num_products: int = 3,
    style: str | None = None,
) -> list[dict]:
    prompt = f"""
    Generate {num_products} realistic product listings for a {category} category store.
    Style preference: {style or 'modern and clean'}

    Return a JSON array where each product has:
    - name: Product name
    - description: 2-3 sentence product description
    - price: Realistic price (number)
    - sku: A unique SKU code
    - stock_quantity: Integer between 10-100
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    products = data.get("products", data) if isinstance(data, dict) else data

    for product in products:
        product["store_id"] = store_id
        product["category"] = category

    return products
