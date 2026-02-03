import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

try:
    import spacy
    from spacy.language import Language
    from spacy.tokens import Doc
except ImportError:  # pragma: no cover - optional dependency
    spacy = None  # type: ignore[assignment]
    Language = None  # type: ignore[assignment]
    Doc = None  # type: ignore[assignment]

_MONITORS: dict[str, "WebMonitorService"] = {}


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


@dataclass
class FeatureDefinition:
    name: str
    description: str
    keywords: list[str]
    price_terms: list[str]


FEATURE_DEFINITIONS: list[FeatureDefinition] = [
    FeatureDefinition(
        name="product",
        description="Product discovery queries and feature highlights",
        keywords=[
            "product",
            "products",
            "produto",
            "produtos",
            "item",
            "items",
            "featured",
            "flagship",
            "collection",
            "category",
        ],
        price_terms=["price", "preço", "valor", "price tag", "price tags", "tag de preço", "pricing"],
    ),
    FeatureDefinition(
        name="launch",
        description="Launch announcements, new arrivals, and novidades",
        keywords=["launch", "new", "novidade", "lancamento", "novo", "estreia"],
        price_terms=["pre-order", "co-order", "lançamento preço", "price lock"],
    ),
    FeatureDefinition(
        name="discount",
        description="Sales, promotions, and discount campaigns",
        keywords=["sale", "discount", "oferta", "promoção", "promo", "rebate", "clearance"],
        price_terms=["desconto", "venda", "coupon", "voucher"],
    ),
]


class QueryExpander:
    """Query expander that maps user input to feature categories via spaCy word vectors."""

    _SIMILARITY_THRESHOLD = 0.45
    # Prefer the lightweight multilingual model; fall back to the medium English model when unavailable.
    _SPACY_MODELS = ("xx_ent_wiki_sm", "en_core_web_md")

    def __init__(self):
        self._nlp: Language | None = None
        self._feature_docs: dict[str, Doc] = {}

    def _load_spacy_model(self) -> Language | None:
        if self._nlp is not None:
            return self._nlp
        if spacy is None:
            return None
        for model in self._SPACY_MODELS:
            try:
                self._nlp = spacy.load(model)
                break
            except Exception:
                self._nlp = None
        # The multilingual model requires `python -m spacy download xx_ent_wiki_sm` when first used.
        return self._nlp

    def _feature_signature(self, feature: FeatureDefinition) -> str:
        return " ".join([feature.name, feature.description, *feature.keywords])

    def _get_feature_doc(self, feature: FeatureDefinition, nlp: Language) -> "Doc":
        if feature.name in self._feature_docs:
            return self._feature_docs[feature.name]
        doc = nlp(self._feature_signature(feature))
        self._feature_docs[feature.name] = doc
        return doc

    def infer_category(self, phrase: str, seed_url: str | None = None) -> str | None:
        text_for_similarity = " ".join(filter(None, [phrase.strip(), seed_url or ""]))
        nlp = self._load_spacy_model()
        best_match: str | None = None
        best_score = 0.0

        if nlp and text_for_similarity:
            query_doc = nlp(text_for_similarity)
            for feature in FEATURE_DEFINITIONS:
                feature_doc = self._get_feature_doc(feature, nlp)
                score = query_doc.similarity(feature_doc)
                if score > best_score:
                    best_score = score
                    best_match = feature.name
            if best_match and best_score >= self._SIMILARITY_THRESHOLD:
                return best_match

        lower = phrase.lower()
        for feature in FEATURE_DEFINITIONS:
            for keyword in feature.keywords:
                if keyword in lower:
                    return feature.name

        return None

    def expand_query(self, phrase: str, include_price_tags: bool = False, seed_url: str | None = None) -> list[str]:
        category = self.infer_category(phrase)
        if not category:
            return [phrase]

        feature = next((f for f in FEATURE_DEFINITIONS if f.name == category), None)
        if not feature:
            return [phrase]

        terms = list(dict.fromkeys(feature.keywords))
        if include_price_tags and feature.price_terms:
            terms = list(dict.fromkeys(terms + feature.price_terms))

        return terms


@dataclass
class MonitorTaskConfig:
    name: str
    pattern: str
    include_price_tags: bool = False
    topk: int = 20
    threshold: float = 0.3
    source: str = "cc+sitemap"
    extra_keywords: list[str] = field(default_factory=list)


class WebMonitorService:
    def __init__(self, base_domain: str, state_dir: str = "./state"):
        self.domain = base_domain
        self.query_expander = QueryExpander()
        _ensure_dir(state_dir)
        self.state_file = os.path.join(state_dir, f"{self.domain.replace('/', '_')}_known.json")
        self._state_lock = asyncio.Lock()
        self.state = self._load_state()
        self.last_results: list[dict] = []
        self._task_configs: dict[str, MonitorTaskConfig] = {}
        self.register_task(MonitorTaskConfig(name="feature", pattern="*/products/*"))
        self.register_task(MonitorTaskConfig(name="price_tags", pattern="*/products/*price*", include_price_tags=True))

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file) as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    async def _save_state(self):
        async with self._state_lock:
            with open(self.state_file, "w") as f:
                json.dump(sorted(list(self.state)), f)

    async def _bm25_search(self, query_terms: list[str], pattern: str = "*/*", topk: int = 20, threshold: float = 0.3, source: str = "cc+sitemap") -> list[dict]:
        """Attempt to use crawl4ai.AsyncUrlSeeder if available, otherwise return empty list.

        The function returns a list of dicts similar to crawl4ai responses:
        {"url": ..., "relevance_score": 0.9, "head_data": {"title": ...}}
        """
        try:
            from crawl4ai import AsyncUrlSeeder, SeedingConfig

            results = []
            async with AsyncUrlSeeder() as seeder:
                for q in query_terms:
                    cfg = SeedingConfig(
                        source=source,
                        pattern=pattern,
                        extract_head=True,
                        query=q,
                        scoring_method="bm25",
                        score_threshold=threshold,
                        max_urls=topk,
                    )
                    found = await seeder.urls(self.domain, cfg)
                    results.extend(found)
            # dedupe by url
            unique = {r["url"]: r for r in results}
            sorted_relevant = sorted(unique.values(), key=lambda x: -x.get("relevance_score", 0))
            return sorted_relevant
        except Exception:
            # crawl4ai not available or failed — return empty list
            return []

    def _show_new_hits(self) -> dict[str, list[str]]:
        hit_urls = set(hit.get("url") for hit in self.last_results)
        new_hits = hit_urls - self.state
        summary = {
            "new_count": len(new_hits),
            "new_urls": sorted(list(new_hits)),
        }
        return summary

    async def _process_results_and_persist(self, results: list[dict]) -> dict:
        self.last_results = results
        hits = set(r.get("url") for r in results if r.get("url"))
        new_summary = {"total_found": len(results)}
        if hits:
            new_urls = hits - self.state
            new_summary.update({"new_count": len(new_urls), "new_urls": sorted(list(new_urls))})
            self.state |= hits
            await self._save_state()
        else:
            new_summary.update({"new_count": 0, "new_urls": []})
        return new_summary

    async def bm25_monitor(self, query_terms: list[str], pattern: str = "*/*", topk: int = 20, threshold: float = 0.3, source: str = "cc+sitemap") -> dict:
        results = await self._bm25_search(query_terms, pattern=pattern, topk=topk, threshold=threshold, source=source)
        summary = await self._process_results_and_persist(results)
        return {"summary": summary, "results": results}

    def register_task(self, config: MonitorTaskConfig) -> None:
        """Register a named monitoring task with its BM25 configuration."""
        self._task_configs[config.name] = config

    async def monitor_task(
        self,
        task_name: str,
        user_query: str,
        seed_url: str | None = None,
        keywords_override: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a pre-configured task, using the expander + BM25 search parameters."""
        config = self._task_configs.get(task_name)
        if not config:
            raise ValueError(f"Task '{task_name}' is not registered")

        if keywords_override is not None:
            query_terms = keywords_override
        else:
            query_terms = self.query_expander.expand_query(
                user_query,
                include_price_tags=config.include_price_tags,
                seed_url=seed_url,
            )

        if config.extra_keywords:
            query_terms = list(dict.fromkeys(query_terms + config.extra_keywords))

        return await self.bm25_monitor(
            query_terms,
            pattern=config.pattern,
            topk=config.topk,
            threshold=config.threshold,
            source=config.source,
        )

    async def monitor_feature(self, user_query: str, seed_url: str | None = None) -> dict[str, Any]:
        return await self.monitor_task("feature", user_query, seed_url=seed_url)

    async def monitor_price_tags(self, user_query: str, seed_url: str | None = None) -> dict[str, Any]:
        return await self.monitor_task("price_tags", user_query, seed_url=seed_url)

    async def monitor_keywords(self, keywords_or_phrases: list[str]) -> dict:
        return await self.bm25_monitor(keywords_or_phrases)

    async def monitor_company_web(self, company_name: str, extra_domains: list[str] | None = None) -> dict:
        domains = extra_domains or [self.domain]
        combined = []
        try:
            from crawl4ai import AsyncUrlSeeder, SeedingConfig
            async with AsyncUrlSeeder() as seeder:
                for domain in domains:
                    cfg = SeedingConfig(
                        source="cc+sitemap",
                        pattern="*",
                        extract_head=True,
                        query=company_name,
                        scoring_method="bm25",
                        score_threshold=0.2,
                        max_urls=20,
                    )
                    hits = await seeder.urls(domain, cfg)
                    for h in hits:
                        h["domain_searched"] = domain
                    combined.extend(hits)
        except Exception:
            # no crawl4ai — return empty
            combined = []

        # dedupe
        uniq = {}
        for r in combined:
            key = (r.get("domain_searched"), r.get("url"))
            uniq[key] = r
        results = sorted(uniq.values(), key=lambda x: -x.get("relevance_score", 0))
        # do not persist company-wide hits into domain-specific state, just return
        return {"summary": {"total_found": len(results)}, "results": results}


async def get_monitor_instance(domain: str) -> WebMonitorService:
    if domain in _MONITORS:
        return _MONITORS[domain]
    monitor = WebMonitorService(domain)
    _MONITORS[domain] = monitor
    return monitor
