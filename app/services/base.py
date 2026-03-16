from abc import ABC, abstractmethod
from collections.abc import Iterable

from app.schemas.opportunity import Opportunity


class BaseOpportunitiesService(ABC):
    """
    Abstraction for services that expose normalized betting opportunities.
    """

    @abstractmethod
    async def close(self) -> None:
        """Release any underlying resources."""

    @abstractmethod
    async def get_opportunities(
        self,
        league: str | None = None,
        sportsbooks: Iterable[str] | None = None,
        markets: Iterable[str] | None = None,
        page: int = 1,
    ) -> list[Opportunity]:
        """
        Fetch and normalize upcoming betting opportunities.
        """
