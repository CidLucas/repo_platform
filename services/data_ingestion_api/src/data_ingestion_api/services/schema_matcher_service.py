"""
Schema Matcher Service - Mapeamento automático de colunas usando difflib.

Este serviço faz o DE-PARA entre colunas de fontes externas e o schema canônico Vizu
usando similaridade de strings (difflib) para sugestões automáticas.
"""

import re
import logging
from difflib import SequenceMatcher, get_close_matches
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Resultado do match de uma coluna."""
    source_column: str
    canonical_column: Optional[str]
    confidence: float
    auto_matched: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_column": self.source_column,
            "canonical_column": self.canonical_column,
            "confidence": round(self.confidence, 2),
            "auto_matched": self.auto_matched
        }


@dataclass
class SchemaMatchResult:
    """Resultado completo do match de um schema."""
    matched: Dict[str, str] = field(default_factory=dict)  # {source: canonical}
    unmatched: List[str] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)  # {source: score}
    needs_review: List[str] = field(default_factory=list)  # colunas com score médio
    details: List[MatchResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
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
    CANONICAL_SCHEMAS: Dict[str, List[str]] = {
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
    COLUMN_ALIASES: Dict[str, List[str]] = {
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
        "order_id": ["id", "orderid", "pedido_id", "numero_pedido"],
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
    
    # Thresholds de confiança
    HIGH_CONFIDENCE_THRESHOLD = 0.75  # Match automático
    MEDIUM_CONFIDENCE_THRESHOLD = 0.50  # Precisa revisão
    
    def __init__(self):
        # Cache de aliases invertido para lookup rápido
        self._alias_to_canonical: Dict[str, Dict[str, str]] = {}
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
    
    def normalize_column_name(self, name: str) -> str:
        """
        Normaliza nome de coluna para comparação.
        
        Transformações:
        - Converte para lowercase
        - Remove prefixos comuns
        - Remove caracteres especiais (mantém _)
        - Remove números no início
        """
        # Lowercase
        normalized = name.lower().strip()
        
        # Remove caracteres especiais exceto underscore
        normalized = re.sub(r'[^a-z0-9_]', '_', normalized)
        
        # Remove underscores duplicados
        normalized = re.sub(r'_+', '_', normalized)
        
        # Remove underscores no início e fim
        normalized = normalized.strip('_')
        
        # Remove prefixos comuns
        for prefix in self.COMMON_PREFIXES:
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break
        
        # Remove números no início
        normalized = re.sub(r'^[0-9]+_?', '', normalized)
        
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
        canonical_columns: List[str],
        schema_type: str
    ) -> Tuple[Optional[str], float]:
        """
        Encontra o melhor match para uma coluna de origem.
        
        Args:
            source_column: Nome da coluna de origem
            canonical_columns: Lista de colunas canônicas
            schema_type: Tipo do schema (products, orders, etc.)
            
        Returns:
            Tuple (melhor_match, score)
        """
        normalized_source = self.normalize_column_name(source_column)
        best_match = None
        best_score = 0.0
        
        # 1. Verifica match exato com aliases
        alias_cache = self._alias_to_canonical.get(schema_type, {})
        if normalized_source in alias_cache:
            canonical = alias_cache[normalized_source]
            if canonical in canonical_columns:
                return canonical, 1.0
        
        # 2. Verifica match exato com nome normalizado
        for canonical in canonical_columns:
            normalized_canonical = self.normalize_column_name(canonical)
            if normalized_source == normalized_canonical:
                return canonical, 1.0
        
        # 3. Usa difflib para encontrar matches aproximados
        for canonical in canonical_columns:
            normalized_canonical = self.normalize_column_name(canonical)
            
            # Calcula similaridade direta
            score = self.calculate_similarity(normalized_source, normalized_canonical)
            
            # Verifica também com aliases
            if canonical in self.COLUMN_ALIASES:
                for alias in self.COLUMN_ALIASES[canonical]:
                    alias_score = self.calculate_similarity(normalized_source, alias.lower())
                    score = max(score, alias_score)
            
            if score > best_score:
                best_score = score
                best_match = canonical
        
        return best_match, best_score
    
    def auto_match(
        self, 
        source_columns: List[str], 
        schema_type: str,
        high_threshold: float = None,
        medium_threshold: float = None
    ) -> SchemaMatchResult:
        """
        Faz matching automático de colunas de origem para schema canônico.
        
        Args:
            source_columns: Lista de colunas da fonte de dados
            schema_type: Tipo do schema (products, orders, customers, inventory)
            high_threshold: Threshold para match automático (default: 0.75)
            medium_threshold: Threshold para revisão (default: 0.50)
            
        Returns:
            SchemaMatchResult com matches, não-mapeados e scores
        """
        if schema_type not in self.CANONICAL_SCHEMAS:
            raise ValueError(f"Schema type '{schema_type}' não suportado. "
                           f"Use: {list(self.CANONICAL_SCHEMAS.keys())}")
        
        high_threshold = high_threshold or self.HIGH_CONFIDENCE_THRESHOLD
        medium_threshold = medium_threshold or self.MEDIUM_CONFIDENCE_THRESHOLD
        
        canonical_columns = self.CANONICAL_SCHEMAS[schema_type]
        result = SchemaMatchResult()
        
        # Track colunas canônicas já usadas para evitar duplicatas
        used_canonicals = set()
        
        for source_col in source_columns:
            best_match, score = self.find_best_match(source_col, canonical_columns, schema_type)
            
            # Evita mapear múltiplas colunas para o mesmo destino
            if best_match and best_match in used_canonicals:
                # Tenta próximo melhor match
                remaining = [c for c in canonical_columns if c not in used_canonicals]
                if remaining:
                    best_match, score = self.find_best_match(source_col, remaining, schema_type)
            
            match_result = MatchResult(
                source_column=source_col,
                canonical_column=best_match if score >= medium_threshold else None,
                confidence=score,
                auto_matched=score >= high_threshold
            )
            result.details.append(match_result)
            
            if score >= high_threshold and best_match:
                # Match de alta confiança - automático
                result.matched[source_col] = best_match
                result.confidence_scores[source_col] = score
                used_canonicals.add(best_match)
                
            elif score >= medium_threshold and best_match:
                # Match de média confiança - precisa revisão
                result.matched[source_col] = best_match
                result.confidence_scores[source_col] = score
                result.needs_review.append(source_col)
                used_canonicals.add(best_match)
                
            else:
                # Sem match aceitável
                result.unmatched.append(source_col)
                result.confidence_scores[source_col] = score
        
        logger.info(f"Schema match para '{schema_type}': "
                   f"{len(result.matched)} matched, "
                   f"{len(result.needs_review)} para revisão, "
                   f"{len(result.unmatched)} não mapeados")
        
        return result
    
    def get_canonical_schema(self, schema_type: str) -> List[str]:
        """Retorna o schema canônico para um tipo de recurso."""
        if schema_type not in self.CANONICAL_SCHEMAS:
            raise ValueError(f"Schema type '{schema_type}' não suportado")
        return self.CANONICAL_SCHEMAS[schema_type].copy()
    
    def get_supported_types(self) -> List[str]:
        """Retorna tipos de schema suportados."""
        return list(self.CANONICAL_SCHEMAS.keys())


# Instância global
schema_matcher = SchemaMatcherService()
