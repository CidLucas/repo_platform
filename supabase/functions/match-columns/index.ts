// Schema Matcher Edge Function
// Port of services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py
// Uses string-similarity for fuzzy matching (equivalent to Python's difflib.SequenceMatcher)

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { compareTwoStrings } from "https://esm.sh/string-similarity@4.0.4";

// =============================================================================
// Types
// =============================================================================

interface MatchCandidate {
    canonical: string;
    confidence: number;
}

interface MatchResult {
    source_column: string;
    canonical_column: string | null;
    confidence: number;
    auto_matched: boolean;
}

interface SchemaMatchResult {
    matched: Record<string, string>;
    unmatched: string[];
    confidence_scores: Record<string, number>;
    needs_review: Array<{
        source: string;
        candidates: MatchCandidate[];
    }>;
    details: MatchResult[];
    detected_context?: string; // The inferred entity context (customer/supplier/product/neutral)
}

type SchemaType = "invoices" | "fcx_vendas" | "dim_produtos" | "fcx_orders" | "dim_clientes" | "dim_inventory" | "fcx_categorias";

// =============================================================================
// Canonical Schemas (Portuguese-aligned with analytics_v2 tables)
// =============================================================================

const CANONICAL_SCHEMAS: Record<SchemaType, string[]> = {
    // Main schema for BigQuery invoice data → analytics_v2.fcx_vendas
    invoices: [
        "pedido_id",
        "data_transacao",
        "fornecedor_nome",
        "fornecedor_cnpj",
        "fornecedor_telefone",
        "fornecedor_uf",
        "fornecedor_cidade",
        "cliente_nome",
        "cliente_cpf_cnpj",
        "cliente_telefone",
        "cliente_rua",
        "cliente_numero",
        "cliente_bairro",
        "cliente_cidade",
        "cliente_uf",
        "cliente_cep",
        "produto_descricao",
        "quantidade",
        "valor_unitario",
        "valor_total",
        "status",
    ],
    // Sales transactions → analytics_v2.fcx_vendas
    fcx_vendas: [
        "venda_id",
        "pedido_id",
        "cliente_id",
        "fornecedor_id",
        "produto_id",
        "data_transacao",
        "quantidade",
        "valor_unitario",
        "valor_total",
        "cliente_cpf_cnpj",
        "fornecedor_cnpj",
        "data_id",
        "hora_id",
        "sequencia_item",
    ],
    // Products dimension → analytics_v2.dim_produtos
    dim_produtos: [
        "produto_id",
        "nome",
        "descricao",
        "preco",
        "preco_custo",
        "sku",
        "codigo_barras",
        "quantidade",
        "quantidade_estoque",
        "peso",
        "unidade_peso",
        "categoria",
        "subcategoria",
        "marca",
        "fornecedor",
        "tags",
        "status",
        "ativo",
        "imagem_url",
        "imagens",
        "variantes",
        "criado_em",
        "atualizado_em",
    ],
    // Orders → analytics_v2.fcx_purchase_orders
    fcx_orders: [
        "pedido_id",
        "numero_pedido",
        "data_pedido",
        "criado_em",
        "atualizado_em",
        "status",
        "status_financeiro",
        "status_entrega",
        "cliente_id",
        "cliente_email",
        "cliente_nome",
        "subtotal",
        "valor_total",
        "imposto_total",
        "desconto_total",
        "frete",
        "moeda",
        "metodo_pagamento",
        "endereco_entrega",
        "endereco_cobranca",
        "itens",
        "observacoes",
        "tags",
        "origem",
    ],
    // Customers dimension → analytics_v2.dim_clientes
    dim_clientes: [
        "cliente_id",
        "email",
        "nome",
        "sobrenome",
        "nome_completo",
        "telefone",
        "empresa",
        "endereco",
        "cidade",
        "estado",
        "pais",
        "cep",
        "total_pedidos",
        "valor_total_gasto",
        "tags",
        "observacoes",
        "aceita_marketing",
        "criado_em",
        "atualizado_em",
        "ultima_compra",
    ],
    // Inventory dimension → analytics_v2.dim_inventory
    dim_inventory: [
        "inventory_id",
        "produto_id",
        "sku",
        "warehouse_code",
        "quantity_on_hand",
        "quantity_reserved",
        "quantity_available",
        "reorder_point",
        "reorder_quantity",
        "unit_cost",
        "last_counted_at",
        "created_at",
        "updated_at",
    ],
    // Categories for financial entries → analytics_v2.fcx_categorias
    fcx_categorias: [
        "id",
        "nome",
        "tipo",
        "grupo",
        "created_at",
    ],
};

// =============================================================================
// Column Aliases (maps source variations → canonical names)
// =============================================================================

const COLUMN_ALIASES: Record<string, string[]> = {
    // =========== INVOICES / VENDAS ===========
    pedido_id: [
        "id_operatorinvoice", "id_invoice", "invoice_id", "order_id",
        "orderid", "numero_pedido", "id_pedido", "order_number", "id",
    ],
    data_transacao: [
        "emittedat_operatorinvoice", "createdat_invoicecredit", "createdat_operatorinvoice",
        "createdat_product", "order_date", "data_pedido", "transaction_date",
        "date", "created_at", "purchase_date", "data_compra",
    ],
    fornecedor_nome: ["emitterlegalname", "emitterfantasyname", "nome_emitter", "supplier_name", "vendor_name"],
    fornecedor_cnpj: ["emitterlegaldoc", "emitter_cnpj", "companyid", "cnpj_emitter", "supplier_cnpj", "vendor_cnpj"],
    fornecedor_telefone: ["emitterphone", "emitter_phone", "telefone_emitter", "supplier_phone"],
    fornecedor_cidade: ["emittercity", "emitter_city", "cidade_emitter", "supplier_city"],
    fornecedor_uf: ["emitterstate", "emitter_state", "uf_emitter", "supplier_state"],
    cliente_nome: ["receiverlegalname", "receiverfantasyname", "nome_receiver", "customer_name", "buyer_name"],
    cliente_cpf_cnpj: ["receiverlegaldoc", "receiver_cnpj", "cpf_cnpj_receiver", "customer_cpf_cnpj", "customer_doc"],
    cliente_telefone: ["receiverphone", "receiver_phone", "telefone_receiver", "customer_phone"],
    cliente_rua: ["receiverstreet", "receiver_street", "rua_receiver", "logradouro_receiver", "customer_street"],
    cliente_numero: ["receivernumber", "receiver_number", "numero_receiver", "customer_number"],
    cliente_bairro: ["receiverneighborhood", "receiver_neighborhood", "bairro_receiver", "customer_neighborhood"],
    cliente_cidade: ["receivercity", "receiver_city", "cidade_receiver", "customer_city"],
    cliente_uf: ["receiverstate", "receiver_state", "estado_receiver", "uf_receiver", "customer_state"],
    cliente_cep: ["receiverpostalcode", "receiver_postal_code", "cep_receiver", "zipcode_receiver", "customer_zip"],
    produto_descricao: ["description_product", "material", "descricao_produto", "ncm", "produto", "product_description"],
    quantidade: ["quantitytraded_product", "quantitytradedkg_product", "quantity", "qty", "qtd"],
    valor_unitario: ["unitprice_product", "unitpricekg_product", "unit_price", "preco_unitario", "price"],
    valor_total: ["price_operatorinvoice", "totalprice_product", "total_price", "total", "grand_total", "order_total"],
    status: ["status_operatorinvoice", "status_product", "order_status", "estado", "situacao"],

    // =========== PRODUCTS ===========
    produto_id: ["product_id", "productid", "prod_id", "item_id", "sku_id", "id"],
    nome: ["name", "title", "product_title", "item_name", "productname", "product_name"],
    descricao: ["body", "body_html", "content", "details", "product_description", "desc", "description"],
    preco: ["price", "unit_price", "sale_price", "selling_price", "valor"],
    preco_custo: ["cost", "custo", "cost_price", "purchase_price", "wholesale_price"],
    sku: ["item_sku", "product_sku", "codigo", "code"],
    codigo_barras: ["barcode", "ean", "upc", "gtin"],
    quantidade_estoque: ["stock_quantity", "available_quantity", "qty_available", "in_stock", "estoque"],
    categoria: ["category", "category_name", "type", "product_type"],
    marca: ["brand", "manufacturer", "fabricante"],
    fornecedor: ["vendor", "supplier", "seller"],
    imagem_url: ["image_url", "image", "photo", "thumbnail", "imagem", "foto"],
    criado_em: ["created_at", "createdat", "date_created", "creation_date"],
    atualizado_em: ["updated_at", "updatedat", "date_modified", "modification_date"],

    // =========== CUSTOMERS ===========
    cliente_id: ["customer_id", "client_id", "user_id", "id"],
    email: ["customer_email", "email_address", "e_mail"],
    sobrenome: ["last_name", "lastname", "family_name", "surname"],
    nome_completo: ["full_name", "customer_name"],
    telefone: ["phone", "telephone", "mobile", "celular", "phone_number"],
    endereco: ["address", "street", "address_line", "logradouro"],
    cidade: ["city", "locality"],
    estado: ["state", "province", "region", "uf"],
    pais: ["country", "country_code"],
    cep: ["postal_code", "zip_code", "zipcode", "postcode"],
    total_pedidos: ["orders_count", "order_count", "num_orders"],
    valor_total_gasto: ["total_spent", "lifetime_value", "total_revenue"],

    // =========== ORDERS ===========
    numero_pedido: ["order_number", "number", "order_no", "numero"],
    data_pedido: ["order_date", "date", "purchase_date", "data_compra"],
    status_financeiro: ["financial_status", "payment_status"],
    status_entrega: ["fulfillment_status", "shipping_status", "delivery_status"],
    subtotal: ["sub_total", "items_total"],
    imposto_total: ["total_tax", "tax", "tax_amount", "impostos"],
    desconto_total: ["total_discount", "discount", "discount_amount", "desconto"],
    frete: ["shipping_cost", "shipping", "freight", "shipping_amount"],
    metodo_pagamento: ["payment_method", "payment_type", "forma_pagamento"],
    endereco_entrega: ["shipping_address"],
    endereco_cobranca: ["billing_address"],
    itens: ["line_items", "items", "order_items"],
    observacoes: ["notes", "comments", "remarks"],
    origem: ["source", "channel", "origem_pedido"],
};

// =============================================================================
// Thresholds
// =============================================================================

const HIGH_CONFIDENCE_THRESHOLD = 0.85;
const MEDIUM_CONFIDENCE_THRESHOLD = 0.70;

// =============================================================================
// Context-Aware Matching
// =============================================================================

// Schema-type based defaults for ambiguous columns
// When a bare column like "cnpj" appears, use schema context to disambiguate
const SCHEMA_CONTEXT_DEFAULTS: Record<SchemaType, Record<string, string>> = {
    dim_clientes: {
        cnpj: "cliente_cpf_cnpj",
        cpf: "cliente_cpf_cnpj",
        cpf_cnpj: "cliente_cpf_cnpj",
        documento: "cliente_cpf_cnpj",
        telefone: "telefone",
        nome: "nome",
        endereco: "endereco",
        cidade: "cidade",
        estado: "estado",
        uf: "estado",
        cep: "cep",
        email: "email",
    },
    invoices: {
        // Default to customer context in invoices (receiver = customer buying)
        cnpj: "cliente_cpf_cnpj",
        cpf: "cliente_cpf_cnpj",
        cpf_cnpj: "cliente_cpf_cnpj",
        documento: "cliente_cpf_cnpj",
        telefone: "cliente_telefone",
        nome: "cliente_nome",
        endereco: "cliente_rua",
        cidade: "cliente_cidade",
        estado: "cliente_uf",
        uf: "cliente_uf",
        cep: "cliente_cep",
        data: "data_transacao",
        valor: "valor_total",
        total: "valor_total",
    },
    fcx_vendas: {
        cnpj: "cliente_cpf_cnpj",
        cpf: "cliente_cpf_cnpj",
        cpf_cnpj: "cliente_cpf_cnpj",
        telefone: "cliente_telefone",
        nome: "cliente_nome",
        data: "data_transacao",
        valor: "valor_total",
    },
    dim_produtos: {
        nome: "nome",
        descricao: "descricao",
        preco: "preco",
        valor: "preco",
        quantidade: "quantidade_estoque",
        codigo: "sku",
    },
    fcx_orders: {
        cnpj: "cliente_cpf_cnpj",
        cpf: "cliente_cpf_cnpj",
        telefone: "telefone",
        nome: "cliente_nome",
        data: "data_pedido",
        valor: "valor_total",
        total: "valor_total",
    },
    dim_inventory: {
        quantidade: "quantity_on_hand",
        codigo: "sku",
        estoque: "quantity_on_hand",
    },
    fcx_categorias: {
        nome: "nome",
        categoria: "nome",
    },
};

// Columns that signal a specific context (customer vs supplier)
// If these appear alongside ambiguous columns, they provide context
type EntityContext = "customer" | "supplier" | "product" | "neutral";

const CONTEXT_SIGNAL_COLUMNS: Record<string, EntityContext> = {
    // Customer signals
    cliente: "customer",
    cliente_id: "customer",
    cliente_nome: "customer",
    nome_cliente: "customer",
    customer: "customer",
    customer_id: "customer",
    customer_name: "customer",
    comprador: "customer",
    buyer: "customer",
    receiver: "customer",
    receiverlegalname: "customer",
    receiverlegaldoc: "customer",

    // Supplier signals
    fornecedor: "supplier",
    fornecedor_id: "supplier",
    fornecedor_nome: "supplier",
    nome_fornecedor: "supplier",
    supplier: "supplier",
    supplier_id: "supplier",
    supplier_name: "supplier",
    vendor: "supplier",
    vendedor: "supplier",
    emitter: "supplier",
    emitterlegalname: "supplier",
    emitterlegaldoc: "supplier",

    // Product signals
    produto: "product",
    produto_id: "product",
    product: "product",
    product_id: "product",
    sku: "product",
    item: "product",
};

// Maps ambiguous columns to their context-specific canonical names
const CONTEXT_SPECIFIC_MAPPINGS: Record<string, Record<EntityContext, string>> = {
    cnpj: {
        customer: "cliente_cpf_cnpj",
        supplier: "fornecedor_cnpj",
        product: "cliente_cpf_cnpj", // Default to customer in product context
        neutral: "cliente_cpf_cnpj", // Default to customer
    },
    cpf: {
        customer: "cliente_cpf_cnpj",
        supplier: "fornecedor_cnpj",
        product: "cliente_cpf_cnpj",
        neutral: "cliente_cpf_cnpj",
    },
    cpf_cnpj: {
        customer: "cliente_cpf_cnpj",
        supplier: "fornecedor_cnpj",
        product: "cliente_cpf_cnpj",
        neutral: "cliente_cpf_cnpj",
    },
    documento: {
        customer: "cliente_cpf_cnpj",
        supplier: "fornecedor_cnpj",
        product: "cliente_cpf_cnpj",
        neutral: "cliente_cpf_cnpj",
    },
    telefone: {
        customer: "cliente_telefone",
        supplier: "fornecedor_telefone",
        product: "telefone",
        neutral: "telefone",
    },
    phone: {
        customer: "cliente_telefone",
        supplier: "fornecedor_telefone",
        product: "telefone",
        neutral: "telefone",
    },
    nome: {
        customer: "cliente_nome",
        supplier: "fornecedor_nome",
        product: "nome",
        neutral: "nome",
    },
    name: {
        customer: "cliente_nome",
        supplier: "fornecedor_nome",
        product: "nome",
        neutral: "nome",
    },
    cidade: {
        customer: "cliente_cidade",
        supplier: "fornecedor_cidade",
        product: "cidade",
        neutral: "cidade",
    },
    city: {
        customer: "cliente_cidade",
        supplier: "fornecedor_cidade",
        product: "cidade",
        neutral: "cidade",
    },
    estado: {
        customer: "cliente_uf",
        supplier: "fornecedor_uf",
        product: "estado",
        neutral: "estado",
    },
    uf: {
        customer: "cliente_uf",
        supplier: "fornecedor_uf",
        product: "estado",
        neutral: "estado",
    },
    state: {
        customer: "cliente_uf",
        supplier: "fornecedor_uf",
        product: "estado",
        neutral: "estado",
    },
    endereco: {
        customer: "cliente_rua",
        supplier: "fornecedor_cidade", // Suppliers usually just have city
        product: "endereco",
        neutral: "endereco",
    },
    cep: {
        customer: "cliente_cep",
        supplier: "fornecedor_cidade", // Map to city as proxy
        product: "cep",
        neutral: "cep",
    },
    data: {
        customer: "criado_em",
        supplier: "data_transacao",
        product: "criado_em",
        neutral: "data_transacao",
    },
    date: {
        customer: "criado_em",
        supplier: "data_transacao",
        product: "criado_em",
        neutral: "data_transacao",
    },
    valor: {
        customer: "valor_total_gasto",
        supplier: "valor_total",
        product: "preco",
        neutral: "valor_total",
    },
    value: {
        customer: "valor_total_gasto",
        supplier: "valor_total",
        product: "preco",
        neutral: "valor_total",
    },
    total: {
        customer: "valor_total_gasto",
        supplier: "valor_total",
        product: "preco",
        neutral: "valor_total",
    },
};

/**
 * Detects the dominant entity context from a set of columns.
 * Analyzes all columns to find signals indicating customer, supplier, or product context.
 */
function detectTableContext(columns: string[]): EntityContext {
    const contextCounts: Record<EntityContext, number> = {
        customer: 0,
        supplier: 0,
        product: 0,
        neutral: 0,
    };

    for (const col of columns) {
        const normalized = col.toLowerCase().trim();

        // Check exact matches
        const exactContext = CONTEXT_SIGNAL_COLUMNS[normalized];
        if (exactContext) {
            contextCounts[exactContext] += 2; // Strong signal
            continue;
        }

        // Check partial matches (column contains signal word)
        for (const [signal, context] of Object.entries(CONTEXT_SIGNAL_COLUMNS)) {
            if (normalized.includes(signal) || signal.includes(normalized)) {
                contextCounts[context] += 1; // Weak signal
            }
        }
    }

    // Find dominant context (excluding neutral)
    let maxContext: EntityContext = "neutral";
    let maxCount = 0;

    for (const [context, count] of Object.entries(contextCounts)) {
        if (context !== "neutral" && count > maxCount) {
            maxCount = count;
            maxContext = context as EntityContext;
        }
    }

    // Require at least some signal strength
    return maxCount >= 1 ? maxContext : "neutral";
}

/**
 * Resolves an ambiguous column using context from schema type and co-occurring columns.
 * Returns the context-aware canonical column name, or null if no context mapping exists.
 *
 * Priority:
 * 1. If we detected a non-neutral context from co-occurring columns, use context-specific mappings
 * 2. Otherwise, fall back to schema-specific defaults
 */
function resolveWithContext(
    sourceColumn: string,
    schemaType: SchemaType,
    tableContext: EntityContext
): string | null {
    const normalized = sourceColumn.toLowerCase().trim();

    // If we detected a clear context from co-occurring columns, prioritize that
    if (tableContext !== "neutral") {
        const contextMapping = CONTEXT_SPECIFIC_MAPPINGS[normalized];
        if (contextMapping) {
            return contextMapping[tableContext];
        }
    }

    // Fall back to schema-specific defaults
    const schemaDefaults = SCHEMA_CONTEXT_DEFAULTS[schemaType];
    if (schemaDefaults && schemaDefaults[normalized]) {
        return schemaDefaults[normalized];
    }

    // Last resort: check context-specific mappings with neutral context
    const contextMapping = CONTEXT_SPECIFIC_MAPPINGS[normalized];
    if (contextMapping) {
        return contextMapping[tableContext];
    }

    return null;
}

// =============================================================================
// Matching Logic
// =============================================================================

function normalizeColumnName(name: string): string {
    return name.toLowerCase().trim();
}

function buildAliasCache(schemaType: SchemaType): Map<string, string> {
    const cache = new Map<string, string>();
    const canonicalColumns = CANONICAL_SCHEMAS[schemaType] || [];

    // Add canonical columns themselves
    for (const canonical of canonicalColumns) {
        cache.set(canonical.toLowerCase(), canonical);
    }

    // Add aliases
    for (const [canonical, aliases] of Object.entries(COLUMN_ALIASES)) {
        if (canonicalColumns.includes(canonical)) {
            for (const alias of aliases) {
                cache.set(alias.toLowerCase(), canonical);
            }
        }
    }

    return cache;
}

function findBestMatch(
    sourceColumn: string,
    canonicalColumns: string[],
    aliasCache: Map<string, string>
): { canonical: string | null; confidence: number } {
    const normalized = normalizeColumnName(sourceColumn);

    // Stage 1: Exact match (via alias cache)
    const exactMatch = aliasCache.get(normalized);
    if (exactMatch) {
        return { canonical: exactMatch, confidence: 1.0 };
    }

    // Stage 2: Fuzzy match
    let bestMatch: string | null = null;
    let bestScore = 0;

    for (const canonical of canonicalColumns) {
        // Compare with canonical name
        const score = compareTwoStrings(normalized, canonical.toLowerCase());
        if (score > bestScore) {
            bestScore = score;
            bestMatch = canonical;
        }

        // Compare with aliases
        const aliases = COLUMN_ALIASES[canonical] || [];
        for (const alias of aliases) {
            const aliasScore = compareTwoStrings(normalized, alias.toLowerCase());
            if (aliasScore > bestScore) {
                bestScore = aliasScore;
                bestMatch = canonical;
            }
        }
    }

    return { canonical: bestMatch, confidence: bestScore };
}

function autoMatch(
    sourceColumns: string[],
    schemaType: SchemaType
): SchemaMatchResult {
    const canonicalColumns = CANONICAL_SCHEMAS[schemaType] || CANONICAL_SCHEMAS.invoices;
    const aliasCache = buildAliasCache(schemaType);

    // Detect table context from all columns for disambiguation
    const tableContext = detectTableContext(sourceColumns);

    const result: SchemaMatchResult = {
        matched: {},
        unmatched: [],
        confidence_scores: {},
        needs_review: [],
        details: [],
        detected_context: tableContext,
    };

    const usedCanonicals = new Set<string>();

    // First pass: collect all matches with scores
    const allMatches: Array<{
        source: string;
        canonical: string | null;
        confidence: number;
        context_resolved: boolean;
    }> = [];

    for (const sourceCol of sourceColumns) {
        // Try context-aware resolution first for ambiguous columns
        const contextResolved = resolveWithContext(sourceCol, schemaType, tableContext);

        if (contextResolved && canonicalColumns.includes(contextResolved)) {
            // Context-aware match found - high confidence
            allMatches.push({
                source: sourceCol,
                canonical: contextResolved,
                confidence: 0.95, // High but not 1.0 to indicate it was inferred
                context_resolved: true,
            });
        } else {
            // Fall back to standard matching
            const { canonical, confidence } = findBestMatch(sourceCol, canonicalColumns, aliasCache);
            allMatches.push({ source: sourceCol, canonical, confidence, context_resolved: false });
        }
    }

    // Sort by confidence (highest first) and process
    allMatches.sort((a, b) => b.confidence - a.confidence);

    for (const match of allMatches) {
        const { source, canonical, confidence } = match;

        // Skip if canonical already used
        if (canonical && usedCanonicals.has(canonical)) {
            // Find next best match that hasn't been used
            const alternateMatch = findAlternateMatch(source, canonicalColumns, usedCanonicals, aliasCache);
            if (alternateMatch) {
                processMatch(result, source, alternateMatch.canonical, alternateMatch.confidence, usedCanonicals);
            } else {
                result.unmatched.push(source);
                result.details.push({
                    source_column: source,
                    canonical_column: null,
                    confidence: 0,
                    auto_matched: false,
                });
            }
            continue;
        }

        processMatch(result, source, canonical, confidence, usedCanonicals);
    }

    return result;
}

function findAlternateMatch(
    sourceColumn: string,
    canonicalColumns: string[],
    usedCanonicals: Set<string>,
    aliasCache: Map<string, string>
): { canonical: string; confidence: number } | null {
    const normalized = normalizeColumnName(sourceColumn);
    let bestMatch: string | null = null;
    let bestScore = 0;

    for (const canonical of canonicalColumns) {
        if (usedCanonicals.has(canonical)) continue;

        const score = compareTwoStrings(normalized, canonical.toLowerCase());
        if (score > bestScore && score >= MEDIUM_CONFIDENCE_THRESHOLD) {
            bestScore = score;
            bestMatch = canonical;
        }
    }

    return bestMatch ? { canonical: bestMatch, confidence: bestScore } : null;
}

function processMatch(
    result: SchemaMatchResult,
    source: string,
    canonical: string | null,
    confidence: number,
    usedCanonicals: Set<string>
): void {
    if (canonical && confidence >= HIGH_CONFIDENCE_THRESHOLD) {
        // High confidence = auto-matched
        result.matched[source] = canonical;
        result.confidence_scores[source] = Math.round(confidence * 100) / 100;
        usedCanonicals.add(canonical);
        result.details.push({
            source_column: source,
            canonical_column: canonical,
            confidence: Math.round(confidence * 100) / 100,
            auto_matched: true,
        });
    } else if (canonical && confidence >= MEDIUM_CONFIDENCE_THRESHOLD) {
        // Medium confidence = needs review
        result.needs_review.push({
            source,
            candidates: [{ canonical, confidence: Math.round(confidence * 100) / 100 }],
        });
        result.confidence_scores[source] = Math.round(confidence * 100) / 100;
        result.details.push({
            source_column: source,
            canonical_column: canonical,
            confidence: Math.round(confidence * 100) / 100,
            auto_matched: false,
        });
    } else {
        // Low confidence = unmatched
        result.unmatched.push(source);
        result.details.push({
            source_column: source,
            canonical_column: null,
            confidence: Math.round(confidence * 100) / 100,
            auto_matched: false,
        });
    }
}

// =============================================================================
// HTTP Handler
// =============================================================================

serve(async (req) => {
    // Handle CORS preflight
    if (req.method === "OPTIONS") {
        return new Response(null, {
            status: 204,
            headers: {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        });
    }

    if (req.method !== "POST") {
        return new Response(JSON.stringify({ error: "Method not allowed" }), {
            status: 405,
            headers: { "Content-Type": "application/json" },
        });
    }

    try {
        const body = await req.json();
        const { source_columns, schema_type = "invoices" } = body as {
            source_columns: string[];
            schema_type?: string;
        };

        if (!source_columns || !Array.isArray(source_columns)) {
            return new Response(
                JSON.stringify({ error: "source_columns must be an array of strings" }),
                { status: 400, headers: { "Content-Type": "application/json" } }
            );
        }

        // Backwards compatibility: map legacy schema names to new names
        const LEGACY_SCHEMA_ALIASES: Record<string, SchemaType> = {
            vendas: "fcx_vendas",
            products: "dim_produtos",
            orders: "fcx_orders",
            customers: "dim_clientes",
            inventory: "dim_inventory",
            categories: "fcx_categorias",
        };

        const validSchemaTypes = Object.keys(CANONICAL_SCHEMAS);
        const inputType = schema_type.toLowerCase();
        const normalizedSchemaType: SchemaType =
            (LEGACY_SCHEMA_ALIASES[inputType] as SchemaType) ||
            (inputType as SchemaType) ||
            "invoices";

        if (!validSchemaTypes.includes(normalizedSchemaType)) {
            const legacyNames = Object.keys(LEGACY_SCHEMA_ALIASES);
            return new Response(
                JSON.stringify({
                    error: `Invalid schema_type. Must be one of: ${validSchemaTypes.join(", ")} (legacy aliases: ${legacyNames.join(", ")})`,
                }),
                { status: 400, headers: { "Content-Type": "application/json" } }
            );
        }

        const result = autoMatch(source_columns, normalizedSchemaType);

        return new Response(JSON.stringify(result), {
            status: 200,
            headers: {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
        });
    } catch (error) {
        console.error("Error processing request:", error);
        return new Response(
            JSON.stringify({ error: "Internal server error", details: String(error) }),
            { status: 500, headers: { "Content-Type": "application/json" } }
        );
    }
});
