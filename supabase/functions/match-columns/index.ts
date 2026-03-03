// Schema Matcher Edge Function
// Port of services/data_ingestion_api/src/data_ingestion_api/services/schema_matcher_service.py
// Uses string-similarity for fuzzy matching (equivalent to Python's difflib.SequenceMatcher)

import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { compareTwoStrings } from "https://esm.sh/string-similarity@4.0.4";

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

type SchemaType = "invoices" | "fato_transacoes" | "dim_clientes" | "dim_inventory" | "dim_categoria";

// =============================================================================
// Canonical Schemas (Portuguese-aligned with analytics_v2 tables)
// =============================================================================

const CANONICAL_SCHEMAS: Record<SchemaType, string[]> = {
    // Main schema for BigQuery invoice data → analytics_v2 multi-table ETL
    // Each canonical name must be UNIQUE so dedup works (one source → one target)
    invoices: [
        // === fato_transacoes (scalar columns via column_mapping) ===
        "documento",            // id_operatorinvoice → internal operation ID
        "nf_numero",            // product_nf → NF-e number
        "data_competencia_id",  // emittedat_operatorinvoice → emission date (YYYYMMDD)
        "quantidade",           // quantitytraded_product
        "quantidade_kg",        // quantitytradedkg_product
        "valor_unitario",       // unitprice_product
        "valor_unitario_kg",    // unitpricekg_product
        "valor",                // totalprice_product → product line total
        "valor_nf",             // price_operatorinvoice → invoice total with taxes
        "status",               // status_operatorinvoice
        "movement_type",        // natop_operatorinvoice → NATOP
        "danfe",                // danfe → DANFE access key
        "data_criacao_origem",  // createdat_operatorinvoice → source creation date
        "is_blocked",           // isblocked_operatorinvoice
        "volume",               // volume_operatorinvoice
        "volume_validado",      // validvolume_operatorinvoice
        "valor_validado",       // validprice_operatorinvoice
        "id_credito",           // id_invoicecredit → credit note ID
        "data_credito",         // createdat_invoicecredit → credit note date
        "status_produto",       // status_product → product-level status
        "data_criacao_produto", // createdat_product → product creation date
        "was_purchased",        // was_purchased
        "was_compensation",     // was_compensation
        "compensations_ids",    // compensations_ids
        "purchase_order_ids",   // purchaseordersids
        "purchase_order_codes", // purchaseorders_codes
        "in_offer",             // invoice_in_offer
        "has_credit",           // has_invoice_credit
        "product_invalidations", // product_invalidations
        "cpl_adicional",        // aditional_cpl_operatorinvoice
        "fisco_adicional",      // aditional_fisco_operatorinvoice
        "danfe_materials",      // danfe_materials
        "filial_id",            // id_subsidiary
        "filial_cnpj",          // cnpj_subsidiary

        // === dim_fornecedores (auto-handled by ETL, mapping is informational) ===
        "fornecedor_cnpj",       // emitterlegaldoc
        "fornecedor_nome",       // emitterlegalname
        "fornecedor_nome_fantasia", // emitterfantasyname
        "fornecedor_telefone",   // emitterphone
        "fornecedor_cnae",       // emittercnae
        "fornecedor_rua",        // emitterstreet
        "fornecedor_numero",     // emitternumber
        "fornecedor_bairro",     // emitterneighborhood
        "fornecedor_cidade",     // emittercity
        "fornecedor_uf",         // emitterstateuf
        "fornecedor_cep",        // emitterzipcode
        "fornecedor_company_id", // companyid

        // === dim_clientes (auto-handled by ETL, mapping is informational) ===
        "cliente_cpf_cnpj",      // receiverlegaldoc
        "cliente_nome",          // receiverlegalname
        "cliente_nome_fantasia", // receiverfantasyname
        "cliente_telefone",      // receiverphone
        "cliente_cnae",          // receivercnae
        "cliente_rua",           // receiverstreet
        "cliente_numero",        // receivernumber
        "cliente_bairro",        // receiverneighborhood
        "cliente_cidade",        // receivercity
        "cliente_uf",            // receiverstateuf
        "cliente_cep",           // receiverzipcode

        // === dim_inventory (auto-handled by ETL, mapping is informational) ===
        "produto_id_externo",    // id_product → external product ID
        "produto_descricao",     // description_product
        "produto_ncm",           // ncm → fiscal classification
        "produto_unidade",       // commercialunit_product

        // === dim_tipo_transacao (auto-handled by ETL, mapping is informational) ===
        "tipo_cfop",             // cfop

        // === dim_categoria (auto-handled by ETL, mapping is informational) ===
        "categoria_material",    // material

    ],

    // Customers dimension → analytics_v2.clientes (aligned with migration 20260224)
    dim_clientes: [
        "cliente_id",            // UUID PK
        "client_id",             // Tenant isolation (UUID)
        "cpf_cnpj",              // CPF/CNPJ (VARCHAR 20)
        "nome",                  // Customer name (VARCHAR 255)
        "nome_fantasia",         // Trade name / fantasy name
        "cnae",                  // CNAE economic activity code
        "telefone",              // Phone (VARCHAR 50)
        "endereco_rua",          // Street address (VARCHAR 255)
        "endereco_numero",       // Street number (VARCHAR 50)
        "endereco_bairro",       // Neighborhood (VARCHAR 100)
        "endereco_cidade",       // City (VARCHAR 100)
        "endereco_uf",           // State (VARCHAR 2)
        "endereco_cep",          // Postal code (VARCHAR 10)
        "total_pedidos",         // Aggregated: total orders
        "receita_total",         // Aggregated: total revenue
        "ticket_medio",          // Aggregated: average order value
        "quantidade_total",      // Aggregated: total quantity
        "pedidos_ultimos_30_dias", // Aggregated: orders in last 30 days
        "frequencia_mensal",     // Aggregated: orders per month
        "dias_recencia",         // Aggregated: days since last order
        "data_primeira_compra",  // First purchase date
        "data_ultima_compra",    // Last purchase date
        "pontuacao_cluster",     // Cluster score (DECIMAL 5,2)
        "nivel_cluster",         // Cluster tier (VARCHAR 50)
        "criado_em",
        "atualizado_em",
    ],
    // Inventory dimension → analytics_v2.dim_inventory
    dim_inventory: [
        "inventory_id",
        "produto_id",
        "sku",                  // Product ID from source (id_product)
        "nome",                 // Product description (description_product)
        "ncm",                  // NCM fiscal classification
        "unidade_comercial",    // Commercial unit (KG, UN, CX)
        "external_id",          // External product ID
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
    // Normalized fact table → analytics_v2.fato_transacoes (FK-based, no denormalized fields)
    fato_transacoes: [
        "documento",
        "nf_numero",
        "data_competencia_id",
        "data_vencimento_id",
        "data_efetiva_id",
        "tipo_id",
        "categoria_id",
        "cliente_id",
        "fornecedor_id",
        "produto_id",
        "parcela",
        "quantidade",
        "quantidade_kg",
        "valor_unitario",
        "valor_unitario_kg",
        "valor",
        "valor_nf",
        "status",
        "movement_type",
        "origem_tabela",
        "origem_id",
    ],
    // Categories → analytics_v2.dim_categoria
    dim_categoria: [
        "nome",              // Category name (TEXT, unique per client)
        "tipo",              // Category type (TEXT)
        "grupo",             // Category group (TEXT)
    ],
};

// =============================================================================
// Column Aliases (maps source variations → canonical names)
// =============================================================================

const COLUMN_ALIASES: Record<string, string[]> = {
    // =============================================================================
    // INVOICES schema: 1-to-1 aliases for all BQ products_invoices columns.
    // Each BQ column maps to exactly ONE unique canonical target so dedup works.
    // =============================================================================

    // --- fato_transacoes scalar columns (actually stored via column_mapping) ---
    documento: ["id_operatorinvoice", "id_invoice", "invoice_id", "order_id", "orderid"],
    nf_numero: ["product_nf", "nota_fiscal", "nf_number", "numero_nf", "nf_e"],
    data_competencia_id: ["emittedat_operatorinvoice", "data_emissao", "emission_date"],
    quantidade: ["quantitytraded_product", "quantity", "qty", "qtd"],
    quantidade_kg: ["quantitytradedkg_product", "qty_kg", "qtd_kg"],
    valor_unitario: ["unitprice_product", "unit_price", "preco_unitario"],
    valor_unitario_kg: ["unitpricekg_product", "unit_price_kg", "preco_unitario_kg"],
    valor: ["totalprice_product", "total_price", "grand_total"],
    valor_nf: ["price_operatorinvoice", "total_nf", "valor_nota_fiscal", "invoice_total"],
    status: ["status_operatorinvoice", "order_status"],
    movement_type: ["natop_operatorinvoice", "natureza_operacao", "natop", "tipo_movimento"],
    danfe: ["danfe", "danfe_key", "chave_danfe"],
    data_criacao_origem: ["createdat_operatorinvoice", "operation_created_at"],
    is_blocked: ["isblocked_operatorinvoice", "blocked", "bloqueado"],
    volume: ["volume_operatorinvoice", "volume_total"],
    volume_validado: ["validvolume_operatorinvoice", "valid_volume"],
    valor_validado: ["validprice_operatorinvoice", "valid_price", "preco_validado"],
    id_credito: ["id_invoicecredit", "credit_note_id", "nota_credito_id"],
    data_credito: ["createdat_invoicecredit", "credit_created_at"],
    status_produto: ["status_product", "product_status"],
    data_criacao_produto: ["createdat_product", "product_created_at"],
    was_purchased: ["was_purchased", "compra_efetiva"],
    was_compensation: ["was_compensation", "compensacao"],
    compensations_ids: ["compensations_ids", "ids_compensacoes"],
    purchase_order_ids: ["purchaseordersids", "purchase_orders_ids"],
    purchase_order_codes: ["purchaseorders_codes", "purchase_orders_codes"],
    in_offer: ["invoice_in_offer", "oferta"],
    has_credit: ["has_invoice_credit", "tem_credito"],
    product_invalidations: ["product_invalidations", "invalidacoes_produto"],
    cpl_adicional: ["aditional_cpl_operatorinvoice", "cpl_additional"],
    fisco_adicional: ["aditional_fisco_operatorinvoice", "fisco_additional"],
    danfe_materials: ["danfe_materials", "materiais_danfe"],
    filial_id: ["id_subsidiary", "subsidiary_id", "branch_id"],
    filial_cnpj: ["cnpj_subsidiary", "subsidiary_cnpj"],

    // --- dim_fornecedores (auto-handled by ETL, mapping is informational) ---
    fornecedor_cnpj: ["emitterlegaldoc", "emitter_cnpj", "supplier_cnpj"],
    fornecedor_nome: ["emitterlegalname", "nome_emitter", "supplier_name"],
    fornecedor_nome_fantasia: ["emitterfantasyname", "emitter_fantasy_name"],
    fornecedor_telefone: ["emitterphone", "emitter_phone", "supplier_phone"],
    fornecedor_cnae: ["emittercnae", "emitter_cnae"],
    fornecedor_rua: ["emitterstreet", "emitter_rua"],
    fornecedor_numero: ["emitternumber", "emitter_numero"],
    fornecedor_bairro: ["emitterneighborhood", "emitter_bairro"],
    fornecedor_cidade: ["emittercity", "emitter_cidade"],
    fornecedor_uf: ["emitterstateuf", "emitter_uf"],
    fornecedor_cep: ["emitterzipcode", "emitter_cep"],
    fornecedor_company_id: ["companyid", "company_id", "emitter_company_id"],

    // --- dim_clientes (auto-handled by ETL, mapping is informational) ---
    cliente_cpf_cnpj: ["receiverlegaldoc", "receiver_cnpj", "customer_doc"],
    cliente_nome: ["receiverlegalname", "nome_receiver", "customer_name"],
    cliente_nome_fantasia: ["receiverfantasyname", "receiver_fantasy_name"],
    cliente_telefone: ["receiverphone", "receiver_phone", "customer_phone"],
    cliente_cnae: ["receivercnae", "receiver_cnae"],
    cliente_rua: ["receiverstreet", "receiver_rua", "customer_street"],
    cliente_numero: ["receivernumber", "receiver_numero", "customer_number"],
    cliente_bairro: ["receiverneighborhood", "receiver_bairro"],
    cliente_cidade: ["receivercity", "receiver_cidade", "customer_city"],
    cliente_uf: ["receiverstateuf", "receiver_uf", "customer_state"],
    cliente_cep: ["receiverzipcode", "receiver_cep", "customer_zip"],

    // --- dim_inventory (auto-handled by ETL, mapping is informational) ---
    produto_id_externo: ["id_product", "product_id", "external_product_id"],
    produto_descricao: ["description_product", "descricao_produto", "product_description"],
    produto_ncm: ["ncm", "ncm_code", "fiscal_classification"],
    produto_unidade: ["commercialunit_product", "commercial_unit", "unit_of_measure"],

    // --- dim_tipo_transacao (auto-handled by ETL, mapping is informational) ---
    tipo_cfop: ["cfop", "cfop_code", "codigo_cfop"],

    // --- dim_categoria (auto-handled by ETL, mapping is informational) ---
    categoria_material: ["material", "material_code", "grupo_material"],

    // =============================================================================
    // Legacy aliases for non-invoice schemas (fcx_vendas, dim_produtos, etc.)
    // =============================================================================
    pedido_id: [
        "id_operatorinvoice", "id_invoice", "invoice_id", "order_id",
        "orderid", "numero_pedido", "id_pedido", "order_number", "id",
    ],
    data_transacao: [
        "emittedat_operatorinvoice", "createdat_invoicecredit", "createdat_operatorinvoice",
        "createdat_product", "order_date", "data_pedido", "transaction_date",
        "date", "created_at", "purchase_date", "data_compra",
    ],
    valor_total: ["totalprice_product", "total_price", "total", "grand_total", "order_total"],

    // --- Products ---
    produto_id: ["product_id", "productid", "prod_id", "item_id", "sku_id", "id"],
    nome: ["name", "title", "product_title", "item_name", "productname", "product_name", "full_name", "customer_name"],
    categoria: ["material", "category", "category_name", "tipo_material"],
    descricao: ["body", "body_html", "content", "details", "desc", "description"],
    preco: ["price", "unit_price", "sale_price", "selling_price", "valor"],
    preco_custo: ["cost", "custo", "cost_price", "purchase_price", "wholesale_price"],
    sku: ["item_sku", "product_sku", "codigo", "code", "id_product"],
    ncm: ["ncm_product", "ncm_code", "fiscal_classification"],
    unidade_comercial: ["commercialunit_product", "commercial_unit", "uom"],
    external_id: ["id_product", "external_product_id"],
    codigo_barras: ["barcode", "ean", "upc", "gtin"],
    quantidade_estoque: ["stock_quantity", "available_quantity", "qty_available", "in_stock", "estoque"],
    marca: ["brand", "manufacturer", "fabricante"],
    fornecedor: ["vendor", "supplier", "seller"],
    imagem_url: ["image_url", "image", "photo", "thumbnail", "imagem", "foto"],
    criado_em: ["created_at", "createdat", "date_created", "creation_date"],
    atualizado_em: ["updated_at", "updatedat", "date_modified", "modification_date"],

    // --- Customers ---
    cliente_id: ["customer_id", "client_id", "user_id", "id"],
    cpf_cnpj: ["receiverlegaldoc", "receiver_cnpj", "customer_doc", "cpf"],
    sobrenome: ["last_name", "lastname", "family_name", "surname"],
    email: ["customer_email", "email_address", "e_mail"],
    telefone: ["phone", "telephone", "mobile", "celular", "phone_number"],
    endereco_rua: ["street", "logradouro", "rua"],
    endereco_numero: ["street_number", "numero_endereco"],
    endereco_bairro: ["neighborhood", "bairro"],
    endereco_cidade: ["city", "cidade", "municipio"],
    endereco_uf: ["state", "uf", "estado"],
    endereco_cep: ["zipcode", "postal_code", "cep"],
    endereco: ["address", "address_line"],
    cidade: ["city", "locality"],
    estado: ["state", "province", "region"],
    pais: ["country", "country_code"],
    cep: ["postal_code", "zip_code", "postcode"],
    total_pedidos: ["orders_count", "order_count", "num_orders"],
    valor_total_gasto: ["total_spent", "lifetime_value", "total_revenue"],
    nome_fantasia: ["fantasy_name", "trade_name", "nome_comercial"],
    cnae: ["cnae_code", "atividade_economica"],

    // --- Orders ---
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
    parcela: ["installment", "parcela_numero", "installment_number"],
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
        // Maps to fato_transacoes columns
        data: "data_competencia_id",
        valor: "valor",
        total: "valor",
        preco: "valor_unitario",
        qtd: "quantidade",
        pedido: "documento",
        nf: "nf_numero",
        nota: "nf_numero",
        nota_fiscal: "nf_numero",
        natureza: "movement_type",
        natop: "movement_type",
        kg: "quantidade_kg",
    },

    dim_inventory: {
        quantidade: "quantity_on_hand",
        codigo: "sku",
        estoque: "quantity_on_hand",
    },
    fato_transacoes: {
        valor: "valor",
        total: "valor",
        quantidade: "quantidade",
        codigo: "documento",
        data: "data_competencia_id",
        status: "status",
    },
    dim_categoria: {
        nome: "nome",
        categoria: "nome",
        tipo: "tipo",
        grupo: "grupo",
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
    const requestId = crypto.randomUUID();
    const startTime = Date.now();

    // Shared CORS headers for all responses
    const corsHeaders: Record<string, string> = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, apikey, x-client-info",
    };

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
        return new Response(JSON.stringify({ error: "Method not allowed" }), {
            status: 405,
            headers: { "Content-Type": "application/json", ...corsHeaders },
        });
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
            return new Response(
                JSON.stringify({
                    error: "source_columns must be an array of strings",
                    error_code: "INVALID_INPUT",
                }),
                { status: 400, headers: { "Content-Type": "application/json", ...corsHeaders } }
            );
        }

        if (source_columns.length === 0) {
            logError("Invalid request: source_columns array is empty", undefined, { requestId });
            return new Response(
                JSON.stringify({
                    error: "source_columns array cannot be empty",
                    error_code: "EMPTY_INPUT",
                }),
                { status: 400, headers: { "Content-Type": "application/json", ...corsHeaders } }
            );
        }

        // Backwards compatibility: map legacy schema names to new names
        const LEGACY_SCHEMA_ALIASES: Record<string, SchemaType> = {
            vendas: "fato_transacoes",
            products: "dim_inventory",
            orders: "fato_transacoes",
            customers: "dim_clientes",
            inventory: "dim_inventory",
            categories: "dim_categoria",
            fcx_vendas: "fato_transacoes",
            dim_produtos: "dim_inventory",
            fcx_orders: "fato_transacoes",
            fcx_categorias: "dim_categoria",
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
            return new Response(
                JSON.stringify({
                    error: `Invalid schema_type. Must be one of: ${validSchemaTypes.join(", ")} (legacy aliases: ${legacyNames.join(", ")})`,
                    error_code: "INVALID_SCHEMA_TYPE",
                }),
                { status: 400, headers: { "Content-Type": "application/json", ...corsHeaders } }
            );
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

        return new Response(JSON.stringify(result), {
            status: 200,
            headers: {
                "Content-Type": "application/json",
                ...corsHeaders,
                "X-Request-Id": requestId,
                "X-Duration-Ms": totalDuration.toString(),
            },
        });
    } catch (error) {
        const totalDuration = Date.now() - startTime;

        logError("Unhandled exception in request handler", error, {
            requestId,
            totalDuration,
        });

        return new Response(
            JSON.stringify({
                error: "Internal server error",
                error_code: "INTERNAL_ERROR",
                details: error instanceof Error ? error.message : String(error),
                request_id: requestId,
            }),
            {
                status: 500,
                headers: {
                    "Content-Type": "application/json",
                    ...corsHeaders,
                    "X-Request-Id": requestId,
                }
            }
        );
    }
});
