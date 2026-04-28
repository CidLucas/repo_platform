/**
 * Onboarding Service — Context 2.0 persistence via merge_onboarding_state RPC
 *
 * Reads company_profile, team_structure, policies from clientes_blu.
 * Writes via merge_onboarding_state() for race-free JSONB patch semantics.
 *
 * NOTE: current_moment was removed from clientes_blu (schema baseline 2026-04-28).
 */

import { supabase } from '../lib/supabase';
import type {
    CompanyProfile,
    TeamStructure,
    Policies,
    OnboardingData,
} from '../types/onboarding';

const TABLE = 'clientes_blu';
const CONTEXT_COLUMNS = 'company_profile, team_structure, policies';

/**
 * Fetch existing context sections for the current client (RLS scoped).
 */
export async function getClientContext(
    _clientId: string
): Promise<OnboardingData | null> {
    const { data, error } = await supabase
        .from(TABLE)
        .select(CONTEXT_COLUMNS)
        .maybeSingle();

    if (error || !data) {
        console.error('Failed to fetch client context:', error);
        return null;
    }

    return {
        company_profile: data.company_profile ?? {},
        team_structure: data.team_structure ?? {},
        policies: data.policies ?? {},
    } as OnboardingData;
}

/**
 * Persist onboarding sections via merge_onboarding_state RPC.
 * Uses JSONB merge semantics — safe for concurrent callers.
 */
export async function saveOnboardingData(
    _clientId: string,
    sections: {
        company_profile?: CompanyProfile;
        team_structure?: TeamStructure;
        policies?: Policies;
    }
): Promise<{ success: boolean; error?: string }> {
    const payload: Record<string, unknown> = {};
    if (sections.company_profile !== undefined) payload.company_profile = sections.company_profile;
    if (sections.team_structure !== undefined) payload.team_structure = sections.team_structure;
    if (sections.policies !== undefined) payload.policies = sections.policies;

    if (Object.keys(payload).length === 0) {
        return { success: true };
    }

    const { error } = await supabase.rpc('merge_onboarding_state', {
        p_patch: payload,
    });

    if (error) {
        console.error('Failed to save onboarding data:', error);
        return { success: false, error: error.message };
    }

    return { success: true };
}
