import re

from bestcard.domain.models import SpendScenario

CATEGORY_KEYWORDS = {
    "grocery": ["grocery", "supermarket", "超市", "买菜"],
    "dining": ["dining", "restaurant", "food", "餐厅", "吃饭", "外卖"],
    "travel": ["travel", "flight", "hotel", "机票", "酒店", "旅行"],
    "gas": ["gas", "fuel", "加油"],
    "online_shopping": ["online", "ecommerce", "amazon", "网购"],
}

FOREIGN_KEYWORDS = ["境外", "海外", "international", "abroad", "foreign"]


class ScenarioParseError(ValueError):
    pass


def _extract_amount(text: str) -> float | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:usd|\$|刀|块|元)?", text.lower())
    if not match:
        return None
    return float(match.group(1))


def _extract_category(text: str) -> str:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "other"


def _is_foreign(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in FOREIGN_KEYWORDS)


def parse_scenario(
    message: str,
    amount: float | None = None,
    category: str | None = None,
    is_foreign: bool | None = None,
    currency: str = "USD",
    include_annual_fee_proration: bool = False,
    monthly_spend_estimate: float | None = None,
) -> SpendScenario:
    parsed_amount = amount if amount is not None else _extract_amount(message)
    if parsed_amount is None or parsed_amount <= 0:
        raise ScenarioParseError("Could not parse amount from message.")

    parsed_category = category or _extract_category(message)
    parsed_foreign = is_foreign if is_foreign is not None else _is_foreign(message)

    return SpendScenario(
        amount=parsed_amount,
        category=parsed_category,
        is_foreign=parsed_foreign,
        currency=currency,
        include_annual_fee_proration=include_annual_fee_proration,
        monthly_spend_estimate=monthly_spend_estimate,
    )
