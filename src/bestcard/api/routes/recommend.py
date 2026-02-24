from fastapi import APIRouter, HTTPException

from bestcard.agents.orchestrator import RecommendationOrchestrator
from bestcard.config import settings
from bestcard.repository.policy_store import PolicyStore
from bestcard.schemas.requests import RecommendRequest
from bestcard.schemas.responses import RecommendResponse

router = APIRouter(tags=["recommend"])
orchestrator = RecommendationOrchestrator(PolicyStore(settings.card_policy_file))


@router.post("/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    try:
        return orchestrator.recommend(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
