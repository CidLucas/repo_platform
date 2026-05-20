// Schema Matcher Edge Function
// Loads canonical column definitions from public.canonical_columns (Supabase).
// Fuzzy matching is the primary path; unmatched columns are flagged for the
// future LLM skill step (skill:match-columns-llm) during onboarding.

import { compareTwoStrings } from "https://esm.sh/string-similarity@4.0.4";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";
import { corsHeaders, json } from "../_shared/cors.ts";

// =============================================================================
// Supabase client (service role — reads public.canonical_columns)
// =============================================================================

const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

// =============================================================================
// Structured Logging
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

interface CanonicalColumnDef {
    column_name: string;
    data_type: string;
    is_required: boolean;
    description: string;
    examples: string[];
}

interface MatchCandidate {
    canonical: string;
    confidence: number;
}

interface SchemaMatchResult {
    matched: Record<string, string>;
    unmatched: string[];
    confidence_scores: Record<string, number>;
    needs_review: Array<{ source: string; candidates: MatchCandidate[] }>;
    detected_context?: string;
}

type SchemaType = "invoices" | "fato_transacoes" | "fato_compras" | "dim_clientes" | "dim_inventory";

// DB table_name that maps to each SchemaType.
// "invoices" is a composite ETL routing schema — uses hardcoded columns below.
const SCHEMA_TO_TABLE: Partial<Record<SchemaType, string>> = {
    fato_transacoes: "fato_transacoes",
    fato_compras:    "fato_compras",
    dim_clientes:    "dim_clientes",
    dim_inventory:   "dim_inventory",
};

// =============================================================================
// Module-level canonical column cache
// Lives as long as the isolate (warm starts reuse it; cold starts refetch).
// No TTL — canonical_columns only changes on schema migrations.
// =============================================================================

const _canonicalCache = new Map<string, CanonicalColumnDef[]>();

async function loadMappableColumns(tableName: string): Promise<CanonicalColumnDef[]> {
    if (_canonicalCache.has(tableName)) return _canonicalCache.get(tableName)!;

    const { data, error } = await supabase
        .from("canonical_columns")
        .select("column_name,data_type,is_required,description,examples")
        .eq("table_name", tableName)
        .eq("category", "mappable")
        .order("column_name");

    if (error || !data?.length) {
        logError(`Failed to load canonical_columns for ${tableName}`, error);
        return [];
    }

    _canonicalCache.set(tableName, data as CanonicalColumnDef[]);
    return data as CanonicalColumnDef[];
}

// =============================================================================
// Fallback: "invoices" composite schema (multi-table ETL routing).
// Prefixed names (cliente_*, fornecedor_*, produto_*) tell the ETL which
// dimension table to write each field to. Not stored in canonical_columns
// because the prefixes are ETL artefacts, not real DB columns.
// =============================================================================

const INVOICES_COLUMNS: CanonicalColumnDef[] = [
    // → fato_transacoes
    { column_name: "documento",           data_type: "text",    is_required: true,  description: "Unique transaction/invoice identifier",                    examples: ["NF-001", "ORD-12345"] },
    { column_name: "data_competencia_id", data_type: "bigint",  is_required: true,  description: "Accounting date as YYYYMMDD integer",                      examples: ["20240115"] },
    { column_name: "quantidade",          data_type: "numeric", is_required: false, description: "Quantity of items",                                         examples: ["1", "5"] },
    { column_name: "valor_unitario",      data_type: "numeric", is_required: false, description: "Unit price per item",                                       examples: ["49.90"] },
    { column_name: "valor",               data_type: "numeric", is_required: true,  description: "Total transaction value",                                   examples: ["249.50"] },
    { column_name: "status",              data_type: "text",    is_required: false, description: "Transaction status (paid/pending/cancelled)",               examples: ["pago", "paid"] },
    { column_name: "tipo_lancamento",     data_type: "text",    is_required: false, description: "Entry type (MAT/MDO/ADITIVO for construction sheets)",      examples: ["MAT", "MDO"] },
    { column_name: "categoria",           data_type: "text",    is_required: false, description: "Business category",                                         examples: ["Eletrônicos"] },
    { column_name: "subcategoria",        data_type: "text",    is_required: false, description: "Sub-category",                                              examples: ["Smartphones"] },
    // → dim_clientes
    { column_name: "cliente_cpf_cnpj",   data_type: "text",    is_required: false, description: "Customer tax ID (CPF/CNPJ)",                               examples: ["123.456.789-09"] },
    { column_name: "cliente_nome",        data_type: "text",    is_required: false, description: "Customer name",                                             examples: ["João Silva"] },
    { column_name: "cliente_telefone",    data_type: "text",    is_required: false, description: "Customer phone",                                            examples: ["(11) 99999-9999"] },
    { column_name: "cliente_cidade",      data_type: "text",    is_required: false, description: "Customer city",                                             examples: ["São Paulo"] },
    { column_name: "cliente_uf",          data_type: "text",    is_required: false, description: "Customer state (2-letter UF)",                             examples: ["SP"] },
    // → dim_fornecedores
    { column_name: "fornecedor_cnpj",     data_type: "text",    is_required: false, description: "Supplier CNPJ",                                            examples: ["12.345.678/0001-99"] },
    { column_name: "fornecedor_nome",     data_type: "text",    is_required: false, description: "Supplier name",                                             examples: ["Distribuidora ABC"] },
    { column_name: "fornecedor_telefone", data_type: "text",    is_required: false, description: "Supplier phone",                                            examples: ["(11) 3333-4444"] },
    { column_name: "fornecedor_cidade",   data_type: "text",    is_required: false, description: "Supplier city",                                             examples: ["Campinas"] },
    { column_name: "fornecedor_uf",       data_type: "text",    is_required: false, description: "Supplier state (2-letter UF)",                             examples: ["SP"] },
    // → dim_inventory
    { column_name: "produto_sku",         data_type: "text",    is_required: false, description: "Product SKU",                                              examples: ["SKU-001"] },
    { column_name: "produto_nome",        data_type: "text",    is_required: false, description: "Product name",                                              examples: ["Camiseta Azul M"] },
];

async function getCanonicalDefs(schemaType: SchemaType): Promise<CanonicalColumnDef[]> {
    if (schemaType === "invoices") return INVOICES_COLUMNS;
    return loadMappableColumns(SCHEMA_TO_TABLE[schemaType]!);
}

// =============================================================================
// Column Aliases (source column names → canonical target names)
// =============================================================================

const COLUMN_ALIASES: Record<string, string[]> = {
    // fato_transacoes
    documento: [
        "id_operatorinvoice", "id_invoice", "invoice_id", "order_id", "orderid",
        "pedido_id", "id_pedido", "numero_pedido", "order_number",
        "number", "numero_nota", "chave_nfe", "document_number", "numero_nf",
        "chave_acesso", "numero",
        "número nf", "numero nf", "num nf", "nr nf", "nf", "nota fiscal",
        "número nota", "numero nota", "nf numero", "nf número",
    ],
    data_competencia_id: [
        "emittedat_operatorinvoice", "createdat_operatorinvoice", "data_emissao",
        "emission_date", "order_date", "data_pedido", "data_transacao",
        "transaction_date", "date", "created_at", "purchase_date",
        "issue_date", "competencia", "dt_emissao", "data_competencia",
        "data custo", "data_custo", "data do custo", "dt custo", "dt_custo",
        "data lancamento", "data_lancamento", "data registro", "data_registro",
    ],
    quantidade: ["quantitytraded_product", "quantity", "qty", "qtd", "quantitytraded"],
    valor_unitario: ["unitprice_product", "unit_price", "preco_unitario", "unitprice"],
    valor: [
        "totalprice_product", "total_price", "grand_total", "valor_total",
        "price", "preco", "total",
        "total_value", "value", "vl_total", "valor_liquido",
        "valor_total_nfse", "valor_servico",
    ],
    status: ["status_operatorinvoice", "order_status", "status_order"],
    // dim_clientes
    cliente_cpf_cnpj: [
        "receiverlegaldoc", "receiver_cnpj", "customer_doc",
        "cpf_cnpj", "cpf", "cnpj_cliente",
        "customer_cnpj", "cnpj_destinatario", "destinatario_cnpj", "recipient_cnpj",
        "documento_tomador", "documento_cliente",
    ],
    cliente_nome: [
        "receiverlegalname", "nome_receiver", "customer_name",
        "nome_cliente", "receiver_name",
        "nome_destinatario", "nome_tomador",
    ],
    cliente_telefone: ["receiverphone", "receiver_phone", "customer_phone", "telefone_cliente"],
    cliente_cidade:   ["receivercity", "receiver_cidade", "customer_city", "cidade_cliente"],
    cliente_uf:       ["receiverstateuf", "receiver_uf", "customer_state", "uf_cliente", "estado_cliente"],
    // dim_fornecedores
    fornecedor_cnpj: [
        "emitterlegaldoc", "emitter_cnpj", "supplier_cnpj", "cnpj_fornecedor",
        "cnpj_emitente", "issuer_cnpj", "emitente_cnpj",
    ],
    fornecedor_nome: [
        "emitterlegalname", "nome_emitter", "supplier_name", "nome_fornecedor",
        "nome_emitente", "issuer_name", "razao_social_emitente", "fornecedor",
    ],
    fornecedor_telefone: ["emitterphone", "emitter_phone", "supplier_phone", "telefone_fornecedor"],
    fornecedor_cidade:   ["emittercity", "emitter_cidade", "supplier_city", "cidade_fornecedor"],
    fornecedor_uf:       ["emitterstateuf", "emitter_uf", "supplier_state", "uf_fornecedor", "estado_fornecedor"],
    // dim_inventory
    produto_sku:  ["id_product", "product_id", "external_product_id", "sku", "codigo_produto", "item_sku", "product_sku"],
    produto_nome: ["description_product", "descricao_produto", "product_description", "product_name", "nome_produto", "item_name"],
    // dim_clientes standalone
    cpf_cnpj:       ["receiverlegaldoc", "customer_doc", "cpf", "cnpj", "documento_cliente"],
    nome:           ["name", "full_name", "customer_name", "product_name", "supplier_name"],
    telefone:       ["phone", "telephone", "mobile", "celular", "phone_number"],
    endereco_cidade:["city", "cidade", "municipio", "receivercity", "emittercity"],
    endereco_uf:    ["state", "uf", "estado", "receiverstateuf", "emitterstateuf"],
    // dim_inventory standalone
    sku: ["item_sku", "product_sku", "codigo", "code", "id_product", "product_id"],
    // construction / cost-center
    tipo_lancamento: ["mat ou mdo", "mat_ou_mdo", "tipo", "type", "lancamento_tipo", "tipo_custo", "modalidade", "mao de obra", "mão de obra", "mat/mdo"],
    categoria:       ["centro de custo - familia", "centro_custo_familia", "familia", "cost_center", "cost center", "centro_custo", "family", "grupo", "centro de custo"],
    subcategoria:    ["centro de custo - sub familia", "centro_custo_sub_familia", "sub_familia", "sub-familia", "subfamilia", "sub_categoria", "subgrupo", "descricao", "sub familia"],
};

// =============================================================================
// Thresholds
// =============================================================================

const HIGH_CONFIDENCE_THRESHOLD   = 0.85;
const MEDIUM_CONFIDENCE_THRESHOLD = 0.70;

// =============================================================================
// Context-Aware Matching
// =============================================================================

type EntityContext = "customer" | "supplier" | "product" | "neutral";

const CONTEXT_SIGNAL_COLUMNS: Record<string, EntityContext> = {
    cliente: "customer", client_id: "customer", cliente_nome: "customer",
    nome_cliente: "customer", customer: "customer", customer_id: "customer",
    customer_name: "customer", comprador: "customer", buyer: "customer",
    receiver: "customer", receiverlegalname: "customer", receiverlegaldoc: "customer",
    cnpj_destinatario: "customer", destinatario_cnpj: "customer",
    destinatario: "customer", nome_destinatario: "customer",
    nome_tomador: "customer", documento_tomador: "customer", documento_cliente: "customer",
    fornecedor: "supplier", fornecedor_id: "supplier", fornecedor_nome: "supplier",
    nome_fornecedor: "supplier", supplier: "supplier", supplier_id: "supplier",
    supplier_name: "supplier", vendor: "supplier", vendedor: "supplier",
    emitter: "supplier", emitterlegalname: "supplier", emitterlegaldoc: "supplier",
    cnpj_emitente: "supplier", issuer_cnpj: "supplier", emitente_cnpj: "supplier",
    nome_emitente: "supplier", nome_prestador: "supplier", cnpj_prestador: "supplier",
    produto: "product", produto_id: "product", product: "product",
    product_id: "product", sku: "product", item: "product",
};

const SCHEMA_CONTEXT_DEFAULTS: Record<SchemaType, Record<string, string>> = {
    dim_clientes:    { cnpj: "cpf_cnpj", cpf: "cpf_cnpj", cpf_cnpj: "cpf_cnpj", telefone: "telefone", nome: "nome", cidade: "endereco_cidade", estado: "endereco_uf", uf: "endereco_uf" },
    invoices:        { data: "data_competencia_id", valor: "valor", total: "valor", preco: "valor_unitario", qtd: "quantidade", pedido: "documento", id: "documento", fornecedor: "fornecedor_nome", cliente: "cliente_nome" },
    dim_inventory:   { codigo: "sku", estoque: "sku", nome: "nome" },
    fato_transacoes: { valor: "valor", total: "valor", quantidade: "quantidade", data: "data_competencia_id", status: "status", documento: "documento" },
    fato_compras:    { valor: "valor", total: "valor", quantidade: "quantidade", data: "data_competencia_id", status: "status", documento: "documento" },
};

const CONTEXT_SPECIFIC_MAPPINGS: Record<string, Record<EntityContext, string>> = {
    cnpj:     { customer: "cliente_cpf_cnpj", supplier: "fornecedor_cnpj", product: "cliente_cpf_cnpj", neutral: "cliente_cpf_cnpj" },
    cpf:      { customer: "cliente_cpf_cnpj", supplier: "fornecedor_cnpj", product: "cliente_cpf_cnpj", neutral: "cliente_cpf_cnpj" },
    cpf_cnpj: { customer: "cliente_cpf_cnpj", supplier: "fornecedor_cnpj", product: "cliente_cpf_cnpj", neutral: "cliente_cpf_cnpj" },
    telefone: { customer: "cliente_telefone",  supplier: "fornecedor_telefone", product: "telefone",       neutral: "telefone" },
    phone:    { customer: "cliente_telefone",  supplier: "fornecedor_telefone", product: "telefone",       neutral: "telefone" },
    nome:     { customer: "cliente_nome",      supplier: "fornecedor_nome",     product: "nome",           neutral: "nome" },
    name:     { customer: "cliente_nome",      supplier: "fornecedor_nome",     product: "nome",           neutral: "nome" },
    cidade:   { customer: "cliente_cidade",    supplier: "fornecedor_cidade",   product: "cidade",         neutral: "cidade" },
    city:     { customer: "cliente_cidade",    supplier: "fornecedor_cidade",   product: "cidade",         neutral: "cidade" },
    estado:   { customer: "cliente_uf",        supplier: "fornecedor_uf",       product: "estado",         neutral: "estado" },
    uf:       { customer: "cliente_uf",        supplier: "fornecedor_uf",       product: "estado",         neutral: "estado" },
    state:    { customer: "cliente_uf",        supplier: "fornecedor_uf",       product: "estado",         neutral: "estado" },
    valor:    { customer: "valor",             supplier: "valor",               product: "valor",          neutral: "valor" },
    value:    { customer: "valor",             supplier: "valor",               product: "valor",          neutral: "valor" },
    total:    { customer: "valor",             supplier: "valor",               product: "valor",          neutral: "valor" },
    data:     { customer: "data_competencia_id", supplier: "data_competencia_id", product: "data_competencia_id", neutral: "data_competencia_id" },
    date:     { customer: "data_competencia_id", supplier: "data_competencia_id", product: "data_competencia_id", neutral: "data_competencia_id" },
};

function detectTableContext(columns: string[]): EntityContext {
    const counts: Record<EntityContext, number> = { customer: 0, supplier: 0, product: 0, neutral: 0 };
    for (const col of columns) {
        const n = col.toLowerCase().trim();
        const exact = CONTEXT_SIGNAL_COLUMNS[n];
        if (exact) { counts[exact] += 2; continue; }
        for (const [signal, ctx] of Object.entries(CONTEXT_SIGNAL_COLUMNS)) {
            if (n.includes(signal) || signal.includes(n)) counts[ctx] += 1;
        }
    }
    let max: EntityContext = "neutral";
    let maxN = 0;
    for (const [ctx, n] of Object.entries(counts)) {
        if (ctx !== "neutral" && n > maxN) { maxN = n; max = ctx as EntityContext; }
    }
    return maxN >= 1 ? max : "neutral";
}

function resolveWithContext(source: string, schemaType: SchemaType, tableCtx: EntityContext): string | null {
    const n = source.toLowerCase().trim();
    const ctxMapping = CONTEXT_SPECIFIC_MAPPINGS[n];
    if (ctxMapping && tableCtx !== "neutral") return ctxMapping[tableCtx];
    const defaults = SCHEMA_CONTEXT_DEFAULTS[schemaType];
    if (defaults?.[n]) return defaults[n];
    return ctxMapping ? ctxMapping[tableCtx] : null;
}

// =============================================================================
// Matching Logic
// =============================================================================

function buildAliasCache(canonicalDefs: CanonicalColumnDef[]): Map<string, string> {
    const cache = new Map<string, string>();
    for (const def of canonicalDefs) {
        cache.set(def.column_name.toLowerCase(), def.column_name);
        for (const alias of (COLUMN_ALIASES[def.column_name] ?? [])) {
            cache.set(alias.toLowerCase(), def.column_name);
        }
    }
    return cache;
}

function findBestMatch(
    source: string,
    canonicalDefs: CanonicalColumnDef[],
): { canonical: string | null; confidence: number } {
    const n = source.toLowerCase().trim();
    let best: string | null = null;
    let bestScore = 0;
    for (const def of canonicalDefs) {
        const score = compareTwoStrings(n, def.column_name.toLowerCase());
        if (score > bestScore) { bestScore = score; best = def.column_name; }
        for (const alias of (COLUMN_ALIASES[def.column_name] ?? [])) {
            const s = compareTwoStrings(n, alias.toLowerCase());
            if (s > bestScore) { bestScore = s; best = def.column_name; }
        }
    }
    return { canonical: best, confidence: bestScore };
}

function processMatch(
    result: SchemaMatchResult,
    source: string,
    canonical: string | null,
    confidence: number,
    used: Set<string>,
): void {
    if (canonical && confidence >= HIGH_CONFIDENCE_THRESHOLD) {
        result.matched[source] = canonical;
        result.confidence_scores[source] = Math.round(confidence * 100) / 100;
        used.add(canonical);
    } else if (canonical && confidence >= MEDIUM_CONFIDENCE_THRESHOLD) {
        result.needs_review.push({ source, candidates: [{ canonical, confidence: Math.round(confidence * 100) / 100 }] });
        result.confidence_scores[source] = Math.round(confidence * 100) / 100;
    } else {
        result.unmatched.push(source);
    }
}

function autoMatch(sourceColumns: string[], schemaType: SchemaType, canonicalDefs: CanonicalColumnDef[]): SchemaMatchResult {
    const aliasCache = buildAliasCache(canonicalDefs);
    const tableCtx   = detectTableContext(sourceColumns);
    const result: SchemaMatchResult = { matched: {}, unmatched: [], confidence_scores: {}, needs_review: [], detected_context: tableCtx };
    const used = new Set<string>();

    const allMatches = sourceColumns.map((src) => {
        const n     = src.toLowerCase().trim();
        const exact = aliasCache.get(n);
        if (exact) return { source: src, canonical: exact, confidence: 1.0 };

        const ctxResolved = resolveWithContext(src, schemaType, tableCtx);
        if (ctxResolved && canonicalDefs.some(d => d.column_name === ctxResolved)) {
            return { source: src, canonical: ctxResolved, confidence: 0.95 };
        }

        const { canonical, confidence } = findBestMatch(src, canonicalDefs);
        return { source: src, canonical, confidence };
    });

    allMatches.sort((a, b) => b.confidence - a.confidence);

    for (const m of allMatches) {
        if (m.canonical && used.has(m.canonical)) {
            let fallback: string | null = null; let fallbackScore = 0;
            for (const def of canonicalDefs) {
                if (used.has(def.column_name)) continue;
                const s = compareTwoStrings(m.source.toLowerCase().trim(), def.column_name.toLowerCase());
                if (s > fallbackScore && s >= MEDIUM_CONFIDENCE_THRESHOLD) { fallbackScore = s; fallback = def.column_name; }
            }
            processMatch(result, m.source, fallback, fallbackScore, used);
        } else {
            processMatch(result, m.source, m.canonical, m.confidence, used);
        }
    }

    return result;
}

// =============================================================================
// LLM Fallback (future)
// When unmatched.length > 0 during onboarding, escalate to a Python skill:
//   skill: "match-columns-llm"
//   payload: { unmatched_columns, column_samples (df.head5), schema_type,
//              canonical_columns (from ContextService), business_context }
// The skill uses build_prompt("skill:match-columns") and returns suggestions
// that are merged back here as needs_review entries.
// =============================================================================

// =============================================================================
// HTTP Handler
// =============================================================================

Deno.serve(async (req) => {
    const requestId = crypto.randomUUID();
    const startTime = Date.now();

    logInfo("Incoming request", { requestId, method: req.method, url: req.url });

    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders });
    if (req.method !== "POST") return json({ error: "Method not allowed" }, 405);

    try {
        const body = await req.json();
        const { source_columns, schema_type = "invoices" } = body as {
            source_columns: string[];
            schema_type?: string;
        };

        if (!source_columns || !Array.isArray(source_columns) || source_columns.length === 0) {
            return json({ error: "source_columns must be a non-empty array", error_code: "INVALID_INPUT" }, 400);
        }

        const validSchemaTypes: SchemaType[] = ["invoices", "fato_transacoes", "fato_compras", "dim_clientes", "dim_inventory"];
        const normalizedSchemaType: SchemaType = validSchemaTypes.includes(schema_type.toLowerCase() as SchemaType)
            ? schema_type.toLowerCase() as SchemaType
            : "invoices";

        // Load canonical column definitions (DB or in-memory for "invoices")
        const canonicalDefs = await getCanonicalDefs(normalizedSchemaType);
        if (!canonicalDefs.length) {
            return json({ error: "Could not load canonical schema", error_code: "SCHEMA_LOAD_ERROR" }, 500);
        }

        logInfo("Starting column matching", {
            requestId,
            sourceColumns: source_columns,
            schemaType: normalizedSchemaType,
            canonicalColumnCount: canonicalDefs.length,
        });

        const result = autoMatch(source_columns, normalizedSchemaType, canonicalDefs);

        // Future: if result.unmatched.length > 0 → escalate to skill:match-columns-llm

        const totalDuration = Date.now() - startTime;
        logInfo("Request completed", {
            requestId,
            totalDuration,
            matched: Object.keys(result.matched).length,
            needsReview: result.needs_review.length,
            unmatched: result.unmatched.length,
        });

        return json(result, 200, { "X-Request-Id": requestId, "X-Duration-Ms": totalDuration.toString() });

    } catch (error) {
        logError("Unhandled exception", error, { requestId });
        return json({ error: "Internal server error", error_code: "INTERNAL_ERROR", request_id: requestId }, 500, { "X-Request-Id": requestId });
    }
});
