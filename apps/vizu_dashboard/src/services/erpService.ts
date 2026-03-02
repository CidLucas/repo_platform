/**
 * ERP Service — Supabase-native API calls (Portuguese)
 *
 * Serviço de acesso tipado aos endpoints ERP via Supabase PostgREST.
 * Operações de leitura usam endpoints auto-gerados do PostgREST.
 * Operações de escrita usam funções RPC.
 *
 * Autenticação: JWT obrigatório (via Supabase auth)
 * Multi-tenancy: Políticas RLS filtram por client_id automaticamente
 */

import { supabase } from "../lib/supabase";

// =============================================================================
// CONSTANTES
// =============================================================================

const ANALYTICS_SCHEMA = "analytics_v2";

// =============================================================================
// TIPOS
// =============================================================================

// Paginação
export interface Paginacao {
  total: number;
  limite: number;
  offset: number;
  tem_mais: boolean;
}

export interface RespostaPaginada<T> {
  dados: T[];
  paginacao: Paginacao;
}

export interface OpcoesConsulta {
  limite?: number;
  offset?: number;
  ordenarPor?: string;
  ascendente?: boolean;
  filtros?: Record<string, string | number | boolean | null>;
}

// Cliente (matches analytics_v2.erp_clientes)
export interface ErpCliente {
  cliente_id: string;
  client_id: string;
  nome: string;
  cpf_cnpj: string | null;
  telefone: string | null;
  endereco_rua: string | null;
  endereco_numero: string | null;
  endereco_bairro: string | null;
  endereco_cidade: string | null;
  endereco_uf: string | null;
  endereco_cep: string | null;
  valor_total_compras: number;
  quantidade_total: number;
  total_pedidos: number;
  ticket_medio: number;
  frequencia_mensal: number;
  dias_recencia: number;
  pedidos_ultimos_30_dias: number | null;
  pontuacao_cluster: number;
  nivel_cluster: string | null;
  data_primeira_compra: string | null;
  data_ultima_compra: string | null;
  criado_em: string;
  atualizado_em: string;
}

export interface CriarClienteInput {
  p_nome: string;
  p_cpf_cnpj?: string;
  p_telefone?: string;
  p_endereco_rua?: string;
  p_endereco_numero?: string;
  p_endereco_bairro?: string;
  p_endereco_cidade?: string;
  p_endereco_uf?: string;
  p_endereco_cep?: string;
}

export interface AtualizarClienteInput {
  p_cliente_id: string;
  p_nome?: string;
  p_cpf_cnpj?: string;
  p_telefone?: string;
  p_endereco_rua?: string;
  p_endereco_numero?: string;
  p_endereco_bairro?: string;
  p_endereco_cidade?: string;
  p_endereco_uf?: string;
  p_endereco_cep?: string;
}

// Fornecedor (matches analytics_v2.erp_fornecedores)
export interface ErpFornecedor {
  fornecedor_id: string;
  client_id: string;
  nome: string;
  cnpj: string | null;
  telefone: string | null;
  endereco_cidade: string | null;
  endereco_uf: string | null;
  valor_total_compras: number;
  total_pedidos_recebidos: number;
  ticket_medio: number;
  total_produtos_fornecidos: number;
  frequencia_mensal: number;
  dias_recencia: number;
  pontuacao_cluster: number;
  nivel_cluster: string | null;
  data_primeira_transacao: string | null;
  data_ultima_transacao: string | null;
  criado_em: string;
  atualizado_em: string;
}

export interface CriarFornecedorInput {
  p_nome: string;
  p_cnpj?: string;
  p_telefone?: string;
  p_endereco_cidade?: string;
  p_endereco_uf?: string;
}

// Produto (matches analytics_v2.erp_produtos)
export interface ErpProduto {
  produto_id: string;
  client_id: string;
  nome: string;
  categoria: string | null;
  ncm: string | null;
  cfop: string | null;
  receita_total: number;
  quantidade_total_vendida: number;
  total_pedidos: number;
  quantidade_media_por_pedido: number;
  preco_medio: number;
  frequencia_mensal: number;
  dias_recencia: number;
  data_ultima_venda: string | null;
  pontuacao_cluster: number;
  nivel_cluster: string | null;
  criado_em: string;
  atualizado_em: string;
}

export interface CriarProdutoInput {
  p_nome: string;
  p_categoria?: string;
  p_ncm?: string;
  p_cfop?: string;
}

// Pedido (matches analytics_v2.erp_pedidos)
export interface ErpPedido {
  pedido_id: string;
  client_id: string;
  cliente_id: string | null;
  nome_cliente: string | null;
  cpf_cnpj_cliente: string | null;
  data_pedido: string;
  valor_total: number;
  quantidade_total: number;
  total_itens: number;
  status: string;
  criado_em: string;
  atualizado_em: string;
}

// Item de Pedido (matches analytics_v2.erp_itens_pedido)
export interface ErpItemPedido {
  venda_id: string;
  pedido_id: string;
  client_id: string;
  produto_id: string;
  nome_produto: string;
  quantidade: number;
  valor_unitario: number;
  valor_total: number;
  sequencia_item: number;
  criado_em: string;
}

export interface CriarPedidoInput {
  p_cliente_id: string;
  p_pedido_id?: string;
  p_itens: Array<{
    produto_id: string;
    quantidade: number;
    valor_unitario: number;
    data?: string;
  }>;
}

// Transação (matches analytics_v2.erp_transacoes)
export interface ErpTransacao {
  transacao_id: string;
  pedido_id: string;
  client_id: string;
  cliente_id: string | null;
  nome_cliente: string | null;
  produto_id: string | null;
  nome_produto: string | null;
  fornecedor_id: string | null;
  nome_fornecedor: string | null;
  data_transacao: string;
  quantidade: number;
  valor_unitario: number;
  valor_total: number;
  date_id: number | null;
  time_id: number | null;
  criado_em: string;
  atualizado_em: string;
}

// Estoque (matches analytics_v2.erp_inventory)
export interface ErpEstoque {
  inventory_id: string;
  client_id: string;
  product_id: string;
  warehouse_code: string;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  reorder_point: number;
  reorder_quantity: number;
  unit_cost: number;
  last_counted_at: string | null;
  created_at: string;
  updated_at: string;
}

// Movimento de Estoque (matches analytics_v2.erp_inventory_movements)
export interface ErpMovimentoEstoque {
  movement_id: string;
  client_id: string;
  product_id: string;
  warehouse_code: string;
  movement_type: "entrada" | "saida" | "ajuste" | "transferencia" | "devolucao" | "descarte";
  quantity: number;
  reference_type: string | null;
  reference_id: string | null;
  notes: string | null;
  performed_by: string | null;
  created_at: string;
}

export interface AjustarEstoqueInput {
  p_produto_id: string;
  p_quantidade: number;
  p_tipo_movimento?: string;
  p_codigo_deposito?: string;
  p_tipo_referencia?: string;
  p_id_referencia?: string;
  p_observacoes?: string;
}

// Ordem de Compra (matches analytics_v2.erp_purchase_orders)
export interface ErpOrdemCompra {
  purchase_order_id: string;
  client_id: string;
  supplier_id: string | null;
  order_number: string;
  status: "draft" | "pending_approval" | "approved" | "ordered" | "partial_received" | "received" | "cancelled";
  order_date: string;
  expected_delivery_date: string | null;
  total_value: number;
  notes: string | null;
  created_by: string | null;
  approved_by: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

// Item de Ordem de Compra (matches analytics_v2.erp_purchase_order_items)
export interface ErpItemOrdemCompra {
  item_id: string;
  purchase_order_id: string;
  client_id: string;
  product_id: string | null;
  line_number: number;
  quantity_ordered: number;
  quantity_received: number;
  unit_price: number;
  total_price: number;
  created_at: string;
  updated_at: string;
}

export interface CriarOrdemCompraInput {
  p_fornecedor_id: string;
  p_numero_ordem?: string;
  p_data_entrega_prevista?: string;
  p_itens: Array<{
    produto_id: string;
    quantidade: number;
    valor_unitario: number;
  }>;
  p_observacoes?: string;
}

// Job (matches analytics_v2.erp_jobs)
export interface ErpJob {
  job_id: string;
  client_id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  input_params: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error_message: string | null;
  progress_pct: number;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

// Resultado de Busca
export interface ResultadoBusca {
  tipo_entidade: "cliente" | "fornecedor" | "produto" | "pedido";
  entidade_id: string;
  nome_exibicao: string;
  info_secundaria: string | null;
  pontuacao: number;
}

// Resumo Dashboard (matches analytics_v2.erp_resumo_dashboard)
export interface ResumoDashboard {
  client_id: string;
  total_clientes: number;
  total_fornecedores: number;
  total_produtos: number;
  total_pedidos: number;
  receita_total: number;
  ticket_medio: number;
  gerado_em: string;
}

// =============================================================================
// FUNÇÕES AUXILIARES
// =============================================================================

/**
 * Consulta paginada genérica
 */
async function consultaPaginada<T>(
  tabela: string,
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<T>> {
  const {
    limite = 50,
    offset = 0,
    ordenarPor = "criado_em",
    ascendente = false,
    filtros = {},
  } = opcoes;

  let query = supabase
    .schema(ANALYTICS_SCHEMA)
    .from(tabela)
    .select("*", { count: "exact" });

  // Aplicar filtros
  for (const [chave, valor] of Object.entries(filtros)) {
    if (valor !== null && valor !== undefined && valor !== "") {
      if (typeof valor === "string" && valor.includes("%")) {
        query = query.ilike(chave, valor);
      } else {
        query = query.eq(chave, valor);
      }
    }
  }

  // Aplicar ordenação
  query = query.order(ordenarPor, { ascending: ascendente });

  // Aplicar paginação
  query = query.range(offset, offset + limite - 1);

  const { data, error, count } = await query;

  if (error) {
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return {
    dados: (data as T[]) ?? [],
    paginacao: {
      total: count ?? 0,
      limite,
      offset,
      tem_mais: offset + limite < (count ?? 0),
    },
  };
}

/**
 * Executar função RPC no schema analytics_v2
 */
async function chamarRpc<T = unknown, P extends object = object>(
  nomeFuncao: string,
  parametros: P
): Promise<T> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .rpc(nomeFuncao, parametros as never);

  if (error) {
    throw new Error(`Erro ERP RPC: ${error.message}`);
  }

  return data as T;
}

// =============================================================================
// ENDPOINTS DE CLIENTES
// =============================================================================

/**
 * Listar clientes com paginação
 */
export async function listarClientes(
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<ErpCliente>> {
  return consultaPaginada<ErpCliente>("erp_clientes", {
    ...opcoes,
    ordenarPor: opcoes.ordenarPor ?? "valor_total_compras",
    ascendente: opcoes.ascendente ?? false,
  });
}

/**
 * Buscar cliente por ID
 */
export async function obterCliente(
  clienteId: string
): Promise<ErpCliente | null> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_clientes")
    .select("*")
    .eq("cliente_id", clienteId)
    .single();

  if (error) {
    if (error.code === "PGRST116") return null;
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return data as ErpCliente;
}

/**
 * Buscar cliente por CPF/CNPJ, nome ou telefone
 */
export async function buscarCliente(params: {
  cpf_cnpj?: string;
  nome?: string;
  telefone?: string;
}): Promise<ErpCliente[]> {
  const dados = await chamarRpc<ErpCliente[]>("erp_buscar_cliente", {
    p_cpf_cnpj: params.cpf_cnpj ?? null,
    p_nome: params.nome ?? null,
    p_telefone: params.telefone ?? null,
  });
  return dados ?? [];
}

/**
 * Criar novo cliente
 */
export async function criarCliente(input: CriarClienteInput): Promise<string> {
  return chamarRpc<string>("erp_criar_cliente", input);
}

/**
 * Atualizar cliente
 */
export async function atualizarCliente(input: AtualizarClienteInput): Promise<boolean> {
  return chamarRpc<boolean>("erp_atualizar_cliente", input);
}

// =============================================================================
// ENDPOINTS DE FORNECEDORES
// =============================================================================

/**
 * Listar fornecedores com paginação
 */
export async function listarFornecedores(
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<ErpFornecedor>> {
  return consultaPaginada<ErpFornecedor>("erp_fornecedores", {
    ...opcoes,
    ordenarPor: opcoes.ordenarPor ?? "valor_total_compras",
    ascendente: opcoes.ascendente ?? false,
  });
}

/**
 * Buscar fornecedor por ID
 */
export async function obterFornecedor(
  fornecedorId: string
): Promise<ErpFornecedor | null> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_fornecedores")
    .select("*")
    .eq("fornecedor_id", fornecedorId)
    .single();

  if (error) {
    if (error.code === "PGRST116") return null;
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return data as ErpFornecedor;
}

/**
 * Buscar fornecedor por CNPJ ou nome
 */
export async function buscarFornecedor(params: {
  cnpj?: string;
  nome?: string;
}): Promise<ErpFornecedor[]> {
  const dados = await chamarRpc<ErpFornecedor[]>("erp_buscar_fornecedor", {
    p_cnpj: params.cnpj ?? null,
    p_nome: params.nome ?? null,
  });
  return dados ?? [];
}

/**
 * Criar novo fornecedor
 */
export async function criarFornecedor(input: CriarFornecedorInput): Promise<string> {
  return chamarRpc<string>("erp_criar_fornecedor", input);
}

// =============================================================================
// ENDPOINTS DE PRODUTOS
// =============================================================================

/**
 * Listar produtos com paginação
 */
export async function listarProdutos(
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<ErpProduto>> {
  return consultaPaginada<ErpProduto>("erp_produtos", {
    ...opcoes,
    ordenarPor: opcoes.ordenarPor ?? "receita_total",
    ascendente: opcoes.ascendente ?? false,
  });
}

/**
 * Buscar produto por ID
 */
export async function obterProduto(
  produtoId: string
): Promise<ErpProduto | null> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_produtos")
    .select("*")
    .eq("produto_id", produtoId)
    .single();

  if (error) {
    if (error.code === "PGRST116") return null;
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return data as ErpProduto;
}

/**
 * Criar novo produto
 */
export async function criarProduto(input: CriarProdutoInput): Promise<string> {
  return chamarRpc<string>("erp_criar_produto", input);
}

/**
 * Obter transações de um produto
 */
export async function obterTransacoesProduto(
  produtoId: string,
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<ErpTransacao>> {
  return consultaPaginada<ErpTransacao>("erp_transacoes", {
    ...opcoes,
    filtros: { ...opcoes.filtros, produto_id: produtoId },
    ordenarPor: opcoes.ordenarPor ?? "data_transacao",
    ascendente: opcoes.ascendente ?? false,
  });
}

// =============================================================================
// ENDPOINTS DE PEDIDOS
// =============================================================================

/**
 * Listar pedidos com paginação
 */
export async function listarPedidos(
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<ErpPedido>> {
  return consultaPaginada<ErpPedido>("erp_pedidos", {
    ...opcoes,
    ordenarPor: opcoes.ordenarPor ?? "data_pedido",
    ascendente: opcoes.ascendente ?? false,
  });
}

/**
 * Buscar pedido por ID
 */
export async function obterPedido(
  pedidoId: string
): Promise<ErpPedido | null> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_pedidos")
    .select("*")
    .eq("pedido_id", pedidoId)
    .single();

  if (error) {
    if (error.code === "PGRST116") return null;
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return data as ErpPedido;
}

/**
 * Obter itens de um pedido
 */
export async function obterItensPedido(
  pedidoId: string
): Promise<ErpItemPedido[]> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_itens_pedido")
    .select("*")
    .eq("pedido_id", pedidoId)
    .order("sequencia_item", { ascending: true });

  if (error) {
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return (data as ErpItemPedido[]) ?? [];
}

/**
 * Criar novo pedido
 */
export async function criarPedido(input: CriarPedidoInput): Promise<string> {
  return chamarRpc<string>("erp_criar_pedido", input);
}

/**
 * Listar pedidos recentes (últimos 50)
 */
export async function listarPedidosRecentes(): Promise<ErpPedido[]> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_pedidos_recentes")
    .select("*");

  if (error) {
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return (data as ErpPedido[]) ?? [];
}

// =============================================================================
// ENDPOINTS DE TRANSAÇÕES
// =============================================================================

/**
 * Listar transações com paginação
 */
export async function listarTransacoes(
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<ErpTransacao>> {
  return consultaPaginada<ErpTransacao>("erp_transacoes", {
    ...opcoes,
    ordenarPor: opcoes.ordenarPor ?? "data_transacao",
    ascendente: opcoes.ascendente ?? false,
  });
}

// =============================================================================
// ENDPOINTS DE ESTOQUE
// =============================================================================

/**
 * Listar estoque com paginação
 */
export async function listarEstoque(
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<ErpEstoque>> {
  return consultaPaginada<ErpEstoque>("erp_inventory", {
    ...opcoes,
    ordenarPor: opcoes.ordenarPor ?? "product_id",
  });
}

/**
 * Buscar estoque de um produto
 */
export async function obterEstoque(
  produtoId: string
): Promise<ErpEstoque | null> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_inventory")
    .select("*")
    .eq("product_id", produtoId)
    .single();

  if (error) {
    if (error.code === "PGRST116") return null;
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return data as ErpEstoque;
}

/**
 * Ajustar estoque
 */
export async function ajustarEstoque(input: AjustarEstoqueInput): Promise<string> {
  return chamarRpc<string>("erp_ajustar_estoque", input);
}

/**
 * Listar movimentos de estoque
 */
export async function listarMovimentosEstoque(
  produtoId: string,
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<ErpMovimentoEstoque>> {
  return consultaPaginada<ErpMovimentoEstoque>("erp_inventory_movements", {
    ...opcoes,
    filtros: { ...opcoes.filtros, product_id: produtoId },
    ordenarPor: opcoes.ordenarPor ?? "created_at",
    ascendente: opcoes.ascendente ?? false,
  });
}

// =============================================================================
// ENDPOINTS DE ORDENS DE COMPRA
// =============================================================================

/**
 * Listar ordens de compra com paginação
 */
export async function listarOrdensCompra(
  opcoes: OpcoesConsulta = {}
): Promise<RespostaPaginada<ErpOrdemCompra>> {
  return consultaPaginada<ErpOrdemCompra>("erp_purchase_orders", {
    ...opcoes,
    ordenarPor: opcoes.ordenarPor ?? "order_date",
    ascendente: opcoes.ascendente ?? false,
  });
}

/**
 * Buscar ordem de compra por ID
 */
export async function obterOrdemCompra(
  ordemId: string
): Promise<ErpOrdemCompra | null> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_purchase_orders")
    .select("*")
    .eq("purchase_order_id", ordemId)
    .single();

  if (error) {
    if (error.code === "PGRST116") return null;
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return data as ErpOrdemCompra;
}

/**
 * Obter itens de uma ordem de compra
 */
export async function obterItensOrdemCompra(
  ordemId: string
): Promise<ErpItemOrdemCompra[]> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_purchase_order_items")
    .select("*")
    .eq("purchase_order_id", ordemId)
    .order("line_number", { ascending: true });

  if (error) {
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return (data as ErpItemOrdemCompra[]) ?? [];
}

/**
 * Criar ordem de compra
 */
export async function criarOrdemCompra(input: CriarOrdemCompraInput): Promise<string> {
  return chamarRpc<string>("erp_criar_ordem_compra", input);
}

/**
 * Receber itens de ordem de compra
 */
export async function receberOrdemCompra(params: {
  p_ordem_compra_id: string;
  p_itens: Array<{ produto_id: string; quantidade_recebida: number }>;
  p_codigo_deposito?: string;
}): Promise<boolean> {
  return chamarRpc<boolean>("erp_receber_ordem_compra", params);
}

// =============================================================================
// ENDPOINTS DE BUSCA
// =============================================================================

/**
 * Busca universal em clientes, produtos, fornecedores e pedidos
 */
export async function buscar(params: {
  termo: string;
  tipos?: ("clientes" | "produtos" | "fornecedores" | "pedidos")[];
  limite?: number;
}): Promise<ResultadoBusca[]> {
  const dados = await chamarRpc<ResultadoBusca[]>("erp_busca", {
    p_termo: params.termo,
    p_tipos_entidade: params.tipos ?? ["clientes", "produtos", "fornecedores", "pedidos"],
    p_limite: params.limite ?? 20,
  });
  return dados ?? [];
}

// =============================================================================
// ENDPOINTS DE DASHBOARD
// =============================================================================

/**
 * Obter resumo do dashboard
 */
export async function obterResumoDashboard(): Promise<ResumoDashboard> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_resumo_dashboard")
    .select("*")
    .single();

  if (error) {
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return data as ResumoDashboard;
}

// =============================================================================
// ENDPOINTS DE JOBS
// =============================================================================

/**
 * Criar job assíncrono
 */
export async function criarJob(tipoJob: string, parametros: Record<string, unknown> = {}): Promise<string> {
  return chamarRpc<string>("erp_criar_job", {
    p_tipo_job: tipoJob,
    p_parametros: parametros,
  });
}

/**
 * Atualizar status do job
 */
export async function atualizarJob(params: {
  p_job_id: string;
  p_status?: string;
  p_progresso_pct?: number;
  p_resultado?: Record<string, unknown>;
  p_mensagem_erro?: string;
}): Promise<boolean> {
  return chamarRpc<boolean>("erp_atualizar_job", params);
}

/**
 * Obter job por ID
 */
export async function obterJob(jobId: string): Promise<ErpJob | null> {
  const { data, error } = await supabase
    .schema(ANALYTICS_SCHEMA)
    .from("erp_jobs")
    .select("*")
    .eq("job_id", jobId)
    .single();

  if (error) {
    if (error.code === "PGRST116") return null;
    throw new Error(`Erro ERP API: ${error.message}`);
  }

  return data as ErpJob;
}

// =============================================================================
// EXPORTS PARA COMPATIBILIDADE (deprecated - use nomes em português)
// =============================================================================

/** @deprecated Use listarClientes */
export const listCustomers = listarClientes;
/** @deprecated Use obterCliente */
export const getCustomer = obterCliente;
/** @deprecated Use criarCliente */
export const createCustomer = criarCliente;
/** @deprecated Use listarFornecedores */
export const listSuppliers = listarFornecedores;
/** @deprecated Use listarProdutos */
export const listProducts = listarProdutos;
/** @deprecated Use listarPedidos */
export const listOrders = listarPedidos;
/** @deprecated Use buscar */
export const search = buscar;
