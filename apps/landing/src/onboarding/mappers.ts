/**
 * Pure mappers: wizard OnboardingState -> Context 2.0 JSONB payloads.
 *
 * These functions are intentionally total and side-effect free so they
 * are trivially unit-testable (see mappers.test.ts in Phase 6) and so
 * the LaunchPad bootstrap edge function can share the exact same shape
 * via the BootstrapPayload contract.
 *
 * Each mapper takes the full OnboardingState and returns a *partial*
 * Context 2.0 section — the caller merges it into whatever the server
 * already has. We never invent facts the user didn't provide (undefined
 * fields are left absent, not filled with empty strings).
 */

import type { OnboardingState, Vertical } from "./state";
import type {
  CompanyProfile,
  Policies,
  TeamStructure,
} from "./types";

// Labels used in Context 2.0 industry field. Keep in sync with
// libs/blu_models/src/blu_models/context_schemas.py (free-form string,
// but these match the landing's vertical enum 1:1).
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

// Map the ApprovalTaskId enum to short human-readable labels the agent
// prompt templates use. Keep aligned with supabase/functions/onboarding-
// bootstrap (Phase 4) — those strings end up in policies.approval_requirements.
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

/**
 * BusinessDNA slice -> CompanyProfile. Empresa name, vertical and porte
 * are the minimum viable set we collect up-front; website gets folded
 * into `tagline` when present (no dedicated field in the schema).
 */
export function mapBusinessDNAToCompanyProfile(
  state: OnboardingState,
): Partial<CompanyProfile> {
  const out: Partial<CompanyProfile> = {
    core_values: [],
  };
  const name = state.empresa.trim();
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
  if (state.website.trim()) {
    // Website has no first-class slot on CompanyProfile; parked on tagline
    // so it's visible to agents until a dedicated column exists.
    out.tagline = state.website.trim();
  }
  return out;
}

/**
 * Notify channel + authenticated user contact populates a minimal
 * TeamStructure. This is a seed — the dashboard will let the user
 * enrich it post-onboarding.
 */
export function mapContactToTeamStructure(
  state: OnboardingState,
): Partial<TeamStructure> {
  const channels: Record<string, string> = {};
  if (state.email) channels.email = state.email;
  if (state.notifyChannel === "whatsapp") channels.whatsapp = "pendente";
  if (state.notifyChannel === "app") channels.app = "dashboard";

  const out: Partial<TeamStructure> = {
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

/**
 * CommandRules slice -> Policies. Splits the approval-task list into
 * `requires_approval` vs `autonomous` using the full task enum so
 * downstream agents can reason about both sides explicitly.
 */
export function mapRulesToPolicies(state: OnboardingState): Partial<Policies> {
  const requires = new Set(state.approvalTasks.map((t) => TASK_LABEL[t] ?? t));
  const autonomous = ALL_TASK_IDS
    .filter((t) => !state.approvalTasks.includes(t as never))
    .map((t) => TASK_LABEL[t]);

  return {
    communication_rules: [],
    operational_limits: [],
    approval_requirements: {
      autonomous,
      requires_approval: Array.from(requires),
    },
    red_flags: [],
    data_handling_rules: [],
  };
}

/**
 * DataFork + agents -> CurrentMoment seed. We only populate what the
 * wizard actually collected so the agent context reflects real answers.
 */
