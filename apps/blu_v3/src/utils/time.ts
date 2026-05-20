export function snoozeUntil(hours = 2): string {
  return new Date(Date.now() + hours * 60 * 60 * 1000).toISOString()
}
