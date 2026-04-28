/**
 * Onboarding types — mirrors Context 2.0 Pydantic schemas
 * from libs/blu_models/src/blu_models/context_schemas.py
 *
 * NOTE: current_moment was removed from clientes_blu (schema baseline 2026-04-28).
 * It was ephemeral data that never belonged in persistent storage.
 */

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
    team_structure: TeamStructure;
    policies: Policies;
}

// ===== DEFAULTS =====
export const emptyCompanyProfile: CompanyProfile = {
    legal_name: null,
    trading_name: null,
    tagline: null,
    business_archetype: null,
    industry: null,
    mission: null,
    vision: null,
    core_values: [],
    founding_year: null,
    headquarters_city: null,
    employee_count_range: null,
};

export const emptyTeamStructure: TeamStructure = {
    key_contacts: [],
    main_contact: null,
    escalation_path: [],
    communication_channels: {},
    headquarters: null,
    operational_locations: [],
    business_hours: null,
};

export const emptyPolicies: Policies = {
    communication_rules: [],
    tone_with_partners: null,
    operational_limits: [],
    approval_requirements: { autonomous: [], requires_approval: [] },
    red_flags: [],
    compliance_notes: null,
    data_handling_rules: [],
};

export const emptyOnboardingData: OnboardingData = {
    company_profile: emptyCompanyProfile,
    team_structure: emptyTeamStructure,
    policies: emptyPolicies,
};
