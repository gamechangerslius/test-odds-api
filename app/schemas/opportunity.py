from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Opportunity(BaseModel):
    event_id: str = Field(..., description="Provider fixture identifier")
    match: str = Field(..., description="Human readable matchup (Home vs Away)")
    league: str
    sport: str
    start_time: datetime

    sportsbook: str
    market: str
    selection: str
    line: Optional[float] = Field(
        None,
        description="Line or points for spreads/totals; null for moneyline",
    )
    odds: int = Field(..., description="American odds price, e.g. -120 or 145")


class OpportunitiesResponse(BaseModel):
    results: List[Opportunity]
