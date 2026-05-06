import { useCallback, useEffect, useRef, useState } from "react";

import {
  getOnboardingState,
  patchOnboardingState,
} from "./services/onboardingService";
import { supabase } from "../lib/supabase";

// ========== ONBOARDING STATE (persisted in localStorage) ==========
export type DataPath = "systems" | "files" | "scratch" | null;

export type Persona = "distribuidora" | "consultoria" | "varejo" | null;
export type PainPoint = "fluxo_caixa" | "estoque" | "atendimento" | null;
export type TeamSize = "solo" | "pequeno" | "estruturado" | null;
export type FirstApprovalDecision = "approved" | "edited" | "rejected" | null;

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

export function personaToVertical(persona: Persona): Vertical {
  if (persona === "distribuidora") return "industria";
  if (persona === "consultoria") return "servicos";
  if (persona === "varejo") return "ecommerce";
  return null;
}

export type NotifyChannel = "email" | "whatsapp" | "app";

export type PrimaryFocus =
  | "vendas"
  | "operacao"
  | "atendimento"
  | "estoque"
  | "outro"
  | null;

export type KpiDimension = "commercial" | "inventory" | "supply" | "finance";

// Tasks an agent may perform. User picks which ones require human approval.
export type ApprovalTaskId =
  | "send_email"
  | "send_message"
  | "book_appointment"
  | "supplier_order"
  | "make_payment"
  | "publish_content"
  | "update_prices"
  | "share_report";

// Built-in routines that can be activated out of the box.
export type RoutineId =
  | "daily_sales_digest"
  | "low_stock_alert"
  | "stale_lead_followup"
  | "overdue_invoice"
  | "weekly_performance"
  | "supplier_quote"
  | "appointment_reminder"
  | "churn_signal";

// ===== COLUMN MAPPING (Step 4 – after DataFork) =====
export interface ColumnMappingDecision {
  sourceColumn: string;
  bluField: string | null; // null = ignored
  status: "auto" | "confirmed" | "ignored" | "flagged";
  confidence?: number; // 0-100, present on auto rows
}

export interface OnboardingState {
  // Pre-auth persona (v2)
  persona: Persona;
  painPoint: PainPoint;
  teamSize: TeamSize;
  firstApprovalDecision: FirstApprovalDecision;
  // Step 0 – Auth
  authMethod: "google" | "email" | null;
  nome: string;
  email: string;
  // Step 2 – Business DNA
  empresa: string;
  vertical: Vertical;
  porte: string;
  website: string;
  primaryFocus: PrimaryFocus;
  // Step 3 – Data fork
  dataPath: DataPath;
  systems: string[]; // shopify, vtex, bigquery, postgres, mysql, api
  csvUploaded: boolean;
  googleDriveConnected: boolean;
  // Step 4 – Column mapping
  columnMapping: ColumnMappingDecision[];
  // Step 5 – Agents
  agents: string[];
  // Step 6 – Command rules
  approvalTasks: ApprovalTaskId[]; // tasks that require human approval
  alwaysRequireApproval: boolean;
  routines: RoutineId[]; // built-in routines to activate
  notifyChannel: NotifyChannel;
  kpiSelections: Partial<Record<KpiDimension, string[]>>;
}

const DEFAULT: OnboardingState = {
  persona: null,
  painPoint: null,
  teamSize: null,
  firstApprovalDecision: null,
  authMethod: null,
  nome: "",
  email: "",
  empresa: "",
  vertical: null,
  porte: "",
  website: "",
  primaryFocus: null,
  dataPath: null,
  systems: [],
  csvUploaded: false,
  googleDriveConnected: false,
  columnMapping: [],
  agents: [],
  approvalTasks: ["supplier_order", "make_payment", "update_prices"],
  alwaysRequireApproval: true,
  routines: ["daily_sales_digest", "low_stock_alert", "stale_lead_followup"],
  notifyChannel: "email",
  kpiSelections: {},
};

const STORAGE_KEY = "blu.onboarding.v1";

function load(): OnboardingState {
  if (typeof window === "undefined") return DEFAULT;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT;
    return { ...DEFAULT, ...JSON.parse(raw) };
  } catch {
    return DEFAULT;
  }
}

function save(state: OnboardingState) {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // ignore
  }
}

export function useOnboarding() {
  const [state, setState] = useState<OnboardingState>(() => load());
  // Tracks which keys have been changed locally since the last server flush,
  // so we only PATCH the delta instead of the full blob.
  const pendingPatchRef = useRef<Partial<OnboardingState>>({});
  const flushTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hydratedRef = useRef(false);

  // Persist to localStorage on every change (fast path, offline fallback).
  useEffect(() => {
    save(state);
  }, [state]);

  // Hydrate from server once per mount, when a session is available.
  // Server state is authoritative; we merge it on top of the local default
  // so steps that haven't been touched yet keep their defaults.
  useEffect(() => {
    let cancelled = false;

    async function hydrate() {
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session || cancelled) return;

      const record = await getOnboardingState();
      if (cancelled || !record) return;

      const serverPartial = record.onboarding_state ?? {};
      if (!serverPartial || Object.keys(serverPartial).length === 0) return;

      setState((prev) => ({ ...prev, ...serverPartial }));
      hydratedRef.current = true;
    }

    void hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  // Flush the accumulated patch to the server (debounced 300ms).
  const scheduleFlush = useCallback(() => {
    if (flushTimerRef.current) clearTimeout(flushTimerRef.current);
    flushTimerRef.current = setTimeout(() => {
      const patch = pendingPatchRef.current;
      pendingPatchRef.current = {};
      flushTimerRef.current = null;
      if (!patch || Object.keys(patch).length === 0) return;
      // Fire-and-forget: localStorage already holds the canonical copy,
      // and failures are logged inside the service. UI stays responsive.
      void patchOnboardingState(patch).catch(() => {
        /* swallowed — see service logs */
      });
    }, 300);
  }, []);

  // Flush any pending patch when the tab is hidden / unloaded so we don't
  // lose in-flight edits if the user closes the wizard.
  useEffect(() => {
    const flushNow = () => {
      if (flushTimerRef.current) {
        clearTimeout(flushTimerRef.current);
        flushTimerRef.current = null;
      }
      const patch = pendingPatchRef.current;
      pendingPatchRef.current = {};
      if (patch && Object.keys(patch).length > 0) {
        void patchOnboardingState(patch).catch(() => {
          /* swallowed */
        });
      }
    };
    window.addEventListener("beforeunload", flushNow);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") flushNow();
    });
    return () => {
      window.removeEventListener("beforeunload", flushNow);
    };
  }, []);

  const update = useCallback(
    (patch: Partial<OnboardingState>) => {
      setState((prev) => ({ ...prev, ...patch }));
      pendingPatchRef.current = { ...pendingPatchRef.current, ...patch };
      scheduleFlush();
    },
    [scheduleFlush],
  );

  const reset = useCallback(() => {
    setState(DEFAULT);
    pendingPatchRef.current = {};
    if (flushTimerRef.current) {
      clearTimeout(flushTimerRef.current);
      flushTimerRef.current = null;
    }
    try {
      window.localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  return { state, update, reset };
}

// ========== AGENT SUGGESTIONS (vertical + path aware) ==========
export interface AgentOption {
  id: string;
  name: string;
  value: string;
  color: string;
}

export const ALL_AGENTS: AgentOption[] = [
  { id: "analytics", name: "Agente de Analytics", value: "Transforma dados em respostas e dashboards.", color: "#3b82f6" },
  { id: "inventory", name: "Agente de Estoque", value: "Alerta de reposição e cotação automática.", color: "#f97316" },
  { id: "marketing", name: "Agente de Marketing", value: "Campanhas e performance sempre ajustadas.", color: "#ec4899" },
  { id: "crm", name: "Agente de CRM", value: "Nenhum cliente esquecido. Follow-up automático.", color: "#a855f7" },
  { id: "scheduling", name: "Agente de Agendamento", value: "Agenda cheia, conflitos resolvidos.", color: "#22d3ee" },
  { id: "projects", name: "Agente de Projetos", value: "Tarefas, prazos e responsáveis no radar.", color: "#10b981" },
  { id: "documents", name: "Agente de Documentos", value: "Organiza contratos, notas e anexos.", color: "#eab308" },
  { id: "finance", name: "Agente Financeiro", value: "Contas a pagar, receber e fluxo de caixa.", color: "#60a5fa" },
];

export function suggestAgents(state: OnboardingState): string[] {
  const v = state.vertical;
  const p = state.dataPath;
  if (v === "ecommerce") return ["inventory", "marketing", "analytics"];
  if (v === "servicos") return ["crm", "scheduling", "projects"];
  if (v === "industria") return ["inventory", "finance", "analytics"];
  if (v === "saude") return ["scheduling", "crm", "documents"];
  if (v === "educacao") return ["crm", "scheduling", "documents"];
  if (v === "financeiro") return ["finance", "documents", "analytics"];
  if (v === "agro") return ["inventory", "finance", "analytics"];
  if (p === "files") return ["analytics", "documents"];
  if (p === "systems") return ["analytics", "finance"];
  return ["analytics", "crm", "documents"];
}
