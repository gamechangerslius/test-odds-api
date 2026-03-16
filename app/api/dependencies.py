from typing import AsyncIterator

from app.clients.base import BaseOddsClient
from app.clients.opticodds import OpticOddsClient
from app.services.opticodds_opportunities import OpticOddsOpportunitiesService


async def get_opticodds_opportunities_service() -> AsyncIterator[
    OpticOddsOpportunitiesService
]:
    """
    FastAPI dependency that wires up the OpticOdds-backed opportunities service
    and ensures resources are cleaned up.
    """
    client: BaseOddsClient = OpticOddsClient()
    service = OpticOddsOpportunitiesService(client=client)
    try:
        yield service
    finally:
        await service.close()
