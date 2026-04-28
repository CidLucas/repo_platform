/**
 * Hook for column matching via Supabase Edge Function.
 * Calls the match-columns Edge Function that uses fuzzy string matching
 * to map source columns to canonical schema columns.
 */

import { useState, useCallback } from 'react';
import { supabase } from '../lib/supabase';

export type SchemaType = 'invoices' | 'vendas' | 'products' | 'orders' | 'customers' | 'inventory' | 'categories' | 'fato_transacoes';

export interface MatchCandidate {
    canonical: string;
    confidence: number;
}

export interface NeedsReviewItem {
    source: string;
    candidates: MatchCandidate[];
}

export interface MatchResult {
    source_column: string;
    canonical_column: string | null;
    confidence: number;
    auto_matched: boolean;
}

export interface SchemaMatchResult {
    matched: Record<string, string>;
    unmatched: string[];
    confidence_scores: Record<string, number>;
    needs_review: NeedsReviewItem[];
    details: MatchResult[];
    detected_context?: 'customer' | 'supplier' | 'product' | 'neutral';
}

export interface UseColumnMatchingResult {
    matchColumns: (sourceColumns: string[], schemaType?: SchemaType) => Promise<SchemaMatchResult>;
    result: SchemaMatchResult | null;
    loading: boolean;
    error: string | null;
    reset: () => void;
}

const EDGE_FUNCTION_URL = import.meta.env.VITE_SUPABASE_URL
    ? `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/match-columns`
    : 'http://localhost:54321/functions/v1/match-columns';

export function useColumnMatching(): UseColumnMatchingResult {
    const [result, setResult] = useState<SchemaMatchResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const matchColumns = useCallback(async (
        sourceColumns: string[],
        schemaType: SchemaType = 'invoices'
    ): Promise<SchemaMatchResult> => {
        setLoading(true);
        setError(null);

        try {
            // Get auth token for Edge Function call
            const { data: sessionData } = await supabase.auth.getSession();
            const token = sessionData?.session?.access_token;

            const response = await fetch(EDGE_FUNCTION_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({
                    source_columns: sourceColumns,
                    schema_type: schemaType,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Falha ao mapear colunas');
            }

            const matchResult: SchemaMatchResult = await response.json();
            setResult(matchResult);
            return matchResult;
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Erro desconhecido';
            setError(errorMessage);
            throw err;
        } finally {
            setLoading(false);
        }
    }, []);

    const reset = useCallback(() => {
        setResult(null);
        setError(null);
    }, []);

    return {
        matchColumns,
        result,
        loading,
        error,
        reset,
    };
}

/**
 * Helper function to merge user-selected mappings with auto-matched ones.
 * Used after user reviews and confirms the column mapping.
 */
export function buildFinalColumnMapping(
    matchResult: SchemaMatchResult,
    userSelections: Record<string, string>,
    ignoredColumns: string[]
): Record<string, string> {
    const finalMapping: Record<string, string> = {};

    // Add auto-matched columns
    for (const [source, canonical] of Object.entries(matchResult.matched)) {
        if (!ignoredColumns.includes(source)) {
            finalMapping[source] = canonical;
        }
    }

    // Add user selections (overwrites auto-matched if user changed it)
    for (const [source, canonical] of Object.entries(userSelections)) {
        if (canonical && !ignoredColumns.includes(source)) {
            finalMapping[source] = canonical;
        }
    }

    return finalMapping;
}
