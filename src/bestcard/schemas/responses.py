from pydantic import BaseModel

from bestcard.domain.models import CardEvaluation, SpendScenario


class RecommendResponse(BaseModel):
    best_card: CardEvaluation
    ranked_cards: list[CardEvaluation]
    parsed_scenario: SpendScenario
    policy_evidence: list[str]
