from bestcard.domain.models import CardEvaluation, CardPolicy, SpendScenario
from bestcard.engine.evaluator import evaluate_card


def rank_cards(cards: list[CardPolicy], scenario: SpendScenario) -> list[CardEvaluation]:
    evaluations = [evaluate_card(card, scenario) for card in cards]
    evaluations.sort(key=lambda item: (item.net_reward, item.cashback), reverse=True)
    return evaluations
