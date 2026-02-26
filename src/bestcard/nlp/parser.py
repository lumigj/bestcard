import json
import os

from bestcard.domain.models import SpendScenario

ALLOWED_CATEGORIES = ["grocery", "dining", "travel", "gas", "online_shopping", "other"]


class ScenarioParseError(ValueError):
    pass


def _llm_extract_scenario(message: str, fallback_currency: str) -> dict:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ScenarioParseError(
            "openai package is required for LLM parser. Install with: pip install -e '.[llm]'"
        ) from exc

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ScenarioParseError("OPENAI_API_KEY is missing for LLM parser.")

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
    client = OpenAI(api_key=api_key)

    system_prompt = (
        "Extract a spending scenario from user message. "
        "Return JSON only with keys: amount, category, is_foreign, currency, "
        "include_annual_fee_proration, monthly_spend_estimate. "
        "amount must be positive number. "
        f"category must be one of: {', '.join(ALLOWED_CATEGORIES)}. "
        "If unknown, set category='other'. "
        "is_foreign must be boolean. "
        "currency must be a short code like USD/CNY/EUR. "
        "include_annual_fee_proration default false unless user explicitly asks annual fee sharing. "
        "monthly_spend_estimate should be null if absent."
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
    )

    content = response.choices[0].message.content
    if not content:
        raise ScenarioParseError("LLM returned empty content.")

    data = json.loads(content)
    if "currency" not in data or not data["currency"]:
        data["currency"] = fallback_currency
    return data


def parse_scenario(
    message: str,
    amount: float | None = None,
    category: str | None = None,
    is_foreign: bool | None = None,
    currency: str = "USD",
    include_annual_fee_proration: bool = False,
    monthly_spend_estimate: float | None = None,
) -> SpendScenario:
    llm_result = _llm_extract_scenario(message=message, fallback_currency=currency)

    parsed_amount = amount if amount is not None else llm_result.get("amount")
    if parsed_amount is None or float(parsed_amount) <= 0:
        raise ScenarioParseError("Could not parse a positive amount from message.")

    parsed_category = category or str(llm_result.get("category", "other")).lower()
    if parsed_category not in ALLOWED_CATEGORIES:
        parsed_category = "other"

    parsed_foreign = is_foreign if is_foreign is not None else bool(llm_result.get("is_foreign", False))

    parsed_currency = currency or str(llm_result.get("currency", "USD")).upper()
    parsed_include_proration = (
        include_annual_fee_proration
        if include_annual_fee_proration
        else bool(llm_result.get("include_annual_fee_proration", False))
    )
    parsed_monthly_spend = (
        monthly_spend_estimate
        if monthly_spend_estimate is not None
        else llm_result.get("monthly_spend_estimate")
    )

    if parsed_monthly_spend is not None:
        parsed_monthly_spend = float(parsed_monthly_spend)

    return SpendScenario(
        amount=float(parsed_amount),
        category=parsed_category,
        is_foreign=parsed_foreign,
        currency=parsed_currency,
        include_annual_fee_proration=parsed_include_proration,
        monthly_spend_estimate=parsed_monthly_spend,
    )
