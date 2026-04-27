import posthog from 'posthog-js';

let initialized = false;

const getDistinctId = (): string | undefined => {
  if (typeof window === 'undefined') return undefined;
  return window.localStorage.getItem('vizu.telemetry.distinct_id') ?? undefined;
};

const setDistinctId = (id: string): void => {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem('vizu.telemetry.distinct_id', id);
};

export const initTelemetry = (): void => {
  if (initialized || typeof window === 'undefined') return;

  const key = import.meta.env.VITE_POSTHOG_KEY;
  if (!key) {
    return;
  }

  const host = import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com';

  posthog.init(key, {
    api_host: host,
    person_profiles: 'identified_only',
    capture_pageview: false,
    capture_pageleave: true,
    persistence: 'localStorage+cookie',
    loaded: () => {
      const existing = getDistinctId();
      if (!existing) {
        const generated = posthog.get_distinct_id();
        if (generated) setDistinctId(generated);
      }
    },
  });

  initialized = true;
};

export const identifyTelemetryUser = (distinctId: string, properties?: Record<string, unknown>): void => {
  if (!initialized) return;
  posthog.identify(distinctId, properties);
  setDistinctId(distinctId);
};

export const captureTelemetryEvent = (
  event: string,
  properties?: Record<string, unknown>,
): void => {
  if (!initialized) return;
  posthog.capture(event, properties);
};

export const resetTelemetry = (): void => {
  if (!initialized) return;
  posthog.reset();
};
