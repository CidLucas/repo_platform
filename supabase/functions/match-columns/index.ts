// Schema Matcher Edge Function
// Port of services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py
// Uses string-similarity for fuzzy matching (equivalent to Python's difflib.SequenceMatcher)

import { compareTwoStrings } from "https://esm.sh/string-similarity@4.0.4";
import { corsHeaders, json } from "../_shared/cors.ts";

// =============================================================================
// Structured Logging Utility
// =============================================================================

function logInfo(message: string, details?: Record<string, unknown>) {
    console.log(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: "INFO",
        function: "match-columns",
        message,
        ...details,
    }));
}

function logError(message: string, error?: unknown, details?: Record<string, unknown>) {
    console.error(JSON.stringify({
        timestamp: new Date().toISOString(),
        level: "ERROR",
        function: "match-columns",
        message,
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
        ...details,
    }));
}

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

type SchemaType = "invoices" | "fato_transacoes" | "dim_clientes" | "dim_inventory";

// =============================================================================
// Canonical Schemas (Portuguese-aligned with analytics_v2 tables)
// =============================================================================

const CANONICAL_SCHEMAS: Record<SchemaType, string[]> = {
    // Main schema for BigQuery → analytics_v2 multi-table ETL.
    // Canonical names are the target DB column names (with table prefix for dim tables
    // so the ETL knows which dimension to write to).
    invoices: [
        // → fato_transacoes
        "documento",           // id_operatorinvoice / order_id
        "data_competencia_id", // emittedat_operatorinvoice (YYYYMMDD integer)
        "quantidade",          // quantitytraded_product
        "valor_unitario",      // unitprice_product
        "valor",               // totalprice_product
        "status",              // status_operatorinvoice

        // → dim_clientes (receiver / buyer fields)
        "cliente_cpf_cnpj",    // receiverlegaldoc
        "cliente_nome",        // receiverlegalname
        "cliente_telefone",    // receiverphone
        "cliente_cidade",      // receivercity  → dim_clientes.endereco_cidade
        "cliente_uf",          // receiverstateuf → dim_clientes.endereco_uf

        // → dim_fornecedores (emitter / supplier fields)
        "fornecedor_cnpj",     // emitterlegaldoc → dim_fornecedores.cnpj
        "fornecedor_nome",     // emitterlegalname
        "fornecedor_telefone", // emitterphone
        "fornecedor_cidade",   // emittercity → dim_fornecedores.endereco_cidade
        "fornecedor_uf",       // emitterstateuf → dim_fornecedores.endereco_uf

        // → dim_inventory (product fields)
        "produto_sku",         // id_product → dim_inventory.sku
        "produto_nome",        // description_product → dim_inventory.nome
    ],

    // analytics_v2.fato_transacoes — actual writeable columns
    fato_transacoes: [
        "documento",
        "data_competencia_id",
        "quantidade",
        "valor_unitario",
        "valor",
        "status",
    ],

    // analytics_v2.dim_clientes — only fields written at ingestion time
    dim_clientes: [
        "cpf_cnpj",
        "nome",
        "telefone",
        "endereco_cidade",
        "endereco_uf",
    ],

    // analytics_v2.dim_inventory — only fields written at ingestion time
    dim_inventory: [
        "sku",
        "nome",
    ],
};

// =============================================================================
// Column Aliases (BigQuery source column names → canonical target names)
// =============================================================================

const COLUMN_ALIASES: Record<string, string[]> = {
    // fato_transacoes
    documento: [
        "id_operatorinvoice", "id_invoice", "invoice_id", "order_id", "orderid",
        "pedido_id", "id_pedido", "numero_pedido", "order_number",
        // Conta Azul
        "number", "numero_nota", "chave_nfe", "document_number", "numero_nf",
    ],
    data_competencia_id: [
        "emittedat_operatorinvoice", "createdat_operatorinvoice", "data_emissao",
        "emission_date", "order_date", "data_pedido", "data_transacao",
        "transaction_date", "date", "created_at", "purchase_date",
        // Conta Azul
        "issue_date", "competencia", "dt_emissao",
    ],
    quantidade: ["quantitytraded_product", "quantity", "qty", "qtd", "quantitytraded"],
    valor_unitario: ["unitprice_product", "unit_price", "preco_unitario", "unitprice"],
    valor: [
        "totalprice_product", "total_price", "grand_total", "valor_total",
        "price", "preco", "total",
        // Conta Azul
        "total_value", "value", "vl_total", "valor_liquido",
    ],
    status: ["status_operatorinvoice", "order_status", "status_order"],

    // dim_clientes (receiver / buyer fields)
    cliente_cpf_cnpj: [
        "receiverlegaldoc", "receiver_cnpj", "customer_doc",
        "cpf_cnpj", "cpf", "cnpj_cliente",
        // Conta Azul
        "customer_cnpj", "cnpj_destinatario", "destinatario_cnpj", "recipient_cnpj",
    ],
    cliente_nome: [
        "receiverlegalname", "nome_receiver", "customer_name",
        "nome_cliente", "receiver_name",
        // Conta Azul
        "customer_name",
    ],
    cliente_telefone: [
        "receiverphone", "receiver_phone", "customer_phone",
        "telefone_cliente", "receiverphone",
    ],
    cliente_cidade: [
        "receivercity", "receiver_cidade", "customer_city",
        "cidade_cliente", "receivercity",
    ],
    cliente_uf: [
        "receiverstateuf", "receiver_uf", "customer_state",
        "uf_cliente", "estado_cliente",
    ],

    // dim_fornecedores (emitter / supplier fields)
    fornecedor_cnpj: [
        "emitterlegaldoc", "emitter_cnpj", "supplier_cnpj",
        "cnpj_fornecedor", "emitter_doc",
        // Conta Azul
        "cnpj_emitente", "issuer_cnpj", "emitente_cnpj",
    ],
    fornecedor_nome: [
        "emitterlegalname", "nome_emitter", "supplier_name",
        "nome_fornecedor", "emittername",
        // Conta Azul
        "nome_emitente", "issuer_name", "razao_social_emitente",
    ],
    fornecedor_telefone: [
        "emitterphone", "emitter_phone", "supplier_phone",
        "telefone_fornecedor",
    ],
    fornecedor_cidade: [
        "emittercity", "emitter_cidade", "supplier_city",
        "cidade_fornecedor",
    ],
    fornecedor_uf: [
        "emitterstateuf", "emitter_uf", "supplier_state",
        "uf_fornecedor", "estado_fornecedor",
    ],

    // dim_inventory (product fields)
    produto_sku: [
        "id_product", "product_id", "external_product_id",
        "sku", "codigo_produto", "item_sku", "product_sku",
    ],
    produto_nome: [
        "description_product", "descricao_produto", "product_description",
        "product_name", "nome_produto", "item_name",
    ],

    // dim_clientes standalone schema
    cpf_cnpj: ["receiverlegaldoc", "customer_doc", "cpf", "cnpj", "documento_cliente"],
    nome: ["name", "full_name", "customer_name", "product_name", "supplier_name"],
    telefone: ["phone", "telephone", "mobile", "celular", "phone_number"],
    endereco_cidade: ["city", "cidade", "municipio", "receivercity", "emittercity"],
    endereco_uf: ["state", "uf", "estado", "receiverstateuf", "emitterstateuf"],
    total_pedidos: ["orders_count", "order_count", "num_orders", "total_orders"],
    receita_total: ["total_revenue", "total_spent", "lifetime_value", "revenue"],
    ticket_medio: ["average_order_value", "avg_order", "ticket"],
    quantidade_total: ["total_quantity", "total_qty"],
    frequencia_mensal: ["monthly_frequency", "orders_per_month"],
    dias_recencia: ["recency_days", "days_since_last_order"],
    data_primeira_compra: ["first_purchase_date", "first_order_date"],
    data_ultima_compra: ["last_purchase_date", "last_order_date"],
    atualizado_em: ["updated_at", "updatedat", "date_modified"],

    // dim_inventory standalone schema
    sku: ["item_sku", "product_sku", "codigo", "code", "id_product", "product_id"],
    quantidade_total_vendida: ["total_quantity_sold", "qty_sold", "total_sold"],
    preco_medio: ["average_price", "avg_price", "mean_price"],
    data_ultima_venda: ["last_sale_date", "last_sold_date"],
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
        cnpj: "cpf_cnpj",
        cpf: "cpf_cnpj",
        cpf_cnpj: "cpf_cnpj",
        telefone: "telefone",
        nome: "nome",
        cidade: "endereco_cidade",
        estado: "endereco_uf",
        uf: "endereco_uf",
    },
    invoices: {
        data: "data_competencia_id",
        valor: "valor",
        total: "valor",
        preco: "valor_unitario",
        qtd: "quantidade",
        pedido: "documento",
        id: "documento",
    },
    dim_inventory: {
        quantidade: "quantidade_total_vendida",
        codigo: "sku",
        estoque: "quantidade_total_vendida",
        nome: "nome",
    },
    fato_transacoes: {
        valor: "valor",
        total: "valor",
        quantidade: "quantidade",
        data: "data_competencia_id",
        status: "status",
        documento: "documento",
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
    // Conta Azul supplier signals
    cnpj_emitente: "supplier",
    issuer_cnpj: "supplier",
    emitente_cnpj: "supplier",
    // Conta Azul customer signals
    cnpj_destinatario: "customer",
    destinatario_cnpj: "customer",
    destinatario: "customer",

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
        customer: "cliente_cidade",
        supplier: "fornecedor_cidade",
        product: "nome",
        neutral: "fornecedor_cidade",
    },
    cep: {
        customer: "cliente_uf",
        supplier: "fornecedor_uf",
        product: "sku",
        neutral: "fornecedor_uf",
    },
    data: {
        customer: "data_ultima_compra",
        supplier: "data_competencia_id",
        product: "data_ultima_venda",
        neutral: "data_competencia_id",
    },
    date: {
        customer: "data_ultima_compra",
        supplier: "data_competencia_id",
        product: "data_ultima_venda",
        neutral: "data_competencia_id",
    },
    valor: {
        customer: "receita_total",
        supplier: "valor",
        product: "preco_medio",
        neutral: "valor",
    },
    value: {
        customer: "receita_total",
        supplier: "valor",
        product: "preco_medio",
        neutral: "valor",
    },
    total: {
        customer: "receita_total",
        supplier: "valor",
        product: "preco_medio",
        neutral: "valor",
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
        const normalized = normalizeColumnName(sourceCol);

        // Exact alias/canonical match takes absolute priority — prevents context resolution
        // from hijacking columns that already have a perfect match (e.g. "documento" → "documento",
        // not "cliente_cpf_cnpj" via CONTEXT_SPECIFIC_MAPPINGS).
        const exactMatch = aliasCache.get(normalized);
        if (exactMatch) {
            allMatches.push({
                source: sourceCol,
                canonical: exactMatch,
                confidence: 1.0,
                context_resolved: false,
            });
            continue;
        }

        // Try context-aware resolution for genuinely ambiguous columns
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
            // Fall back to fuzzy matching
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

Deno.serve(async (req) => {
    const requestId = crypto.randomUUID();
    const startTime = Date.now();

    logInfo("Incoming request", {
        requestId,
        method: req.method,
        url: req.url,
    });

    // Handle CORS preflight
    if (req.method === "OPTIONS") {
        return new Response(null, {
            status: 204,
            headers: corsHeaders,
        });
    }

    if (req.method !== "POST") {
        logError("Method not allowed", undefined, { requestId, method: req.method });
        return json({ error: "Method not allowed" }, 405);
    }

    try {
        const body = await req.json();
        const { source_columns, schema_type = "invoices", client_id } = body as {
            source_columns: string[];
            schema_type?: string;
            client_id?: string;
        };

        logInfo("Request body parsed", {
            requestId,
            columnCount: source_columns?.length,
            schemaType: schema_type,
            clientId: client_id,
        });

        if (!source_columns || !Array.isArray(source_columns)) {
            logError("Invalid request: source_columns missing or not an array", undefined, {
                requestId,
                receivedType: typeof source_columns,
            });
            return json({
                    error: "source_columns must be an array of strings",
                    error_code: "INVALID_INPUT",
                }, 400);
        }

        if (source_columns.length === 0) {
            logError("Invalid request: source_columns array is empty", undefined, { requestId });
            return json({
                    error: "source_columns array cannot be empty",
                    error_code: "EMPTY_INPUT",
                }, 400);
        }

        // Backwards compatibility: map legacy schema names to new names
        const LEGACY_SCHEMA_ALIASES: Record<string, SchemaType> = {
            vendas: "fato_transacoes",
            products: "dim_inventory",
            orders: "fato_transacoes",
            customers: "dim_clientes",
            inventory: "dim_inventory",
            fcx_vendas: "fato_transacoes",
            dim_produtos: "dim_inventory",
            fcx_orders: "fato_transacoes",
        };

        const validSchemaTypes = Object.keys(CANONICAL_SCHEMAS);
        const inputType = schema_type.toLowerCase();
        const normalizedSchemaType: SchemaType =
            (LEGACY_SCHEMA_ALIASES[inputType] as SchemaType) ||
            (inputType as SchemaType) ||
            "invoices";

        if (!validSchemaTypes.includes(normalizedSchemaType)) {
            const legacyNames = Object.keys(LEGACY_SCHEMA_ALIASES);
            logError("Invalid schema_type", undefined, {
                requestId,
                providedSchemaType: schema_type,
                normalizedSchemaType,
                validTypes: validSchemaTypes,
            });
            return json({
                    error: `Invalid schema_type. Must be one of: ${validSchemaTypes.join(", ")} (legacy aliases: ${legacyNames.join(", ")})`,
                    error_code: "INVALID_SCHEMA_TYPE",
                }, 400);
        }

        logInfo("Starting column matching", {
            requestId,
            sourceColumns: source_columns,
            schemaType: normalizedSchemaType,
            canonicalColumnCount: CANONICAL_SCHEMAS[normalizedSchemaType].length,
        });

        const matchStartTime = Date.now();
        const result = autoMatch(source_columns, normalizedSchemaType);
        const matchDuration = Date.now() - matchStartTime;

        // Calculate confidence distribution
        const confidenceDistribution = {
            high: result.details.filter(d => d.auto_matched).length,
            medium: result.needs_review.length,
            low: result.unmatched.length,
        };

        logInfo("Column matching completed", {
            requestId,
            matchDuration,
            matchedCount: Object.keys(result.matched).length,
            unmatchedCount: result.unmatched.length,
            needsReviewCount: result.needs_review.length,
            confidenceDistribution,
            detectedContext: result.detected_context,
        });

        const totalDuration = Date.now() - startTime;

        logInfo("Request completed successfully", {
            requestId,
            totalDuration,
            statusCode: 200,
        });

        return json(result, 200, {
                "X-Request-Id": requestId,
                "X-Duration-Ms": totalDuration.toString(),
            });
    } catch (error) {
        const totalDuration = Date.now() - startTime;

        logError("Unhandled exception in request handler", error, {
            requestId,
            totalDuration,
        });

        return json({
                error: "Internal server error",
                error_code: "INTERNAL_ERROR",
                details: error instanceof Error ? error.message : String(error),
                request_id: requestId,
            }, 500, { "X-Request-Id": requestId });
    }
});
