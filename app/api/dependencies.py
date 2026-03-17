from typing import Annotated

from fastapi import Depends, Request

from app.clients.opticodds import OpticOddsClient
from app.services.opticodds_opportunities import OpticOddsOpportunitiesService


def get_opticodds_client(request: Request) -> OpticOddsClient:
    client = getattr(request.app.state, "opticodds_client", None)
    if client is None:
        # Should be created by app lifespan, but keep a clear failure mode.
        raise RuntimeError("OpticOdds client not initialized")
    return client


def get_opticodds_opportunities_service(
    client: Annotated[OpticOddsClient, Depends(get_opticodds_client)],
) -> OpticOddsOpportunitiesService:
    # Service is cheap; client/session is shared and closed on shutdown.
    return OpticOddsOpportunitiesService(client=client)
