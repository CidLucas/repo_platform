/**
 * Onboarding Service — Direct Supabase CRUD for Context 2.0 sections
 *
 * Reads and writes company_profile, current_moment, team_structure, policies
 * JSONB columns on clientes_vizu via RLS-protected queries.
 */

import { supabase } from '../lib/supabase';
import type {
    CompanyProfile,
    CurrentMoment,
    TeamStructure,
    Policies,
    OnboardingData,
} from '../types/onboarding';

const TABLE = 'clientes_vizu';

const CONTEXT_COLUMNS = 'company_profile, current_moment, team_structure, policies';

/**
 * Fetch existing context sections for a given client.
 */
export async function getClientContext(
    clientId: string
): Promise<OnboardingData | null> {
    const { data, error } = await supabase
        .from(TABLE)
        .select(CONTEXT_COLUMNS)
        .eq('client_id', clientId)
        .single();

    if (error || !data) {
        console.error('Failed to fetch client context:', error);
        return null;
    }

    return {
        company_profile: data.company_profile ?? {},
        current_moment: data.current_moment ?? {},
        team_structure: data.team_structure ?? {},
        policies: data.policies ?? {},
    } as OnboardingData;
}

/**
 * Update all onboarding sections at once.
 */
export async function saveOnboardingData(
    clientId: string,
    sections: {
        company_profile?: CompanyProfile;
        current_moment?: CurrentMoment;
        team_structure?: TeamStructure;
        policies?: Policies;
    }
): Promise<{ success: boolean; error?: string }> {
    const payload: Record<string, unknown> = {};
    if (sections.company_profile !== undefined) payload.company_profile = sections.company_profile;
    if (sections.current_moment !== undefined) payload.current_moment = sections.current_moment;
    if (sections.team_structure !== undefined) payload.team_structure = sections.team_structure;
    if (sections.policies !== undefined) payload.policies = sections.policies;

    if (Object.keys(payload).length === 0) {
        return { success: true };
    }

    const { error } = await supabase
        .from(TABLE)
        .update(payload)
        .eq('client_id', clientId);

    if (error) {
        console.error('Failed to save onboarding data:', error);
        return { success: false, error: error.message };
    }

    return { success: true };
}
