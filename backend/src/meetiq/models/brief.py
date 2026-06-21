from pydantic import BaseModel, field_validator
from typing import Optional


class ResearchBrief(BaseModel):
    """
    The intelligence brief produced by the research agent for one company.
    Every field is Optional so we can return a partial brief if some sources fail.
    """
    description: str = ""                  # What the company does, in plain language
    recent_news: list[str] = []            # News/funding/launches from last 90 days
    tech_signals: list[str] = []           # Stack, tools, infra signals
    pain_points: list[str] = []            # Inferred pain points
    talking_points: list[str] = []         # 2-3 suggested talking points for the call
    sources_used: list[str] = []           # Which sources contributed (for transparency)
    partial: bool = False                  # True if one or more research sources failed
    eval_score: Optional[float] = None     # Quality score set after eval pipeline runs

    @field_validator("talking_points")
    @classmethod
    def must_have_talking_points(cls, v: list[str]) -> list[str]:
        """Ensure talking points are trimmed to 2-3 max."""
        return v[:3]


class MeetingCard(BaseModel):
    """
    The full object sent to the frontend for each meeting.
    Combines meeting info + company identity + research brief.
    """
    id: str
    title: str
    start_time: str
    end_time: str
    attendees: list[str]

    # Company identification result
    company_identified: bool
    company_name: Optional[str] = None
    company_domain: Optional[str] = None

    # Research state
    # "ready"        → brief is populated and complete
    # "researching"  → agent is working, card shown with loading skeleton
    # "failed"       → all sources failed, show retry button
    # "unidentified" → couldn't figure out the company (e.g. gmail.com attendee)
    brief_status: str = "researching"
    brief: Optional[ResearchBrief] = None
