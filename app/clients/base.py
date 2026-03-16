from abc import ABC, abstractmethod
from collections.abc import Iterable


class BaseOddsClient(ABC):
    """
    Abstraction for odds provider integrations.
    """

    @abstractmethod
    async def close(self) -> None:
        """Release any underlying resources (e.g., HTTP sessions)."""

    @abstractmethod
    async def get_active_fixtures(
        self,
        sport: str,
        league: str | None = None,
    ) -> list[dict[str, object]]:
        """Fetch fixtures that have or have had odds for the given sport/league."""

    @abstractmethod
    async def get_fixtures_odds(
        self,
        fixture_ids: Iterable[str],
        sportsbooks: Iterable[str],
        markets: Iterable[str],
    ) -> list[dict[str, object]]:
        """Fetch current odds snapshots for the given fixtures from selected books."""
