from bestcard.domain.models import SpendScenario
from bestcard.engine.selectors import rank_cards
from bestcard.nlp.parser import parse_scenario
from bestcard.rag.retriever import retrieve_policy_evidence
from bestcard.repository.policy_store import PolicyStore
from bestcard.schemas.requests import RecommendRequest
from bestcard.schemas.responses import RecommendResponse


class RecommendationOrchestrator:
    def __init__(self, policy_store: PolicyStore):
        self.policy_store = policy_store

    def _build_scenario(self, request: RecommendRequest) -> SpendScenario:
        if request.message:
            return parse_scenario(
                message=request.message,
                amount=request.amount,
                category=request.category,
                is_foreign=request.is_foreign,
                currency=request.currency,
                include_annual_fee_proration=request.include_annual_fee_proration,
                monthly_spend_estimate=request.monthly_spend_estimate,
            )

        if request.amount is None or request.category is None:
            raise ValueError("Either message or (amount + category) is required.")

        return SpendScenario(
            amount=request.amount,
            category=request.category,
            is_foreign=bool(request.is_foreign),
            currency=request.currency,
            include_annual_fee_proration=request.include_annual_fee_proration,
            monthly_spend_estimate=request.monthly_spend_estimate,
        )

    def recommend(self, request: RecommendRequest) -> RecommendResponse:
        scenario = self._build_scenario(request)
        cards = self.policy_store.load_cards()
        ranked = rank_cards(cards, scenario)

        if not ranked:
            raise ValueError("No cards available.")

        best = ranked[0]
        best_card_policy = next(card for card in cards if card.card_id == best.card_id)
        evidence = retrieve_policy_evidence(best_card_policy, scenario.category)

        return RecommendResponse(
            best_card=best,
            ranked_cards=ranked,
            parsed_scenario=scenario,
            policy_evidence=evidence,
        )
