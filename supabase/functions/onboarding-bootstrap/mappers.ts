/**
 * Deno/edge-function port of apps/landing/src/onboarding/mappers.ts.
 *
 * Kept verbatim so the server re-validates wizard state end-to-end with
 * the exact same shape the client produced. Any change in the landing
 * mapper must be mirrored here (or lifted to a shared module — see the
 * note in apps/landing/src/onboarding/types.ts).
 */

export type Vertical =
  | "ecommerce"
  | "servicos"
  | "industria"
  | "saude"
  | "educacao"
  | "financeiro"
  | "agro"
  | "outro"
  | null;

export type NotifyChannel = "email" | "whatsapp" | "app";

export interface OnboardingState {
  authMethod: "google" | "email" | null;
  nome: string;
  email: string;
  empresa: string;
  cnpj?: string;
  vertical: Vertical;
  porte: string;
  website: string;
  primaryFocus?: "vendas" | "operacao" | "atendimento" | "estoque" | "outro" | null;
  produtoServico?: string;
  dataPath: "systems" | "files" | "scratch" | null;
  systems: string[];
  csvUploaded: boolean;
  googleDriveConnected: boolean;
  agents: string[];
  approvalTasks: string[];
  alwaysRequireApproval?: boolean;
  routines: string[];
  notifyChannel: NotifyChannel;
  kpiSelections?: Record<string, string[]>;
  approvalLimit?: string;
  riskProfile?: string;
}

const VERTICAL_LABEL: Record<Exclude<Vertical, null>, string> = {
  ecommerce: "E-commerce / Varejo",
  servicos: "Serviços",
  industria: "Indústria",
  saude: "Saúde",
  educacao: "Educação",
  financeiro: "Financeiro",
  agro: "Agro",
  outro: "Outro",
};

const EMPLOYEE_RANGE: Record<string, string> = {
  solo: "1",
  micro: "2-10",
  pequena: "11-50",
  media: "51-250",
  grande: "250+",
};

const TASK_LABEL: Record<string, string> = {
  send_email: "Enviar e-mails",
  send_message: "Enviar mensagens",
  book_appointment: "Marcar compromissos",
  supplier_order: "Fazer pedidos a fornecedores",
  make_payment: "Realizar pagamentos",
  publish_content: "Publicar em redes sociais",
  update_prices: "Alterar preços e catálogo",
  share_report: "Compartilhar relatórios",
};

const ALL_TASK_IDS = Object.keys(TASK_LABEL);

export function mapBusinessDNAToCompanyProfile(
  state: OnboardingState,
): Record<string, unknown> {
  const out: Record<string, unknown> = { core_values: [] };
  const name = (state.empresa ?? "").trim();
  if (name) {
    out.legal_name = name;
    out.trading_name = name;
  }
  if (state.vertical) {
    out.industry = VERTICAL_LABEL[state.vertical];
  }
  if (state.porte && EMPLOYEE_RANGE[state.porte]) {
    out.employee_count_range = EMPLOYEE_RANGE[state.porte];
  }
  if ((state.website ?? "").trim()) {
    out.website = state.website.trim();
  }
  if (state.primaryFocus) {
    out.primary_focus = state.primaryFocus;
  }
  if ((state.produtoServico ?? "").trim()) {
    out.main_product_service = state.produtoServico!.trim();
  }
  return out;
}

export function mapContactToTeamStructure(
  state: OnboardingState,
): Record<string, unknown> {
  const channels: Record<string, string> = {};
  if (state.email) channels.email = state.email;
  if (state.notifyChannel === "whatsapp") channels.whatsapp = "pendente";
  if (state.notifyChannel === "app") channels.app = "dashboard";

  const out: Record<string, unknown> = {
    key_contacts: state.nome
      ? [
          {
            role: "Fundador / Operação",
            name: state.nome,
            contact_preference: state.notifyChannel,
          },
        ]
      : [],
    communication_channels: channels,
    escalation_path: [],
    operational_locations: [],
  };
  if (state.nome) out.main_contact = state.nome;
  return out;
}

export function mapRulesToPolicies(
  state: OnboardingState,
): Record<string, unknown> {
  const requires = Array.from(
    new Set((state.approvalTasks ?? []).map((t) => TASK_LABEL[t] ?? t)),
  );
  const autonomous = ALL_TASK_IDS
    .filter((t) => !(state.approvalTasks ?? []).includes(t))
    .map((t) => TASK_LABEL[t]);

  return {
    communication_rules: [],
    operational_limits: [],
    approval_requirements: {
      autonomous,
      requires_approval: requires,
    },
    red_flags: [],
    data_handling_rules: [],
  };
}

