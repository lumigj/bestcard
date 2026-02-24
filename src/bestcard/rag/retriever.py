from bestcard.domain.models import CardPolicy


def retrieve_policy_evidence(card: CardPolicy, category: str) -> list[str]:
    snippets: list[str] = []

    for rule in card.reward_rules:
        if rule.category.lower() == category.lower():
            line = f"{card.card_name}: {rule.category} cashback {rule.cashback_rate:.0%}"
            if rule.cap_amount and rule.cap_period:
                line += f" (cap {rule.cap_amount:.0f}/{rule.cap_period})"
            snippets.append(line)

    if card.foreign_txn_fee_rate > 0:
        snippets.append(f"{card.card_name}: foreign transaction fee {card.foreign_txn_fee_rate:.1%}")

    if card.notes:
        snippets.append(f"Policy note: {card.notes}")

    return snippets[:3]
