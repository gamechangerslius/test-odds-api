import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_opticodds_opportunities_service
from app.clients.exceptions import ProviderClientError, ProviderRequestError
from app.clients.opticodds import OpticOddsError, OpticOddsRequestError
from app.schemas.opportunity import OpportunitiesResponse
from app.services.opticodds_opportunities import OpticOddsOpportunitiesService


logger = logging.getLogger("app.api.opportunities")
router = APIRouter(prefix="/v1", tags=["opportunities"])


@router.get(
    "/opportunities",
    response_model=OpportunitiesResponse,
    summary="Get upcoming soccer betting opportunities",
)
async def list_opportunities(
    league: Optional[str] = Query(
        default=None,
        description="Filter by league name, e.g. 'England - Premier League'",
    ),
    sportsbook: Optional[str] = Query(
        default=None,
        description="Filter by sportsbook name (comma-separated for multiple), e.g. 'DraftKings' or 'DraftKings,BetMGM'",
    ),
    market: Optional[str] = Query(
        default=None,
        description="Filter by market id (comma-separated for multiple), e.g. 'moneyline' or 'moneyline,total_goals'",
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Fixture page number",
    ),
    service: OpticOddsOpportunitiesService = Depends(
        get_opticodds_opportunities_service
    ),
) -> OpportunitiesResponse:
    sportsbooks_list: list[str] = (
        [s.strip() for s in sportsbook.split(",") if s.strip()] if sportsbook else None
    )
    markets_list: list[str] = (
        [m.strip() for m in market.split(",") if m.strip()] if market else None
    )

    logger.info(
        "Handling /v1/opportunities request",
        extra={
            "league": league,
            "sportsbooks": sportsbooks_list,
            "markets": markets_list,
            "page": page,
        },
    )
    try:
        opportunities = await service.get_opportunities(
            league=league,
            sportsbooks=sportsbooks_list,
            markets=markets_list,
            page=page,
        )
    except (OpticOddsRequestError, ProviderRequestError) as exc:
        logger.error("Provider request failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstream odds provider is unavailable",
        ) from exc
    except (OpticOddsError, ProviderClientError) as exc:
        logger.error("Provider response was invalid", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to process data from odds provider",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error while listing opportunities")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from exc

    logger.info(
        "Returning opportunities response",
        extra={"count": len(opportunities), "page": page},
    )

    return OpportunitiesResponse(results=opportunities)
