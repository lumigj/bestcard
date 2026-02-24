from pydantic import BaseModel


class RecommendRequest(BaseModel):
    message: str | None = None
    amount: float | None = None
    category: str | None = None
    is_foreign: bool | None = None
    currency: str = "USD"
    include_annual_fee_proration: bool = False
    monthly_spend_estimate: float | None = None
