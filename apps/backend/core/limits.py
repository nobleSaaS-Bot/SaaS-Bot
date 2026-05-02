from typing import Any


def check_limit(plan: dict, feature: str) -> bool:
    limits = plan.get("limits", {})
    value = limits.get(feature)

    if value is None:
        return False
    if value is True or value == -1:
        return True
    if isinstance(value, int) and value > 0:
        return True
    return False


def get_limit_value(plan: dict, feature: str) -> Any:
    return plan.get("limits", {}).get(feature, 0)


FEATURE_KEYS = [
    "products",
    "orders_per_month",
    "stores",
    "flows",
    "ai_store_builder",
    "analytics",
    "custom_domain",
    "payment_providers",
    "team_members",
]
