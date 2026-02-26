from bestcard import SpendScenario
from bestcard import rank_cards
from bestcard import PolicyStore


def t_rank_cards_prefers_highest_net_reward() -> None:
    cards = PolicyStore("../data/cards/sample_cards.json").load_cards()
    scenario = SpendScenario(amount=200, category="grocery", is_foreign=False)

    ranked = rank_cards(cards, scenario)

    print(ranked[0].card_id)
    print(ranked[0].net_reward)
    # assert ranked[0].card_id == "blue_cash_plus"
    # assert ranked[0].net_reward == 8.0

#别走test 走这里debug
if __name__ == "__main__":
    t_rank_cards_prefers_highest_net_reward()