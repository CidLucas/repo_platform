from dataclasses import dataclass


@dataclass(slots=True)
class LandingIntel:
    company_name: str | None
    industry_tags: list[str]
    suggested_size: str | None
    products_or_services: list[str]
    likely_pain_points: list[str]
    suggested_agents: list[str]
    suggested_routines: list[str]
    suggested_kpis: dict[str, list[str]]
    raw_summary: str
    confidence: float
