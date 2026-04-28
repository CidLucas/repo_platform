/**
 * Tenant Context — Feature gating based on client tier.
 *
 * Tiers: FREE | BASIC | SME | PREMIUM | ENTERPRISE | ADMIN
 *
 * Initial gating strategy:
 * - FREE: everything visible EXCEPT the agent chat
 * - BASIC: agent enabled with SQL tool
 * - SME / PREMIUM / ENTERPRISE / ADMIN: all features
 */
import React, { createContext, useContext, useMemo, ReactNode } from 'react';
import { useAuth } from '../hooks/useAuth';

export const TIERS = ['FREE', 'BASIC', 'SME', 'PREMIUM', 'ENTERPRISE', 'ADMIN'] as const;
export type TierType = (typeof TIERS)[number];

const TIER_ORDER: Record<TierType, number> = {
    FREE: 0,
    BASIC: 1,
    SME: 2,
    PREMIUM: 3,
    ENTERPRISE: 4,
    ADMIN: 5,
};

export interface TenantFeatures {
    /** Whether the user can access the AI agent/chat */
    canUseAgent: boolean;
    /** Whether the agent has access to the SQL tool */
    canUseSqlTool: boolean;
    /** Whether the user can export data */
    canExportData: boolean;
    /** Whether the geographic map card is shown */
    showGeographicMap: boolean;
    /** Whether the insights carousel graphs are shown */
    showInsightCarousel: boolean;
    /** Whether KPI accordion is shown in performance card modal */
    showKpiAccordion: boolean;
    /** Max items in list card (3 for free, 4 for others) */
    maxListCardItems: number;
}

export interface TenantConfig {
    tier: TierType;
    features: TenantFeatures;
}

const TenantContext = createContext<TenantConfig | null>(null);

function tierAtLeast(current: TierType, minimum: TierType): boolean {
    return TIER_ORDER[current] >= TIER_ORDER[minimum];
}

function normalizeTier(raw: string | null | undefined): TierType {
    if (!raw) return 'FREE';
    const upper = raw.toUpperCase() as TierType;
    return TIERS.includes(upper) ? upper : 'FREE';
}

function buildFeatures(tier: TierType): TenantFeatures {
    return {
        // FREE: no agent. BASIC+: agent enabled
        canUseAgent: tierAtLeast(tier, 'BASIC'),
        // BASIC+: SQL tool available
        canUseSqlTool: tierAtLeast(tier, 'BASIC'),
        // All tiers can export for now (future gating)
        canExportData: true,
        // All tiers see the map for now
        showGeographicMap: true,
        // All tiers see insight carousel for now
        showInsightCarousel: true,
        // All tiers see KPI accordion for now
        showKpiAccordion: true,
        // All tiers get 4 list card items for now
        maxListCardItems: 4,
    };
}

export const TenantProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const auth = useAuth();
    const tier = normalizeTier(auth.tier);

    const config = useMemo<TenantConfig>(
        () => ({ tier, features: buildFeatures(tier) }),
        [tier],
    );

    return (
        <TenantContext.Provider value={config}>
            {children}
        </TenantContext.Provider>
    );
};

// eslint-disable-next-line react-refresh/only-export-components -- Context exports are intentional
export const useTenant = (): TenantConfig => {
    const ctx = useContext(TenantContext);
    if (!ctx) throw new Error('useTenant must be used within TenantProvider');
    return ctx;
};
