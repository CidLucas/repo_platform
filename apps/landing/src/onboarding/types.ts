/**
 * Onboarding types — Context 2.0 shapes + landing wizard contracts.
 *
 * These mirror the dashboard copy at
 *   apps/vizu_dashboard/src/types/onboarding.ts
 * which itself mirrors the Pydantic schemas in
 *   libs/vizu_models/src/vizu_models/context_schemas.py
 *
 * We duplicate rather than cross-import because Vite / tsconfig in each
 * app only includes `./src`. If a third surface needs these, lift them
 * to `apps/shared/onboarding-types.ts` and wire path aliases in both
 * apps' tsconfig + vite configs.
 */

import type { OnboardingState } from "./state";

// ===== COMPANY PROFILE =====
export interface CompanyProfile {
  legal_name?: string | null;
  trading_name?: string | null;
  tagline?: string | null;
  business_archetype?: string | null;
  industry?: string | null;
  mission?: string | null;
  vision?: string | null;
  core_values: string[];
  founding_year?: number | null;
  headquarters_city?: string | null;
  employee_count_range?: string | null;
}

// ===== CURRENT MOMENT =====
export interface CurrentMoment {
  stage?: string | null;
  current_priorities: string[];
  current_challenges: string[];
  recent_wins: string[];
  key_metrics: Record<string, string | number>;
  active_campaigns: string[];
  upcoming_events: string[];
  period?: string | null;
  last_updated?: string | null;
}

// ===== TEAM =====
export interface TeamMember {
  role: string;
  name?: string | null;
  responsibility?: string | null;
  contact_preference?: string | null;
}

export interface TeamStructure {
  key_contacts: TeamMember[];
  main_contact?: string | null;
  escalation_path: string[];
  communication_channels: Record<string, string>;
  headquarters?: string | null;
  operational_locations: string[];
  business_hours?: string | null;
}

// ===== POLICIES =====
export interface Policies {
  communication_rules: string[];
  tone_with_partners?: string | null;
  operational_limits: string[];
  approval_requirements: {
    autonomous: string[];
    requires_approval: string[];
  };
  red_flags: string[];
  compliance_notes?: string | null;
  data_handling_rules: string[];
}

// ===== AGGREGATE =====
export interface OnboardingData {
  company_profile: CompanyProfile;
  current_moment: CurrentMoment;
  team_structure: TeamStructure;
  policies: Policies;
}

// ===== SERVER STATE RECORD =====

/** Shape of the row returned by `getOnboardingState`. */
export interface OnboardingStateRecord {
  onboarding_state: Partial<OnboardingState>;
  onboarding_completed_at: string | null;
}

// ===== BOOTSTRAP (Phase 4 edge function contract) =====

/**
 * Payload sent to the `onboarding-bootstrap` edge function at LaunchPad.
 * Mirrors the wizard state so the server can re-validate end-to-end.
 */
export type BootstrapPayload = OnboardingState;

export interface BootstrapResult {
  client_id: string;
  agents: number;
  routines: number;
  prompts_seeded: number;
}
