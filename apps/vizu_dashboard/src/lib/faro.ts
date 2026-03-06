/**
 * Grafana Faro — Frontend Observability
 *
 * Captures browser errors, unhandled promise rejections, console errors,
 * web vitals, and OpenTelemetry traces. All data is sent to the Grafana
 * Cloud OTLP gateway (same endpoint used by the backend services).
 *
 * The SDK is initialized lazily at app startup via `initFaro()`.
 * If VITE_GRAFANA_OTLP_ENDPOINT is not set the call is a no-op.
 */

import {
    initializeFaro,
    getWebInstrumentations,
    type Faro,
} from '@grafana/faro-web-sdk';
import { TracingInstrumentation } from '@grafana/faro-web-tracing';
import { OtlpHttpTransport } from '@grafana/faro-transport-otlp-http';

let faro: Faro | null = null;

/**
 * Initialize the Grafana Faro SDK.
 * Safe to call multiple times — will only initialise once.
 *
 * Environment variables (set at build time via Vite):
 *   VITE_GRAFANA_OTLP_ENDPOINT   – Grafana Cloud OTLP gateway base URL
 *                                   e.g. https://otlp-gateway-prod-sa-east-1.grafana.net/otlp
 *   VITE_GRAFANA_OTLP_BASIC_AUTH – Base64-encoded "instanceId:apiToken" for Basic auth
 *   VITE_FARO_APP_NAME           – Application name label (default: vizu_dashboard)
 */
export function initFaro(): Faro | null {
    const otlpEndpoint = import.meta.env.VITE_GRAFANA_OTLP_ENDPOINT;
    const basicAuth = import.meta.env.VITE_GRAFANA_OTLP_BASIC_AUTH;

    if (!otlpEndpoint) {
        console.debug('[faro] VITE_GRAFANA_OTLP_ENDPOINT not set — Faro disabled');
        return null;
    }

    if (faro) return faro;

    // Build OTLP v1 endpoints from base URL (strip trailing slash)
    const base = otlpEndpoint.replace(/\/+$/, '');
    const logsURL = `${base}/v1/logs`;
    const tracesURL = `${base}/v1/traces`;

    // Build auth headers (same credentials as backend OTEL exporter)
    const headers: Record<string, string> = {};
    if (basicAuth) {
        headers['Authorization'] = `Basic ${basicAuth}`;
    }

    try {
        faro = initializeFaro({
            app: {
                name: import.meta.env.VITE_FARO_APP_NAME || 'vizu_dashboard',
                version: '1.2.0',
                environment: import.meta.env.MODE, // 'development' | 'production'
            },
            instrumentations: [
                // Core web instrumentations: errors, console, web-vitals, performance
                ...getWebInstrumentations({
                    captureConsole: true,
                }),
                // OpenTelemetry browser tracing (fetch/XHR auto-instrumentation)
                new TracingInstrumentation(),
            ],
            transports: [
                new OtlpHttpTransport({
                    logsURL,
                    tracesURL,
                    requestOptions: { headers },
                }),
            ],
        });

        console.info('[faro] Initialized — sending telemetry via OTLP to', base);
    } catch (err) {
        console.warn('[faro] Failed to initialize:', err);
    }

    return faro;
}

export { faro };
