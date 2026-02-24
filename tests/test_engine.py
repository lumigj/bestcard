from bestcard.domain.models import SpendScenario
from bestcard.engine.selectors import rank_cards
from bestcard.repository.policy_store import PolicyStore


def test_rank_cards_prefers_highest_net_reward() -> None:
    cards = PolicyStore("data/cards/sample_cards.json").load_cards()
    scenario = SpendScenario(amount=200, category="grocery", is_foreign=False)

    ranked = rank_cards(cards, scenario)

    assert ranked[0].card_id == "blue_cash_plus"
    assert ranked[0].net_reward == 8.0
