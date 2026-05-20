from __future__ import annotations

import re
from typing import Iterable

import httpx

from .models import LandingIntel

DEFAULT_SUGGESTED_KPIS: dict[str, list[str]] = {
    "commercial": [
        "com.receita_periodo",
        "com.ticket_medio",
        "com.clientes_unicos",
        "com.clientes_novos",
        "com.crescimento_receita_perc",
    ],
    "inventory": [
        "inv.skus_ativos",
        "inv.qtd_vendida_periodo",
        "inv.receita_periodo",
        "inv.ticket_medio_sku",
        "inv.crescimento_quantidade_perc",
    ],
    "supply": [
        "sup.rfqs_abertas",
        "sup.taxa_resposta_perc",
        "sup.spend_periodo",
        "sup.fornecedores_ativos",
        "sup.pos_pendentes_aprovacao",
    ],
    "finance": [
        "fin.receita_liquida",
        "fin.custo_total",
        "fin.margem_bruta_perc",
        "fin.ticket_medio",
        "fin.total_pedidos",
    ],
}


class LandingIntelService:
    """Extracts onboarding suggestions from a website URL.

    This service is intentionally deterministic and lightweight. It can be called
    directly from API services/edge functions as a fallback when LLM extraction is
    unavailable, and it always returns a usable default payload.
    """

    def __init__(self, timeout_seconds: float = 5.0) -> None:
        self._timeout = timeout_seconds

    def extract(
        self,
        website_url: str,
        valid_agent_slugs: Iterable[str] | None = None,
        valid_routine_ids: Iterable[str] | None = None,
        valid_kpi_slugs: Iterable[str] | None = None,
    ) -> LandingIntel:
        normalized = self._normalize_url(website_url)
        raw_html = self._fetch_html(normalized) if normalized else ""
        text = self._strip_html(raw_html)

        vertical = self._detect_vertical(text)
        suggested_agents = self._agents_for_vertical(vertical)
        suggested_routines = self._routines_for_vertical(vertical)
        suggested_kpis = self._kpis_for_vertical(vertical)

        if valid_agent_slugs is not None:
            valid = set(valid_agent_slugs)
            suggested_agents = [slug for slug in suggested_agents if slug in valid]

        if valid_routine_ids is not None:
            valid = set(valid_routine_ids)
            suggested_routines = [rid for rid in suggested_routines if rid in valid]

        if valid_kpi_slugs is not None:
            valid = set(valid_kpi_slugs)
            suggested_kpis = {
                dim: [slug for slug in slugs if slug in valid]
                for dim, slugs in suggested_kpis.items()
            }

        return LandingIntel(
            company_name=self._extract_title(raw_html),
            industry_tags=[vertical] if vertical else [],
            suggested_size=None,
            products_or_services=[],
            likely_pain_points=self._pain_points_for_vertical(vertical),
            suggested_agents=suggested_agents,
            suggested_routines=suggested_routines,
            suggested_kpis=suggested_kpis,
            raw_summary=text[:1200],
            confidence=0.72 if vertical else 0.42,
        )

    def _fetch_html(self, url: str) -> str:
        try:
            with httpx.Client(timeout=self._timeout, follow_redirects=True) as client:
                response = client.get(url, headers={"User-Agent": "BluLandingIntel/1.0"})
                response.raise_for_status()
                return response.text
        except Exception:
            return ""

    @staticmethod
    def _normalize_url(raw: str) -> str:
        candidate = raw.strip()
        if not candidate:
            return ""
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return candidate
        return f"https://{candidate}"

    @staticmethod
    def _strip_html(html: str) -> str:
        if not html:
            return ""
        without_scripts = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
        without_styles = re.sub(r"<style[\s\S]*?</style>", " ", without_scripts, flags=re.IGNORECASE)
        plain = re.sub(r"<[^>]+>", " ", without_styles)
        return re.sub(r"\s+", " ", plain).strip().lower()

    @staticmethod
    def _extract_title(html: str) -> str | None:
        match = re.search(r"<title[^>]*>([\s\S]*?)</title>", html, flags=re.IGNORECASE)
        if not match:
            return None
        title = re.sub(r"\s+", " ", match.group(1)).strip()
        return title or None

    @staticmethod
    def _detect_vertical(text: str) -> str | None:
        if re.search(r"e-?commerce|checkout|carrinho|sku|produto", text):
            return "ecommerce"
        if re.search(r"distribui|fornecedor|atacado|estoque|supply", text):
            return "industria"
        if re.search(r"cl[ií]nica|hospital|paciente|consult[oó]rio", text):
            return "saude"
        if re.search(r"curso|aluno|escola|educa", text):
            return "educacao"
        if re.search(r"contabil|financeir|banco|cr[eé]dito|invest", text):
            return "financeiro"
        if re.search(r"servi[cç]o|ag[eê]ncia|consultoria|atendimento", text):
            return "servicos"
        return None

    @staticmethod
    def _agents_for_vertical(vertical: str | None) -> list[str]:
        if vertical == "ecommerce":
            return ["analytics", "inventory", "marketing"]
        if vertical == "servicos":
            return ["crm", "scheduling", "analytics"]
        return ["analytics", "crm", "documents"]

    @staticmethod
    def _routines_for_vertical(vertical: str | None) -> list[str]:
        if vertical == "ecommerce":
            return ["daily_sales_digest", "low_stock_alert", "stale_lead_followup"]
        if vertical == "servicos":
            return ["stale_lead_followup", "appointment_reminder", "weekly_performance"]
        return ["daily_sales_digest", "weekly_performance", "low_stock_alert"]

    @staticmethod
    def _kpis_for_vertical(vertical: str | None) -> dict[str, list[str]]:
        # Current deterministic fallback uses the same default set across verticals;
        # this keeps UX predictable when no LLM extraction is available.
        return {k: list(v) for k, v in DEFAULT_SUGGESTED_KPIS.items()}

    @staticmethod
    def _pain_points_for_vertical(vertical: str | None) -> list[str]:
        if vertical == "ecommerce":
            return ["queda de conversao", "estoque sem giro", "aumento de cac"]
        if vertical == "servicos":
            return ["leads sem follow-up", "agenda ociosa", "atraso em cobrancas"]
        return ["falta de visibilidade", "processos manuais", "dados dispersos"]
