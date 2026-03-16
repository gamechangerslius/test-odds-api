import logging
from collections.abc import Iterable

import aiohttp

from app.clients.base import BaseOddsClient
from app.clients.exceptions import (
    ProviderClientError,
    ProviderRequestError,
    ProviderResponseError,
)
from app.core.config import get_settings


logger = logging.getLogger("app.clients.opticodds")


class OpticOddsError(ProviderClientError):
    """Base error for OpticOdds-specific issues."""


class OpticOddsRequestError(OpticOddsError, ProviderRequestError):
    """Network or HTTP-level error when calling OpticOdds."""


class OpticOddsResponseError(OpticOddsError, ProviderResponseError):
    """Response payload missing expected structure."""


class OpticOddsClient(BaseOddsClient):
    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = str(settings.opticodds_base_url)
        self._api_key = settings.opticodds_api_key
        self._timeout = settings.request_timeout_seconds

        timeout = aiohttp.ClientTimeout(total=self._timeout)
        self._session = aiohttp.ClientSession(
            base_url=self._base_url,
            timeout=timeout,
            headers={"X-Api-Key": self._api_key},
        )

    async def close(self) -> None:
        await self._session.close()

    async def get_active_fixtures(
        self,
        sport: str,
        league: str | None = None,
        page: int = 1,
    ) -> list[dict[str, object]]:
        """
        Fetch a single page of active fixtures with odds for a given sport
        (and optional league), using the documented `page` parameter.
        """
        params: dict[str, object] = {"sport": sport, "page": page}
        if league is not None:
            params["league"] = league

        logger.info(
            "Fetching active fixtures from OpticOdds",
            extra={"sport": sport, "league": league, "page": page},
        )

        try:
            async with self._session.get("fixtures/active", params=params) as response:
                status = response.status
                text = await response.text()
                if status != 200:
                    logger.error(
                        "OpticOdds fixtures responded with non-200 status",
                        extra={"status_code": status, "body": text, "page": page},
                    )
                    raise OpticOddsRequestError(
                        f"OpticOdds fixtures request failed with status {status}"
                    )

                try:
                    data = await response.json()
                except aiohttp.ContentTypeError as exc:
                    logger.error(
                        "OpticOdds fixtures response was not valid JSON",
                        extra={"body": text, "page": page},
                    )
                    raise OpticOddsResponseError(
                        "Failed to decode fixtures response JSON"
                    ) from exc
        except aiohttp.ClientError as exc:
            logger.error("OpticOdds fixtures request failed", exc_info=exc)
            raise OpticOddsRequestError("Failed to fetch fixtures") from exc

        fixtures: list[dict[str, object]] = data.get("data", [])

        logger.info(
            "Fetched active fixtures from OpticOdds",
            extra={
                "count": len(fixtures),
                "page": page,
                "total_pages": data.get("total_pages"),
            },
        )
        return fixtures

    async def get_fixtures_odds(
        self,
        fixture_ids: Iterable[str],
        sportsbooks: Iterable[str],
        markets: Iterable[str],
    ) -> list[dict[str, object]]:
        """
        Fetch current odds snapshot for the given fixtures, sportsbooks and market.
        """
        fixture_ids_list = list(fixture_ids)
        sportsbooks_list = list(sportsbooks)
        markets_list = list(markets)

        if not fixture_ids_list or not sportsbooks_list:
            raise OpticOddsRequestError("Missing required parameters")

        params: dict[str, object] = {
            "is_main": "true",
            "odds_format": "AMERICAN",
            "fixture_id": fixture_ids_list,
            "sportsbook": sportsbooks_list,
        }
        if markets_list:
            params["market"] = markets_list

        logger.info(
            "Fetching odds from OpticOdds",
            extra={
                "fixture_count": len(fixture_ids_list),
                "sportsbooks": sportsbooks_list,
                "markets": markets_list,
            },
        )

        try:
            async with self._session.get("fixtures/odds", params=params) as response:
                status = response.status
                text = await response.text()
                if status != 200:
                    logger.error(
                        "OpticOdds odds responded with non-200 status",
                        extra={"status_code": status, "body": text},
                    )
                    raise OpticOddsRequestError(
                        f"OpticOdds odds request failed with status {status}"
                    )

                try:
                    data = await response.json()
                except aiohttp.ContentTypeError as exc:
                    logger.error(
                        "OpticOdds odds response was not valid JSON",
                        extra={"body": text},
                    )
                    raise OpticOddsResponseError(
                        "Failed to decode odds response JSON"
                    ) from exc
        except aiohttp.ClientError as exc:
            logger.error("OpticOdds odds request failed", exc_info=exc)
            raise OpticOddsRequestError("Failed to fetch odds") from exc

        fixtures_odds: list[dict[str, object]] = data.get("data", [])

        logger.info(
            "Fetched odds from OpticOdds",
            extra={"fixture_count": len(fixtures_odds)},
        )
        return fixtures_odds
