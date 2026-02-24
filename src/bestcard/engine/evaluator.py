from bestcard.domain.models import CardEvaluation, CardPolicy, SpendScenario


def _category_rate(card: CardPolicy, category: str) -> tuple[float, str]:
    for rule in card.reward_rules:
        if rule.category.lower() == category.lower():
            return rule.cashback_rate, f"matched category '{rule.category}'"
    return card.base_cashback_rate, "fallback to base cashback"


def evaluate_card(card: CardPolicy, scenario: SpendScenario) -> CardEvaluation:
    rate, reason = _category_rate(card, scenario.category)
    cashback = scenario.amount * rate

    fee = 0.0
    if scenario.is_foreign:
        fee += scenario.amount * card.foreign_txn_fee_rate

    if scenario.include_annual_fee_proration and scenario.monthly_spend_estimate:
        fee += card.annual_fee / 12

    net_reward = cashback - fee
    reasoning = (
        f"rate={rate:.2%} ({reason}), cashback={cashback:.2f}, fee={fee:.2f}, net={net_reward:.2f}"
    )

    return CardEvaluation(
        card_id=card.card_id,
        card_name=card.card_name,
        cashback=round(cashback, 2),
        fee=round(fee, 2),
        net_reward=round(net_reward, 2),
        reasoning=reasoning,
    )
