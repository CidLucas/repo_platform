import { useEffect, useState, useCallback } from 'react';
import { supabase } from '../lib/supabase';
import { useAuth } from './useAuth';

/**
 * A connector that needs the user's attention on the column mapping page.
 *
 * Reasons (in priority order):
 *  - `discovery_pending`: discovery never produced source_columns yet.
 *  - `needs_review`: schema match left columns in `needs_review_columns`.
 *  - `unmapped`: columns in `unmapped_columns` and not yet synced.
 *  - `awaiting_sync`: mapping looks complete but sync hasn't started.
 */
export type MappingReviewReason =
    | 'discovery_pending'
    | 'needs_review'
    | 'unmapped'
    | 'awaiting_sync';

export interface ConnectorNeedingReview {
    credentialId: number;
    nomeServico: string;
    tipoServico: string;
    reason: MappingReviewReason;
    needsReviewCount: number;
    unmappedCount: number;
}

interface CredentialRow {
    id: number;
    nome_servico: string | null;
    tipo_servico: string | null;
}

interface DataSourceRow {
    credential_id: number | null;
    source_columns: unknown;
    column_mapping: unknown;
    unmapped_columns: unknown;
    needs_review_columns: unknown;
    sync_status: string | null;
}

function arrLen(value: unknown): number {
    if (Array.isArray(value)) return value.length;
    if (value && typeof value === 'object') return Object.keys(value as object).length;
    return 0;
}

function hasSourceColumns(value: unknown): boolean {
    return arrLen(value) > 0;
}

/**
 * Returns the list of credentials for the current client whose column mapping
 * requires user attention. Used to render warning banners on the dashboard
 * home page and on the data sources page.
 */
export function useConnectorsNeedingReview() {
    const { clientId } = useAuth();
    const [items, setItems] = useState<ConnectorNeedingReview[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const refetch = useCallback(async () => {
        if (!clientId) return;
        setLoading(true);
        setError(null);
        try {
            const { data: credentials, error: credErr } = await supabase
                .from('credencial_servico_externo')
                .select('id, nome_servico, tipo_servico')
                .eq('client_id', clientId);
            if (credErr) throw credErr;
            const creds = (credentials || []) as CredentialRow[];
            if (creds.length === 0) {
                setItems([]);
                return;
            }

            const credIds = creds.map((c) => c.id);
            const { data: sources, error: srcErr } = await supabase
                .from('client_data_sources')
                .select(
                    'credential_id, source_columns, column_mapping, unmapped_columns, needs_review_columns, sync_status',
                )
                .in('credential_id', credIds);
            if (srcErr) throw srcErr;

            const sourceByCred = new Map<number, DataSourceRow>();
            (sources || []).forEach((row) => {
                const r = row as DataSourceRow;
                if (r.credential_id != null) sourceByCred.set(r.credential_id, r);
            });

            const result: ConnectorNeedingReview[] = [];
            for (const cred of creds) {
                const ds = sourceByCred.get(cred.id);
                const base = {
                    credentialId: cred.id,
                    nomeServico: cred.nome_servico || `Credencial #${cred.id}`,
                    tipoServico: cred.tipo_servico || '',
                };

                if (!ds || !hasSourceColumns(ds.source_columns)) {
                    result.push({
                        ...base,
                        reason: 'discovery_pending',
                        needsReviewCount: 0,
                        unmappedCount: 0,
                    });
                    continue;
                }

                const needsReviewCount = arrLen(ds.needs_review_columns);
                const unmappedCount = arrLen(ds.unmapped_columns);
                const status = (ds.sync_status || '').toLowerCase();
                const synced = status === 'completed' || status === 'success';

                if (needsReviewCount > 0) {
                    result.push({
                        ...base,
                        reason: 'needs_review',
                        needsReviewCount,
                        unmappedCount,
                    });
                } else if (unmappedCount > 0 && !synced) {
                    result.push({
                        ...base,
                        reason: 'unmapped',
                        needsReviewCount,
                        unmappedCount,
                    });
                } else if (
                    !synced &&
                    arrLen(ds.column_mapping) > 0 &&
                    (status === '' || status === 'pending' || status === 'awaiting_review')
                ) {
                    result.push({
                        ...base,
                        reason: 'awaiting_sync',
                        needsReviewCount,
                        unmappedCount,
                    });
                }
            }

            setItems(result);
        } catch (err) {
            console.error('useConnectorsNeedingReview error:', err);
            setError(err instanceof Error ? err.message : 'Erro ao carregar credenciais');
        } finally {
            setLoading(false);
        }
    }, [clientId]);

    useEffect(() => {
        void refetch();
    }, [refetch]);

    return { items, loading, error, refetch };
}
