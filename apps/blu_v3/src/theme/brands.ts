/**
 * Third-party brand colors.
 *
 * These are the ONLY sanctioned raw color literals outside the design-system
 * tokens (`--ac`, `--ok`, `--att`, `--chart-*`, …). They are the official brand
 * identity colors of external services and intentionally DO NOT participate in
 * the light/dark theme system — a Slack mark is aubergine in both themes.
 *
 * Anything that is a UI color (surfaces, text, semantic status, categorical
 * charts) must use a CSS token, never a value from here.
 */
export const BRAND = {
  google: '#4285F4',
  asana: '#F06A6A',
  clickup: '#7B68EE',
  linear: '#5E6AD2',
  slack: {
    aubergine: '#E01E5A',
    blue: '#36C5F0',
    green: '#2EB67D',
    yellow: '#ECB22E',
  },
  monday: {
    red: '#FF3D57',
    yellow: '#FFCB00',
    green: '#00CA72',
  },
} as const
