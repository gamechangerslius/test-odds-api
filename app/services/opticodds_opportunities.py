import logging
import asyncio
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from app.clients.opticodds import OpticOddsClient
from app.core.config import get_settings
from app.schemas.opportunity import Opportunity
from app.services.base import BaseOpportunitiesService


logger = logging.getLogger("app.services.opticodds_opportunities")


class OpticOddsOpportunitiesService(BaseOpportunitiesService):
    def __init__(self, client: OpticOddsClient) -> None:
        self._settings = get_settings()
        self._client = client

    async def close(self) -> None:
        # Client lifecycle is owned by the FastAPI app lifespan.
        return None

    async def get_opportunities(
        self,
        league: Optional[str] = None,
        sportsbooks: Optional[Iterable[str]] = None,
        markets: Optional[Iterable[str]] = None,
        page: int = 1,
    ) -> List[Opportunity]:
        """
        Fetch upcoming soccer opportunities and normalize them.
        """
        sport = self._settings.default_sport

        if markets is not None:
            requested_markets: list[str] = list(markets)
        else:
            requested_markets = []

        if sportsbooks is not None:
            requested_sportsbooks: list[str] = list(sportsbooks)
        else:
            requested_sportsbooks = self._settings.default_sportsbooks

        fixtures = await self._client.get_active_fixtures(
            sport=sport,
            league=league,
            page=page,
        )

        filtered_fixtures: list[Dict[str, Any]] = []
        for fixture in fixtures:
            start_raw = fixture.get("start_date")
            start_time = self._parse_start_time(start_raw)
            if start_time is None:
                logger.warning(
                    "Skipping fixture with invalid start_date",
                    extra={"raw_start_date": start_raw},
                )
                continue
            fixture["_parsed_start_time"] = start_time
            filtered_fixtures.append(fixture)

        fixture_ids: list[str] = [
            fixture.get("id")
            for fixture in filtered_fixtures
            if fixture.get("id") is not None
        ]
        if not fixture_ids:
            logger.info("No fixtures with valid IDs after filtering")
            return []

        chunk_size = max(1, int(self._settings.opticodds_odds_chunk_size))
        max_concurrency = max(1, int(self._settings.opticodds_odds_max_concurrency))
        semaphore = asyncio.Semaphore(max_concurrency)

        async def fetch_chunk(chunk_ids: list[str]) -> list[Dict[str, Any]]:
            async with semaphore:
                return await self._client.get_fixtures_odds(
                    fixture_ids=chunk_ids,
                    sportsbooks=requested_sportsbooks,
                    markets=requested_markets,
                )

        chunks: list[list[str]] = [
            fixture_ids[idx : idx + chunk_size]
            for idx in range(0, len(fixture_ids), chunk_size)
        ]
        chunk_results = await asyncio.gather(*(fetch_chunk(c) for c in chunks))
        fixtures_odds: list[Dict[str, Any]] = [
            item for sub in chunk_results for item in sub
        ]

        opportunities: list[Opportunity] = []
        fixtures_by_id: Dict[str, Dict[str, Any]] = {
            fixture.get("id"): fixture
            for fixture in filtered_fixtures
            if fixture.get("id") is not None
        }

        for fixture_with_odds in fixtures_odds:
            fixture_id = fixture_with_odds.get("id")
            fixture = fixtures_by_id.get(fixture_id)

            try:
                start_time = fixture["_parsed_start_time"]
                league_obj = fixture["league"]
                league_name = league_obj["name"]
                sport_obj = fixture["sport"]
                sport_id = sport_obj["id"]
                home_competitors = fixture["home_competitors"]
                away_competitors = fixture["away_competitors"]
            except (KeyError, TypeError) as exc:
                logger.warning(
                    "Skipping fixture with missing required fields",
                    extra={"fixture_id": fixture_id, "error": str(exc)},
                )
                continue

            home_name = self._extract_team_name(home_competitors)
            away_name = self._extract_team_name(away_competitors)

            match_display = f"{home_name} vs {away_name}"

            odds_entries = fixture_with_odds.get("odds")

            for odd in odds_entries:
                try:
                    opp = self._normalize_opportunity(
                        fixture_id=fixture_id,
                        match_display=match_display,
                        league_name=league_name,
                        sport_id=sport_id,
                        start_time=start_time,
                        odd=odd,
                    )
                except ValueError as exc:
                    logger.warning(
                        "Skipping odd due to normalization error",
                        extra={"fixture_id": fixture_id, "reason": str(exc)},
                    )
                    continue
                opportunities.append(opp)

        logger.info(
            "Built opportunities",
            extra={"count": len(opportunities)},
        )
        return opportunities

    @staticmethod
    def _parse_start_time(value: Optional[str]) -> Optional[datetime]:
        if value is None:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _extract_team_name(competitors: Any) -> Optional[str]:
        """
        Extract a team name from the competitors array based on the documented
        fixture schema (first entry, `name` or `abbreviation`).
        """
        if not isinstance(competitors, list) or not competitors:
            return None

        team = competitors[0]
        if not isinstance(team, dict):
            return None

        name_value = team.get("name")
        if isinstance(name_value, str):
            return name_value

        return None

    @staticmethod
    def _normalize_opportunity(
        *,
        fixture_id: str,
        match_display: str,
        league_name: str,
        sport_id: str,
        start_time: datetime,
        odd: Dict[str, Any],
    ) -> Opportunity:
        """
        Normalize a single OpticOdds odds entry into the internal Opportunity model.

        Based on the documented `/fixtures/odds` response:
        - `sportsbook`: string
        - `market`: display label (e.g., "Moneyline")
        - `market_id`: identifier (e.g., "moneyline")
        - `name`: selection display (e.g., "Houston Astros -1.5")
        - `selection`: selection name for some markets (optional)
        - `points`: numeric spread/total or null for moneyline
        - `price`: American odds number
        """
        sportsbook_value = odd.get("sportsbook")
        if not isinstance(sportsbook_value, str):
            raise ValueError("Missing or invalid sportsbook")

        price_value = odd.get("price")
        if not isinstance(price_value, (int, float)):
            raise ValueError("Missing or invalid price")

        market_identifier = odd.get("market_id")
        if not isinstance(market_identifier, str):
            market_identifier = odd.get("market")
            if not isinstance(market_identifier, str):
                raise ValueError("Missing market identifier")

        if "selection" in odd and isinstance(odd["selection"], str):
            selection_value = odd["selection"]
        elif "name" in odd and isinstance(odd["name"], str):
            selection_value = odd["name"]
        else:
            raise ValueError("Missing selection name")

        points_value = odd.get("points")
        if isinstance(points_value, (int, float)):
            line_value: Optional[float] = float(points_value)
        else:
            line_value = None

        return Opportunity(
            event_id=fixture_id,
            match=match_display,
            league=league_name,
            sport=sport_id,
            start_time=start_time,
            sportsbook=sportsbook_value,
            market=market_identifier.lower(),
            selection=selection_value,
            line=line_value,
            odds=int(price_value),
        )
