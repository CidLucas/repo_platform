"""
Schema Matcher Service - Mapeamento automático de colunas usando difflib.

Este serviço faz o DE-PARA entre colunas de fontes externas e o schema canônico Vizu
usando similaridade de strings (difflib) para sugestões automáticas.
"""

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class DataType(Enum):
    """Tipos de dados para classificação de colunas."""
    STRING = "string"
    NUMBER = "number"
    DATETIME = "datetime"
    BOOLEAN = "boolean"
    JSON = "json"
    ARRAY = "array"
    ID = "id"


@dataclass
class MatchResult:
    """Resultado do match de uma coluna."""
    source_column: str
    canonical_column: str | None
    confidence: float
    auto_matched: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_column": self.source_column,
            "canonical_column": self.canonical_column,
            "confidence": round(self.confidence, 2),
            "auto_matched": self.auto_matched
        }


@dataclass
class SchemaMatchResult:
    """Resultado completo do match de um schema."""
    matched: dict[str, str] = field(default_factory=dict)  # {source: canonical}
    unmatched: list[str] = field(default_factory=list)
    confidence_scores: dict[str, float] = field(default_factory=dict)  # {source: score}
    needs_review: list[str] = field(default_factory=list)  # colunas com score médio
    details: list[MatchResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "matched": self.matched,
            "unmatched": self.unmatched,
            "confidence_scores": {k: round(v, 2) for k, v in self.confidence_scores.items()},
            "needs_review": self.needs_review,
            "details": [d.to_dict() for d in self.details]
        }


class SchemaMatcherService:
    """
    Serviço de matching de schemas usando difflib.

    Estratégia:
    1. Normaliza nomes (lowercase, remove prefixos)
    2. Usa difflib.SequenceMatcher para calcular similaridade
    3. Aplica aliases comuns (sinônimos)
    4. Classifica matches por confiança
    """

    # Schema canônico Vizu - Colunas padrão para cada tipo de recurso
    CANONICAL_SCHEMAS: dict[str, list[str]] = {
        # Canonical schema aligned with analytics expectations (silver tables)
        "invoices": [
            "order_id",
            "data_transacao",
            "emitter_nome",
            "emitter_cnpj",
            "emitter_telefone",
            "emitterstateuf",
            "receiver_nome",
            "receiver_cpf_cnpj",
            "receiver_telefone",
            "receiver_rua",
            "receiver_numero",
            "receiver_bairro",
            "receiver_cidade",
            "receiver_uf",
            "receiver_cep",
            "receiverstateuf",
            "raw_product_description",
            "quantidade",
            "valor_unitario",
            "valor_total_emitter",
            "status",
        ],
        "products": [
            "product_id",
            "product_name",
            "description",
            "price",
            "cost_price",
            "compare_at_price",
            "sku",
            "barcode",
            "quantity",
            "stock_quantity",
            "weight",
            "weight_unit",
            "category",
            "subcategory",
            "brand",
            "vendor",
            "tags",
            "status",
            "is_active",
            "image_url",
            "images",
            "variants",
            "created_at",
            "updated_at",
            "published_at",
        ],
        "orders": [
            "order_id",
            "order_number",
            "order_date",
            "created_at",
            "updated_at",
            "status",
            "financial_status",
            "fulfillment_status",
            "customer_id",
            "customer_email",
            "customer_name",
            "subtotal",
            "total_amount",
            "total_tax",
            "total_discount",
            "shipping_cost",
            "currency",
            "payment_method",
            "shipping_address",
            "billing_address",
            "line_items",
            "notes",
            "tags",
            "source",
            "cancelled_at",
            "closed_at",
        ],
        "customers": [
            "customer_id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "company",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "zip_code",
            "orders_count",
            "total_spent",
            "tags",
            "notes",
            "accepts_marketing",
            "created_at",
            "updated_at",
            "last_order_at",
        ],
        "inventory": [
            "inventory_id",
            "product_id",
            "sku",
            "variant_id",
            "location_id",
            "location_name",
            "quantity",
            "available",
            "reserved",
            "incoming",
            "updated_at",
        ],
        "categories": [
            "category_id",
            "name",
            "slug",
            "description",
            "parent_id",
            "image_url",
            "position",
            "is_active",
            "created_at",
            "updated_at",
        ],
    }

    # Aliases/sinônimos comuns para melhorar o match
    COLUMN_ALIASES: dict[str, list[str]] = {
        # Invoices (canonical aligned to analytics: order_id/data_transacao/...)
        # NOTE: order_id is defined later in Orders section to consolidate all aliases
        "data_transacao": [
            "emittedat_operatorinvoice",
            "createdat_invoicecredit",
            "createdat_operatorinvoice",
            "createdat_product",
            "order_date",
            "data_pedido",
        ],
        "emitter_nome": ["emitterlegalname", "emitterfantasyname", "nome_emitter"],
        "emitter_cnpj": ["emitterlegaldoc", "emitter_cnpj", "companyid", "cnpj_emitter"],
        "receiver_nome": ["receiverlegalname", "receiverfantasyname", "nome_receiver"],
        "receiver_cpf_cnpj": ["receiverlegaldoc", "receiver_cnpj", "cpf_cnpj_receiver"],
        "receiver_telefone": ["receiverphone", "receiver_phone", "telefone_receiver", "fone_receiver", "phone_receiver"],
        "receiver_rua": ["receiverstreet", "receiver_street", "rua_receiver", "logradouro_receiver", "endereco_receiver"],
        "receiver_numero": ["receivernumber", "receiver_number", "numero_receiver", "num_receiver"],
        "receiver_bairro": ["receiverneighborhood", "receiver_neighborhood", "bairro_receiver", "district_receiver"],
        "receiver_cidade": ["receivercity", "receiver_city", "cidade_receiver", "city_receiver"],
        "receiver_uf": ["receiverstate", "receiver_state", "estado_receiver", "uf_receiver"],
        "receiver_cep": ["receiverpostalcode", "receiver_postal_code", "cep_receiver", "zipcode_receiver"],
        "emitter_telefone": ["emitterphone", "emitter_phone", "telefone_emitter", "fone_emitter", "phone_emitter"],
        "raw_product_description": ["description_product", "material", "descricao_produto", "ncm", "produto"],
        "quantidade": ["quantitytraded_product", "quantitytradedkg_product", "quantity"],
        "valor_unitario": ["unitprice_product", "unitpricekg_product", "valor_unitario"],
        "valor_total_emitter": ["price_operatorinvoice", "totalprice_product", "valor_total", "total_price"],
        "status": ["status_operatorinvoice", "status_product", "status"],
        # Products
        "product_id": ["id", "productid", "prod_id", "item_id", "sku_id"],
        "product_name": ["name", "title", "product_title", "item_name", "productname"],
        "description": ["body", "body_html", "content", "details", "product_description", "desc"],
        "price": ["unit_price", "sale_price", "selling_price", "preco", "valor"],
        "cost_price": ["cost", "custo", "purchase_price", "wholesale_price"],
        "sku": ["item_sku", "product_sku", "codigo", "code"],
        "barcode": ["ean", "upc", "gtin", "codigo_barras"],
        "quantity": ["qty", "stock", "estoque", "inventory_quantity"],
        "stock_quantity": ["available_quantity", "qty_available", "in_stock"],
        "category": ["category_name", "categoria", "type", "product_type"],
        "brand": ["marca", "manufacturer", "fabricante"],
        "vendor": ["supplier", "fornecedor", "seller"],
        "image_url": ["image", "photo", "thumbnail", "imagem", "foto"],
        "created_at": ["createdat", "date_created", "creation_date", "criado_em"],
        "updated_at": ["updatedat", "date_modified", "modification_date", "atualizado_em"],

        # Orders
        # NOTE: order_id already defined above in Invoices section with id_operatorinvoice
        # Merging additional order-specific aliases here (this will override the previous definition)
        "order_id": [
            # Invoice-specific (from BigQuery)
            "id_operatorinvoice",
            "id_invoice",
            "invoice_id",
            # Order-specific
            "id",
            "orderid",
            "pedido_id",
            "numero_pedido",
            "id_pedido",
            "order_id",
        ],
        "order_number": ["number", "order_no", "numero", "pedido_numero"],
        "order_date": ["date", "purchase_date", "data_pedido", "data_compra"],
        "total_amount": ["total", "grand_total", "order_total", "total_price", "valor_total"],
        "subtotal": ["sub_total", "items_total"],
        "total_tax": ["tax", "tax_amount", "impostos"],
        "total_discount": ["discount", "discount_amount", "desconto"],
        "shipping_cost": ["shipping", "freight", "frete", "shipping_amount"],
        "customer_email": ["email", "buyer_email", "client_email"],
        "customer_name": ["buyer_name", "client_name", "nome_cliente"],
        "status": ["order_status", "estado", "situacao"],
        "payment_method": ["payment_type", "forma_pagamento", "metodo_pagamento"],

        # Customers
        "customer_id": ["id", "client_id", "user_id", "cliente_id"],
        "email": ["customer_email", "email_address", "e_mail"],
        "first_name": ["firstname", "given_name", "nome"],
        "last_name": ["lastname", "family_name", "surname", "sobrenome"],
        "full_name": ["name", "customer_name", "nome_completo"],
        "phone": ["telephone", "mobile", "celular", "telefone", "phone_number"],
        "address": ["street", "address_line", "endereco", "logradouro"],
        "city": ["cidade", "locality"],
        "state": ["estado", "province", "region", "uf"],
        "country": ["pais", "country_code"],
        "postal_code": ["cep", "zipcode", "postcode"],
        "zip_code": ["cep", "postal_code", "postcode"],
    }

    # Prefixos comuns a serem removidos na normalização
    COMMON_PREFIXES = [
        "product_", "order_", "customer_", "item_", "line_",
        "shipping_", "billing_", "payment_", "inventory_",
        "fk_", "pk_", "tb_", "tbl_", "col_",
    ]

    # Thresholds de confiança (ajustados para evitar false positives)
    HIGH_CONFIDENCE_THRESHOLD = 0.85  # Match automático - aumentado de 0.75
    MEDIUM_CONFIDENCE_THRESHOLD = 0.70  # Precisa revisão - aumentado de 0.50

    # Mapeamento de tipos de dados para cada coluna canônica
    COLUMN_DATA_TYPES: dict[str, DataType] = {
        # IDs
        "order_id": DataType.ID,
        "product_id": DataType.ID,
        "customer_id": DataType.ID,
        "inventory_id": DataType.ID,
        "category_id": DataType.ID,
        "variant_id": DataType.ID,
        "location_id": DataType.ID,
        "parent_id": DataType.ID,

        # Datetime
        "data_transacao": DataType.DATETIME,
        "order_date": DataType.DATETIME,
        "created_at": DataType.DATETIME,
        "updated_at": DataType.DATETIME,
        "published_at": DataType.DATETIME,
        "cancelled_at": DataType.DATETIME,
        "closed_at": DataType.DATETIME,
        "last_order_at": DataType.DATETIME,

        # Numbers
        "quantidade": DataType.NUMBER,
        "quantity": DataType.NUMBER,
        "stock_quantity": DataType.NUMBER,
        "available": DataType.NUMBER,
        "reserved": DataType.NUMBER,
        "incoming": DataType.NUMBER,
        "valor_unitario": DataType.NUMBER,
        "valor_total_emitter": DataType.NUMBER,
        "price": DataType.NUMBER,
        "cost_price": DataType.NUMBER,
        "compare_at_price": DataType.NUMBER,
        "subtotal": DataType.NUMBER,
        "total_amount": DataType.NUMBER,
        "total_tax": DataType.NUMBER,
        "total_discount": DataType.NUMBER,
        "shipping_cost": DataType.NUMBER,
        "weight": DataType.NUMBER,
        "orders_count": DataType.NUMBER,
        "total_spent": DataType.NUMBER,
        "position": DataType.NUMBER,

        # JSON/Complex
        "shipping_address": DataType.JSON,
        "billing_address": DataType.JSON,
        "line_items": DataType.JSON,
        "variants": DataType.JSON,
        "address": DataType.JSON,

        # Arrays
        "images": DataType.ARRAY,
        "tags": DataType.ARRAY,

        # Booleans
        "is_active": DataType.BOOLEAN,
        "accepts_marketing": DataType.BOOLEAN,

        # Strings (default for most text fields)
        "emitter_nome": DataType.STRING,
        "emitter_cnpj": DataType.STRING,
        "receiver_nome": DataType.STRING,
        "receiver_cpf_cnpj": DataType.STRING,
        "raw_product_description": DataType.STRING,
        "status": DataType.STRING,
        "product_name": DataType.STRING,
        "description": DataType.STRING,
        "sku": DataType.STRING,
        "barcode": DataType.STRING,
        "category": DataType.STRING,
        "subcategory": DataType.STRING,
        "brand": DataType.STRING,
        "vendor": DataType.STRING,
        "image_url": DataType.STRING,
        "order_number": DataType.STRING,
        "financial_status": DataType.STRING,
        "fulfillment_status": DataType.STRING,
        "customer_email": DataType.STRING,
        "customer_name": DataType.STRING,
        "currency": DataType.STRING,
        "payment_method": DataType.STRING,
        "notes": DataType.STRING,
        "source": DataType.STRING,
        "email": DataType.STRING,
        "first_name": DataType.STRING,
        "last_name": DataType.STRING,
        "full_name": DataType.STRING,
        "phone": DataType.STRING,
        "company": DataType.STRING,
        "city": DataType.STRING,
        "state": DataType.STRING,
        "country": DataType.STRING,
        "postal_code": DataType.STRING,
        "zip_code": DataType.STRING,
        "location_name": DataType.STRING,
        "name": DataType.STRING,
        "slug": DataType.STRING,
        "weight_unit": DataType.STRING,
    }

    def __init__(self):
        # Cache de aliases invertido para lookup rápido
        self._alias_to_canonical: dict[str, dict[str, str]] = {}
        self._build_alias_cache()

    def _build_alias_cache(self):
        """Constrói cache invertido de aliases para cada schema."""
        for schema_type, columns in self.CANONICAL_SCHEMAS.items():
            self._alias_to_canonical[schema_type] = {}
            for canonical in columns:
                # Adiciona o próprio nome canônico
                self._alias_to_canonical[schema_type][canonical.lower()] = canonical
                # Adiciona aliases
                if canonical in self.COLUMN_ALIASES:
                    for alias in self.COLUMN_ALIASES[canonical]:
                        self._alias_to_canonical[schema_type][alias.lower()] = canonical

    def infer_data_type(self, column_name: str) -> DataType:
        """
        Infere o tipo de dado de uma coluna baseado no nome.

        Args:
            column_name: Nome da coluna

        Returns:
            DataType inferido
        """
        normalized = column_name.lower()

        # ID fields
        if normalized.endswith('_id') or normalized.startswith('id_') or normalized == 'id':
            return DataType.ID

        # Datetime fields
        datetime_keywords = ['date', 'time', 'timestamp', 'created', 'updated', 'deleted',
                           'published', 'cancelled', 'closed', 'at', 'data', 'hora']
        if any(kw in normalized for kw in datetime_keywords):
            return DataType.DATETIME

        # Number fields
        number_keywords = ['price', 'preco', 'valor', 'amount', 'total', 'subtotal',
                          'quantity', 'quantidade', 'qty', 'count', 'numero', 'weight',
                          'tax', 'discount', 'shipping', 'cost', 'spent', 'position']
        if any(kw in normalized for kw in number_keywords):
            return DataType.NUMBER

        # Boolean fields
        boolean_keywords = ['is_', 'has_', 'active', 'enabled', 'accepts', 'verified']
        if any(kw in normalized for kw in boolean_keywords):
            return DataType.BOOLEAN

        # JSON/Complex fields
        json_keywords = ['address', 'metadata', 'config', 'settings', 'data', 'info',
                        'details', 'attributes', 'properties', 'items']
        if any(kw in normalized for kw in json_keywords):
            # Could be JSON or string, default to JSON if plural or contains specific words
            if normalized.endswith('s') or 'line_items' in normalized or 'variants' in normalized:
                return DataType.JSON

        # Array fields
        if normalized.endswith('s') and any(kw in normalized for kw in ['image', 'tag', 'variant']):
            return DataType.ARRAY

        # Default to STRING
        return DataType.STRING

    def normalize_column_name(self, name: str) -> str:
        """
        Normaliza nome de coluna para comparação.

        Transformações:
        - Converte para lowercase (ONLY)

        SIMPLIFIED: Previously did too much normalization which broke matches.
        Now only lowercase for consistent comparison.
        """
        normalized = name.lower().strip()
        logger.debug(f"Normalized '{name}' → '{normalized}'")
        return normalized

    def calculate_similarity(self, s1: str, s2: str) -> float:
        """
        Calcula similaridade entre duas strings usando SequenceMatcher.

        Args:
            s1: Primeira string
            s2: Segunda string

        Returns:
            Score de similaridade entre 0.0 e 1.0
        """
        return SequenceMatcher(None, s1, s2).ratio()

    def find_best_match(
        self,
        source_column: str,
        canonical_columns: list[str],
        schema_type: str
    ) -> tuple[str | None, float]:
        """
        Encontra o melhor match para uma coluna de origem usando estratégia simplificada:

        Stage 1: Exact match com nomes normalizados (includes aliases via cache)
        Stage 2: Fuzzy match dentro de colunas de tipo compatível
        Stage 3: Fuzzy match em todas as colunas restantes (fallback)

        Args:
            source_column: Nome da coluna de origem
            canonical_columns: Lista de colunas canônicas
            schema_type: Tipo do schema (products, orders, etc.)

        Returns:
            Tuple (melhor_match, score)
        """
        normalized_source = self.normalize_column_name(source_column)
        logger.info(f"[MATCH] Finding match for '{source_column}' (normalized: '{normalized_source}')")

        # STAGE 1: Exact match (combines old Stage 1 & 2)
        # First check alias cache for instant match
        alias_cache = self._alias_to_canonical.get(schema_type, {})
        logger.debug(f"  Checking alias cache for '{normalized_source}' in schema '{schema_type}'")
        logger.debug(f"  Alias cache has {len(alias_cache)} entries")

        if normalized_source in alias_cache:
            canonical = alias_cache[normalized_source]
            if canonical in canonical_columns:
                logger.info(f"  ✓ Stage 1 - Exact alias match: '{source_column}' → '{canonical}' (score: 1.0)")
                return canonical, 1.0
            else:
                logger.warning(f"  ⚠ Alias matched '{canonical}' but not in canonical_columns for this schema")

        # Then check direct normalized match
        for canonical in canonical_columns:
            normalized_canonical = self.normalize_column_name(canonical)
            if normalized_source == normalized_canonical:
                logger.info(f"  ✓ Stage 1 - Exact normalized match: '{source_column}' → '{canonical}' (score: 1.0)")
                return canonical, 1.0

        logger.debug(f"  ✗ No exact match found for '{source_column}'")

        # Detecta tipo de dado da coluna de origem
        source_type = self.infer_data_type(source_column)
        logger.debug(f"  Inferred type for '{source_column}': {source_type.value}")

        # STAGE 2: Fuzzy match dentro de colunas de tipo compatível
        compatible_columns = []
        for canonical in canonical_columns:
            canonical_type = self.COLUMN_DATA_TYPES.get(canonical, DataType.STRING)
            # Aceita match se os tipos são iguais, ou se ambos são textuais (STRING/ID)
            if canonical_type == source_type or \
               (canonical_type in [DataType.STRING, DataType.ID] and source_type in [DataType.STRING, DataType.ID]):
                compatible_columns.append(canonical)

        logger.debug(f"  Found {len(compatible_columns)} type-compatible columns (out of {len(canonical_columns)})")

        if compatible_columns:
            best_match, best_score = self._fuzzy_match_in_columns(
                source_column, normalized_source, compatible_columns
            )
            if best_score >= 0.6:  # Threshold mínimo para fuzzy match
                logger.info(f"  ✓ Stage 2 - Type-filtered fuzzy match: '{source_column}' → '{best_match}' (score: {best_score:.2f}, type: {source_type.value})")
                return best_match, best_score
            else:
                logger.debug(f"  ✗ Best type-compatible match score {best_score:.2f} below 0.6 threshold")

        # STAGE 3: Fuzzy match em todas as colunas (fallback)
        logger.debug(f"  Trying fuzzy match across all {len(canonical_columns)} canonical columns")
        best_match, best_score = self._fuzzy_match_in_columns(
            source_column, normalized_source, canonical_columns
        )

        # Penaliza matches entre tipos incompatíveis
        if best_match:
            canonical_type = self.COLUMN_DATA_TYPES.get(best_match, DataType.STRING)
            if canonical_type != source_type and \
               not (canonical_type in [DataType.STRING, DataType.ID] and source_type in [DataType.STRING, DataType.ID]):
                # Reduz score em 30% se os tipos são incompatíveis
                original_score = best_score
                best_score = best_score * 0.7
                logger.debug(f"  ⚠ Type-incompatible match penalized: {original_score:.2f} → {best_score:.2f}")

            if best_score >= 0.6:
                logger.info(f"  ✓ Stage 3 - Global fuzzy match: '{source_column}' → '{best_match}' (score: {best_score:.2f})")
            else:
                logger.warning(f"  ✗ No good match found for '{source_column}' (best: '{best_match}' with score {best_score:.2f})")
        else:
            logger.warning(f"  ✗ No match found for '{source_column}'")

        return best_match, best_score

    def _fuzzy_match_in_columns(
        self,
        source_column: str,  # noqa: ARG002 - kept for API consistency
        normalized_source: str,
        candidate_columns: list[str]
    ) -> tuple[str | None, float]:
        """
        Realiza fuzzy matching em um conjunto de colunas candidatas.

        Args:
            source_column: Nome original da coluna de origem (não usado, mantido para consistência da API)
            normalized_source: Nome normalizado da coluna de origem
            candidate_columns: Lista de colunas candidatas

        Returns:
            Tuple (melhor_match, score)
        """
        best_match = None
        best_score = 0.0

        for canonical in candidate_columns:
            normalized_canonical = self.normalize_column_name(canonical)

            # Calcula similaridade direta
            score = self.calculate_similarity(normalized_source, normalized_canonical)

            # Verifica também com aliases
            if canonical in self.COLUMN_ALIASES:
                for alias in self.COLUMN_ALIASES[canonical]:
                    normalized_alias = self.normalize_column_name(alias)
                    alias_score = self.calculate_similarity(normalized_source, normalized_alias)
                    score = max(score, alias_score)

            if score > best_score:
                best_score = score
                best_match = canonical

        return best_match, best_score

    def auto_match(
        self,
        source_columns: list[str],
        schema_type: str,
        high_threshold: float = None,
        medium_threshold: float = None
    ) -> SchemaMatchResult:
        """
        Faz matching automático de colunas de origem para schema canônico.

        Args:
            source_columns: Lista de colunas da fonte de dados
            schema_type: Tipo do schema (products, orders, customers, inventory)
            high_threshold: Threshold para match automático (default: 0.85)
            medium_threshold: Threshold para revisão (default: 0.70)

        Returns:
            SchemaMatchResult com matches, não-mapeados e scores
        """
        if schema_type not in self.CANONICAL_SCHEMAS:
            raise ValueError(f"Schema type '{schema_type}' não suportado. "
                           f"Use: {list(self.CANONICAL_SCHEMAS.keys())}")

        high_threshold = high_threshold or self.HIGH_CONFIDENCE_THRESHOLD
        medium_threshold = medium_threshold or self.MEDIUM_CONFIDENCE_THRESHOLD

        logger.info("=" * 80)
        logger.info(f"[AUTO_MATCH] Starting schema matching for '{schema_type}'")
        logger.info(f"  Source columns ({len(source_columns)}): {source_columns[:10]}{'...' if len(source_columns) > 10 else ''}")
        logger.info(f"  High confidence threshold: {high_threshold}")
        logger.info(f"  Medium confidence threshold: {medium_threshold}")
        logger.info("=" * 80)

        canonical_columns = self.CANONICAL_SCHEMAS[schema_type]
        result = SchemaMatchResult()

        # Track all matches for each canonical column to pick the best one
        # canonical_name -> [(source_col, score), ...]
        canonical_matches: dict[str, list[tuple[str, float]]] = {}

        # First pass: Find all potential matches
        for source_col in source_columns:
            best_match, score = self.find_best_match(source_col, canonical_columns, schema_type)

            match_result = MatchResult(
                source_column=source_col,
                canonical_column=best_match if score >= medium_threshold else None,
                confidence=score,
                auto_matched=score >= high_threshold
            )
            result.details.append(match_result)

            if best_match and score >= medium_threshold:
                # Track this potential match
                if best_match not in canonical_matches:
                    canonical_matches[best_match] = []
                canonical_matches[best_match].append((source_col, score))

        # Second pass: Resolve conflicts by picking highest score
        logger.info(f"\n[CONFLICT RESOLUTION] Resolving {len(canonical_matches)} potential matches")

        for canonical, candidates in canonical_matches.items():
            if len(candidates) > 1:
                # Multiple source columns map to same canonical
                # Use multi-criteria sorting for tiebreaker:
                # 1. Score (descending) - higher is better
                # 2. Fuzzy similarity to canonical (descending) - closer match is better
                candidates_sorted = sorted(candidates, key=lambda c: (
                    -c[1],  # Higher score first
                    -self.calculate_similarity(c[0].lower(), canonical.lower())  # Higher similarity as tiebreaker
                ))

                best_candidate, best_score = candidates_sorted[0]

                # Log the selection reasoning
                if all(c[1] == best_score for c in candidates_sorted):
                    # All have same score - used fuzzy similarity tiebreaker
                    logger.warning(
                        f"  ⚠ Conflict: {len(candidates)} columns with equal score ({best_score:.2f}) map to '{canonical}'. "
                        f"Using tiebreaker (fuzzy similarity): '{best_candidate}' chosen over "
                        f"{[c[0] for c in candidates_sorted[1:]]}"
                    )
                else:
                    # Different scores - straightforward
                    logger.warning(
                        f"  ⚠ Conflict: {len(candidates)} columns map to '{canonical}'. "
                        f"Picking '{best_candidate}' (score: {best_score:.2f}) over "
                        f"{[f'{c[0]}({c[1]:.2f})' for c in candidates_sorted[1:]]}"
                    )

                # Only use the best match
                result.matched[best_candidate] = canonical
                result.confidence_scores[best_candidate] = best_score

                if best_score >= high_threshold:
                    # High confidence - auto-matched
                    pass  # Already marked as auto_matched in details
                else:
                    # Medium confidence - needs review
                    result.needs_review.append(best_candidate)

                # Mark others as unmatched
                for rejected_col, rejected_score in candidates_sorted[1:]:
                    result.unmatched.append(rejected_col)
                    result.confidence_scores[rejected_col] = rejected_score
                    logger.debug(f"    Rejected '{rejected_col}' (score: {rejected_score:.2f})")
            else:
                # Single match - use it
                source_col, score = candidates[0]
                result.matched[source_col] = canonical
                result.confidence_scores[source_col] = score

                if score >= high_threshold:
                    logger.info(f"  ✓ High confidence: '{source_col}' → '{canonical}' (score: {score:.2f})")
                else:
                    logger.info(f"  ⚠ Needs review: '{source_col}' → '{canonical}' (score: {score:.2f})")
                    result.needs_review.append(source_col)

        # Third pass: Mark columns with no acceptable match as unmatched
        for detail in result.details:
            if detail.source_column not in result.matched and detail.source_column not in result.unmatched:
                result.unmatched.append(detail.source_column)
                result.confidence_scores[detail.source_column] = detail.confidence
                logger.debug(f"  ✗ Unmatched: '{detail.source_column}' (best score: {detail.confidence:.2f})")

        logger.info(f"\n[SUMMARY] Schema match for '{schema_type}':")
        logger.info(f"  ✓ Matched: {len(result.matched)} columns")
        logger.info(f"  ⚠ Needs review: {len(result.needs_review)} columns")
        logger.info(f"  ✗ Unmatched: {len(result.unmatched)} columns")
        logger.info("\n  Matched columns:")
        for source, canonical in list(result.matched.items())[:20]:
            score = result.confidence_scores[source]
            logger.info(f"    '{source}' → '{canonical}' (score: {score:.2f})")
        if len(result.matched) > 20:
            logger.info(f"    ... and {len(result.matched) - 20} more")
        logger.info("=" * 80)

        return result

    def get_canonical_schema(self, schema_type: str) -> list[str]:
        """Retorna o schema canônico para um tipo de recurso."""
        if schema_type not in self.CANONICAL_SCHEMAS:
            raise ValueError(f"Schema type '{schema_type}' não suportado")
        return self.CANONICAL_SCHEMAS[schema_type].copy()

    def get_supported_types(self) -> list[str]:
        """Retorna tipos de schema suportados."""
        return list(self.CANONICAL_SCHEMAS.keys())


# Instância global
schema_matcher = SchemaMatcherService()
