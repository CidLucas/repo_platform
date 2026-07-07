"""
Schema Matcher — port of supabase/functions/match-columns edge function.

The Deno EF is gone (replaced by this module + a FastAPI router); the
2 TS callers (upload-csv-source, upload-drive-source) and 1 Python
caller (context_module) all go through the router.

The logic is a faithful port of the Deno version:
  - Loads canonical column defs from public.canonical_columns (cached
    per-process, like the Deno isolate cache)
  - Alias-table lookup + Dice coefficient (Sorensen-Dice on bigrams)
  - Context detection: customer | supplier | product | neutral
  - High-confidence matches (≥0.85) auto-map; medium (0.70-0.84) go
    to needs_review; low (<0.70) go to unmatched

The output shape matches the Deno EF exactly so callers don't need
to change their parsing logic.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Types ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CanonicalColumnDef:
    column_name: str
    data_type: str
    is_required: bool
    description: str
    examples: list[str]


@dataclass
class MatchCandidate:
    canonical: str
    confidence: float


@dataclass
class SchemaMatchResult:
    matched: dict[str, str] = field(default_factory=dict)
    unmatched: list[str] = field(default_factory=list)
    confidence_scores: dict[str, float] = field(default_factory=dict)
    needs_review: list[dict[str, Any]] = field(default_factory=list)
    detected_context: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "unmatched": self.unmatched,
            "needs_review": self.needs_review,
            "confidence_scores": self.confidence_scores,
            "detected_context": self.detected_context,
        }


SchemaType = str  # "invoices" | "fato_transacoes" | "dim_clientes" | "dim_inventory"
EntityContext = str  # "customer" | "supplier" | "product" | "neutral"

SCHEMA_TO_TABLE: dict[SchemaType, str] = {
    "fato_transacoes": "fato_transacoes",
    "dim_clientes": "dim_clientes",
    "dim_inventory": "dim_inventory",
}


# ── Fallback: "invoices" composite schema ───────────────────────────────────
# Prefixed names (cliente_*, fornecedor_*, produto_*) tell the ETL which
# dimension table to write each field to. Not stored in canonical_columns
# because the prefixes are ETL artefacts, not real DB columns.
INVOICES_COLUMNS: list[CanonicalColumnDef] = [
    CanonicalColumnDef("documento", "text", True, "Unique transaction/invoice identifier",
                       ["NF-001", "ORD-12345"]),
    CanonicalColumnDef("data_competencia_id", "bigint", True, "Accounting date as YYYYMMDD integer",
                       ["20240115"]),
    CanonicalColumnDef("quantidade", "numeric", False, "Quantity of items", ["1", "5"]),
    CanonicalColumnDef("valor_unitario", "numeric", False, "Unit price per item", ["49.90"]),
    CanonicalColumnDef("valor", "numeric", True, "Total transaction value", ["249.50"]),
    CanonicalColumnDef("status", "text", False, "Transaction status (paid/pending/cancelled)",
                       ["pago", "paid"]),
    CanonicalColumnDef("transaction_label", "text", False,
                       "Free-text label from the source (venda, NF saída, boleto, etc.)",
                       ["venda", "NF-e saída", "PIX recebido"]),
    CanonicalColumnDef("categoria", "text", False, "Business category (free-text, user-defined)",
                       ["Material", "Mão de obra", "Centro de custo A"]),
    CanonicalColumnDef("subcategoria", "text", False, "Sub-category (free-text, user-defined)",
                       ["Insumos", "Sub família 1", "Sub categoria B"]),
    # → dim_clientes
    CanonicalColumnDef("cliente_cpf_cnpj", "text", False, "Customer tax ID (CPF/CNPJ)",
                       ["123.456.789-09"]),
    CanonicalColumnDef("cliente_nome", "text", False, "Customer name", ["João Silva"]),
    CanonicalColumnDef("cliente_telefone", "text", False, "Customer phone", ["(11) 99999-9999"]),
    CanonicalColumnDef("cliente_cidade", "text", False, "Customer city", ["São Paulo"]),
    CanonicalColumnDef("cliente_uf", "text", False, "Customer state (2-letter UF)", ["SP"]),
    # → dim_fornecedores
    CanonicalColumnDef("fornecedor_cnpj", "text", False, "Supplier CNPJ",
                       ["12.345.678/0001-99"]),
    CanonicalColumnDef("fornecedor_nome", "text", False, "Supplier name", ["Distribuidora ABC"]),
    CanonicalColumnDef("fornecedor_telefone", "text", False, "Supplier phone", ["(11) 3333-4444"]),
    CanonicalColumnDef("fornecedor_cidade", "text", False, "Supplier city", ["Campinas"]),
    CanonicalColumnDef("fornecedor_uf", "text", False, "Supplier state (2-letter UF)", ["SP"]),
    # → dim_inventory
    CanonicalColumnDef("produto_sku", "text", False, "Product SKU", ["SKU-001"]),
    CanonicalColumnDef("produto_nome", "text", False, "Product name", ["Camiseta Azul M"]),
]


# ── Column Aliases ───────────────────────────────────────────────────────────

COLUMN_ALIASES: dict[str, list[str]] = {
    "documento": [
        "id_operatorinvoice", "id_invoice", "invoice_id", "order_id", "orderid",
        "pedido_id", "id_pedido", "numero_pedido", "order_number",
        "number", "numero_nota", "chave_nfe", "document_number", "numero_nf",
        "chave_acesso", "numero",
        "número nf", "numero nf", "num nf", "nr nf", "nf", "nota fiscal",
        "número nota", "numero nota", "nf numero", "nf número",
        "nf_id", "id_nf", "nfe_id", "id_nota",
    ],
    "data_competencia_id": [
        "emittedat_operatorinvoice", "createdat_operatorinvoice", "data_emissao",
        "emission_date", "order_date", "data_pedido", "data_transacao",
        "transaction_date", "date", "created_at", "purchase_date",
        "issue_date", "competencia", "dt_emissao", "data_competencia",
        "data custo", "data_custo", "data do custo", "dt custo", "dt_custo",
        "data lancamento", "data_lancamento", "data registro", "data_registro",
    ],
    "quantidade": ["quantitytraded_product", "quantity", "qty", "qtd", "quantitytraded"],
    "valor_unitario": ["unitprice_product", "unit_price", "preco_unitario", "unitprice"],
    "valor": [
        "totalprice_product", "total_price", "grand_total", "valor_total",
        "price", "preco", "total",
        "total_value", "value", "vl_total", "valor_liquido",
        "valor_total_nfse", "valor_servico",
    ],
    "status": ["status_operatorinvoice", "order_status", "status_order"],
    "cliente_cpf_cnpj": [
        "receiverlegaldoc", "receiver_cnpj", "customer_doc",
        "cpf_cnpj", "cpf", "cnpj_cliente",
        "customer_cnpj", "cnpj_destinatario", "destinatario_cnpj", "recipient_cnpj",
        "documento_tomador", "documento_cliente",
    ],
    "cliente_nome": [
        "receiverlegalname", "nome_receiver", "customer_name",
        "nome_cliente", "receiver_name",
        "nome_destinatario", "nome_tomador",
    ],
    "cliente_telefone": ["receiverphone", "receiver_phone", "customer_phone", "telefone_cliente"],
    "cliente_cidade": ["receivercity", "receiver_cidade", "customer_city", "cidade_cliente"],
    "cliente_uf": ["receiverstateuf", "receiver_uf", "customer_state", "uf_cliente", "estado_cliente"],
    "fornecedor_cnpj": [
        "emitterlegaldoc", "emitter_cnpj", "supplier_cnpj", "cnpj_fornecedor",
        "cnpj_emitente", "issuer_cnpj", "emitente_cnpj",
    ],
    "fornecedor_nome": [
        "emitterlegalname", "nome_emitter", "supplier_name", "nome_fornecedor",
        "nome_emitente", "issuer_name", "razao_social_emitente", "fornecedor",
    ],
    "fornecedor_telefone": ["emitterphone", "emitter_phone", "supplier_phone", "telefone_fornecedor"],
    "fornecedor_cidade": ["emittercity", "emitter_cidade", "supplier_city", "cidade_fornecedor"],
    "fornecedor_uf": ["emitterstateuf", "emitter_uf", "supplier_state", "uf_fornecedor", "estado_fornecedor"],
    "produto_sku": ["id_product", "product_id", "external_product_id", "sku", "codigo_produto", "item_sku", "product_sku"],
    "produto_nome": ["description_product", "descricao_produto", "product_description", "product_name", "nome_produto", "item_name"],
    "cpf_cnpj": ["receiverlegaldoc", "customer_doc", "cpf", "cnpj", "documento_cliente"],
    "nome": ["name", "full_name", "customer_name", "product_name", "supplier_name"],
    "telefone": ["phone", "telephone", "mobile", "celular", "phone_number"],
    "endereco_cidade": ["city", "cidade", "municipio", "receivercity", "emittercity"],
    "endereco_uf": ["state", "uf", "estado", "receiverstateuf", "emitterstateuf"],
    "sku": ["item_sku", "product_sku", "codigo", "code", "id_product", "product_id"],
    "transaction_label": [
        "tipo_transacao", "transaction_type", "tipo_operacao", "natureza_operacao",
        "tipo_nf", "operacao", "tipo_documento",
    ],
    "categoria": [
        "category", "centro de custo", "centro_custo", "cost_center", "cost center",
        "familia", "grupo", "family", "group",
        "mao de obra", "mão de obra", "mat ou mdo", "mat_ou_mdo", "mat/mdo",
        "material", "insumo", "tipo_custo", "modalidade",
        "centro de custo - familia", "centro_custo_familia",
    ],
    "subcategoria": [
        "subcategory", "sub_categoria", "sub categoria",
        "sub_familia", "sub-familia", "subfamilia", "sub familia",
        "subgrupo", "descricao",
        "centro de custo - sub familia", "centro_custo_sub_familia",
    ],
}


# ── Thresholds ───────────────────────────────────────────────────────────────

HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.70


# ── Context-Aware Matching ───────────────────────────────────────────────────

CONTEXT_SIGNAL_COLUMNS: dict[str, EntityContext] = {
    "cliente": "customer", "client_id": "customer", "cliente_nome": "customer",
    "nome_cliente": "customer", "customer": "customer", "customer_id": "customer",
    "customer_name": "customer", "comprador": "customer", "buyer": "customer",
    "receiver": "customer", "receiverlegalname": "customer", "receiverlegaldoc": "customer",
    "cnpj_destinatario": "customer", "destinatario_cnpj": "customer",
    "destinatario": "customer", "nome_destinatario": "customer",
    "nome_tomador": "customer", "documento_tomador": "customer", "documento_cliente": "customer",
    "fornecedor": "supplier", "fornecedor_id": "supplier", "fornecedor_nome": "supplier",
    "nome_fornecedor": "supplier", "supplier": "supplier", "supplier_id": "supplier",
    "supplier_name": "supplier", "vendor": "supplier", "vendedor": "supplier",
    "emitter": "supplier", "emitterlegalname": "supplier", "emitterlegaldoc": "supplier",
    "cnpj_emitente": "supplier", "issuer_cnpj": "supplier", "emitente_cnpj": "supplier",
    "nome_emitente": "supplier", "nome_prestador": "supplier", "cnpj_prestador": "supplier",
    "produto": "product", "produto_id": "product", "product": "product",
    "product_id": "product", "sku": "product", "item": "product",
}

SCHEMA_CONTEXT_DEFAULTS: dict[SchemaType, dict[str, str]] = {
    "dim_clientes": {"cnpj": "cpf_cnpj", "cpf": "cpf_cnpj", "cpf_cnpj": "cpf_cnpj", "telefone": "telefone", "nome": "nome", "cidade": "endereco_cidade", "estado": "endereco_uf", "uf": "endereco_uf"},
    "invoices": {"data": "data_competencia_id", "valor": "valor", "total": "valor", "preco": "valor_unitario", "qtd": "quantidade", "pedido": "documento", "id": "documento", "fornecedor": "fornecedor_nome", "cliente": "cliente_nome"},
    "dim_inventory": {"codigo": "sku", "estoque": "sku", "nome": "nome"},
    "fato_transacoes": {"valor": "valor", "total": "valor", "quantidade": "quantidade", "data": "data_competencia_id", "status": "status", "documento": "documento", "categoria": "categoria", "subcategoria": "subcategoria"},
}

CONTEXT_SPECIFIC_MAPPINGS: dict[str, dict[EntityContext, str]] = {
    "cnpj":     {"customer": "cliente_cpf_cnpj", "supplier": "fornecedor_cnpj", "product": "cliente_cpf_cnpj", "neutral": "cliente_cpf_cnpj"},
    "cpf":      {"customer": "cliente_cpf_cnpj", "supplier": "fornecedor_cnpj", "product": "cliente_cpf_cnpj", "neutral": "cliente_cpf_cnpj"},
    "cpf_cnpj": {"customer": "cliente_cpf_cnpj", "supplier": "fornecedor_cnpj", "product": "cliente_cpf_cnpj", "neutral": "cliente_cpf_cnpj"},
    "telefone": {"customer": "cliente_telefone",  "supplier": "fornecedor_telefone", "product": "telefone",       "neutral": "telefone"},
    "phone":    {"customer": "cliente_telefone",  "supplier": "fornecedor_telefone", "product": "telefone",       "neutral": "telefone"},
    "nome":     {"customer": "cliente_nome",      "supplier": "fornecedor_nome",     "product": "nome",           "neutral": "nome"},
    "name":     {"customer": "cliente_nome",      "supplier": "fornecedor_nome",     "product": "nome",           "neutral": "nome"},
    "cidade":   {"customer": "cliente_cidade",    "supplier": "fornecedor_cidade",   "product": "cidade",         "neutral": "cidade"},
    "city":     {"customer": "cliente_cidade",    "supplier": "fornecedor_cidade",   "product": "cidade",         "neutral": "cidade"},
    "estado":   {"customer": "cliente_uf",        "supplier": "fornecedor_uf",       "product": "estado",         "neutral": "estado"},
    "uf":       {"customer": "cliente_uf",        "supplier": "fornecedor_uf",       "product": "estado",         "neutral": "estado"},
    "state":    {"customer": "cliente_uf",        "supplier": "fornecedor_uf",       "product": "estado",         "neutral": "estado"},
    "valor":    {"customer": "valor",             "supplier": "valor",               "product": "valor",          "neutral": "valor"},
    "value":    {"customer": "valor",             "supplier": "valor",               "product": "valor",          "neutral": "valor"},
    "total":    {"customer": "valor",             "supplier": "valor",               "product": "valor",          "neutral": "valor"},
    "data":     {"customer": "data_competencia_id", "supplier": "data_competencia_id", "product": "data_competencia_id", "neutral": "data_competencia_id"},
    "date":     {"customer": "data_competencia_id", "supplier": "data_competencia_id", "product": "data_competencia_id", "neutral": "data_competencia_id"},
}


def detect_table_context(columns: list[str]) -> EntityContext:
    counts: dict[EntityContext, int] = {"customer": 0, "supplier": 0, "product": 0, "neutral": 0}
    for col in columns:
        n = col.lower().strip()
        exact = CONTEXT_SIGNAL_COLUMNS.get(n)
        if exact:
            counts[exact] += 2
            continue
        for signal, ctx in CONTEXT_SIGNAL_COLUMNS.items():
            if n in signal or signal in n:
                counts[ctx] += 1
    best_ctx: EntityContext = "neutral"
    best_n = 0
    for ctx, n in counts.items():
        if ctx != "neutral" and n > best_n:
            best_n = n
            best_ctx = ctx
    return best_ctx if best_n >= 1 else "neutral"


def resolve_with_context(source: str, schema_type: SchemaType, table_ctx: EntityContext) -> str | None:
    n = source.lower().strip()
    ctx_mapping = CONTEXT_SPECIFIC_MAPPINGS.get(n)
    if ctx_mapping and table_ctx != "neutral":
        return ctx_mapping[table_ctx]
    defaults = SCHEMA_CONTEXT_DEFAULTS.get(schema_type, {})
    if defaults.get(n):
        return defaults[n]
    if ctx_mapping:
        return ctx_mapping[table_ctx]
    return None


# ── Dice coefficient (Sorensen-Dice on bigrams) ─────────────────────────────


def _bigrams(s: str) -> set[str]:
    return {s[i : i + 2] for i in range(len(s) - 1)} if len(s) >= 2 else {s}


def compare_two_strings(a: str, b: str) -> float:
    """Sorensen-Dice coefficient on character bigrams. Same as the
    string-similarity@4.0.4 npm package used by the Deno EF.

    Edge cases match the npm source (in this exact order):
      - either string empty → 0.0
      - identical strings → 1.0
      - either string < 2 chars → 0.0
      - otherwise bigram Dice coefficient
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if len(a) < 2 or len(b) < 2:
        return 0.0
    a_bigrams = _bigrams(a)
    b_bigrams = _bigrams(b)
    if not a_bigrams or not b_bigrams:
        return 0.0
    intersection = len(a_bigrams & b_bigrams)
    return (2.0 * intersection) / (len(a_bigrams) + len(b_bigrams))


# ── Matching logic ───────────────────────────────────────────────────────────


def build_alias_cache(canonical_defs: list[CanonicalColumnDef]) -> dict[str, str]:
    cache: dict[str, str] = {}
    for def_ in canonical_defs:
        cache[def_.column_name.lower()] = def_.column_name
        for alias in COLUMN_ALIASES.get(def_.column_name, []):
            cache[alias.lower()] = def_.column_name
    return cache


def find_best_match(
    source: str,
    canonical_defs: list[CanonicalColumnDef],
) -> tuple[str | None, float]:
    n = source.lower().strip()
    best: str | None = None
    best_score = 0.0
    for def_ in canonical_defs:
        score = compare_two_strings(n, def_.column_name.lower())
        if score > best_score:
            best_score = score
            best = def_.column_name
        for alias in COLUMN_ALIASES.get(def_.column_name, []):
            s = compare_two_strings(n, alias.lower())
            if s > best_score:
                best_score = s
                best = def_.column_name
    return best, best_score


def _process_match(
    result: SchemaMatchResult,
    source: str,
    canonical: str | None,
    confidence: float,
    used: set[str],
    canonical_defs: list[CanonicalColumnDef],
) -> None:
    if canonical and confidence >= HIGH_CONFIDENCE_THRESHOLD:
        result.matched[source] = canonical
        result.confidence_scores[source] = round(confidence, 2)
        used.add(canonical)
    elif canonical and confidence >= MEDIUM_CONFIDENCE_THRESHOLD:
        result.needs_review.append({
            "source": source,
            "candidates": [{"canonical": canonical, "confidence": round(confidence, 2)}],
        })
        result.confidence_scores[source] = round(confidence, 2)
    else:
        result.unmatched.append(source)


def auto_match(
    source_columns: list[str],
    schema_type: SchemaType,
    canonical_defs: list[CanonicalColumnDef],
) -> SchemaMatchResult:
    alias_cache = build_alias_cache(canonical_defs)
    table_ctx = detect_table_context(source_columns)
    result = SchemaMatchResult(detected_context=table_ctx)
    used: set[str] = set()

    all_matches: list[dict[str, Any]] = []
    for src in source_columns:
        n = src.lower().strip()
        exact = alias_cache.get(n)
        if exact:
            all_matches.append({"source": src, "canonical": exact, "confidence": 1.0})
            continue

        ctx_resolved = resolve_with_context(src, schema_type, table_ctx)
        if ctx_resolved and any(d.column_name == ctx_resolved for d in canonical_defs):
            all_matches.append({"source": src, "canonical": ctx_resolved, "confidence": 0.95})
            continue

        canonical, confidence = find_best_match(src, canonical_defs)
        all_matches.append({"source": src, "canonical": canonical, "confidence": confidence})

    all_matches.sort(key=lambda m: m["confidence"], reverse=True)

    for m in all_matches:
        if m["canonical"] and m["canonical"] in used:
            fallback: str | None = None
            fallback_score = 0.0
            for def_ in canonical_defs:
                if def_.column_name in used:
                    continue
                s = compare_two_strings(m["source"].lower().strip(), def_.column_name.lower())
                if s > fallback_score and s >= MEDIUM_CONFIDENCE_THRESHOLD:
                    fallback_score = s
                    fallback = def_.column_name
            _process_match(result, m["source"], fallback, fallback_score, used, canonical_defs)
        else:
            _process_match(result, m["source"], m["canonical"], m["confidence"], used, canonical_defs)

    return result


# ── Public entry point ───────────────────────────────────────────────────────


# Per-process cache (replaces the Deno isolate-level cache). No TTL —
# canonical_columns only changes on schema migrations.
_canonical_cache: dict[str, list[CanonicalColumnDef]] = {}


def load_mappable_columns(db: Any, table_name: str) -> list[CanonicalColumnDef]:
    """Load canonical column defs from public.canonical_columns. Cached
    per process. `db` is any object with a `.table(name).select(cols).eq(...).execute()`
    chain (e.g. a Supabase client or a SQLAlchemy session wrapper)."""
    if table_name in _canonical_cache:
        return _canonical_cache[table_name]

    try:
        resp = (
            db.table("canonical_columns")
            .select("column_name,data_type,is_required,description,examples")
            .eq("table_name", table_name)
            .eq("category", "mappable")
            .order("column_name")
            .execute()
        )
        rows = getattr(resp, "data", None) or []
    except Exception as e:
        logger.error("Failed to load canonical_columns for %s: %s", table_name, e)
        return []

    defs = [
        CanonicalColumnDef(
            column_name=row["column_name"],
            data_type=row.get("data_type", ""),
            is_required=bool(row.get("is_required", False)),
            description=row.get("description", ""),
            examples=row.get("examples") or [],
        )
        for row in rows
    ]
    _canonical_cache[table_name] = defs
    return defs


def get_canonical_defs(db: Any, schema_type: SchemaType) -> list[CanonicalColumnDef]:
    """Get canonical column defs for a schema type. The "invoices"
    composite schema uses the hardcoded INVOICES_COLUMNS; the others
    load from public.canonical_columns."""
    if schema_type == "invoices":
        return INVOICES_COLUMNS
    table = SCHEMA_TO_TABLE.get(schema_type)
    if not table:
        return []
    return load_mappable_columns(db, table)


VALID_SCHEMA_TYPES: tuple[SchemaType, ...] = (
    "invoices", "fato_transacoes", "dim_clientes", "dim_inventory",
)


def match_columns(
    db: Any,
    source_columns: list[str],
    schema_type: str = "invoices",
) -> SchemaMatchResult:
    """Public entry point. Matches `source_columns` against the canonical
    schema for `schema_type`. Returns a `SchemaMatchResult` with
    `matched`, `unmatched`, `needs_review`, `confidence_scores`,
    `detected_context`. The `to_dict()` method gives the wire format."""
    if not source_columns or not isinstance(source_columns, list):
        raise ValueError("source_columns must be a non-empty array")

    normalized = (
        schema_type.lower() if schema_type.lower() in VALID_SCHEMA_TYPES
        else "invoices"
    )

    canonical_defs = get_canonical_defs(db, normalized)
    if not canonical_defs:
        raise RuntimeError(f"Could not load canonical schema for {normalized}")

    logger.info(
        "matching %d source columns against %d canonical columns (schema=%s)",
        len(source_columns), len(canonical_defs), normalized,
    )
    return auto_match(source_columns, normalized, canonical_defs)
