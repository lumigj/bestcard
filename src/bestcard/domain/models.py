from pydantic import BaseModel, Field


class RewardRule(BaseModel):
    category: str
    cashback_rate: float
    cap_amount: float | None = None
    cap_period: str | None = None


class CardPolicy(BaseModel):
    card_id: str
    card_name: str
    annual_fee: float = 0
    foreign_txn_fee_rate: float = 0
    base_cashback_rate: float = 0
    reward_rules: list[RewardRule] = Field(default_factory=list)
    notes: str | None = None


class SpendScenario(BaseModel):
    amount: float = Field(gt=0)
    category: str
    is_foreign: bool = False
    currency: str = "USD"
    include_annual_fee_proration: bool = False
    monthly_spend_estimate: float | None = None


class CardEvaluation(BaseModel):
    card_id: str
    card_name: str
    cashback: float
    fee: float
    net_reward: float
    reasoning: str
