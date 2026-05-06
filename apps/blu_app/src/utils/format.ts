/** Format a number as BRL currency, abbreviated for large values */
export function formatBRL(value: number): string {
  if (value >= 1_000_000) {
    return `R$ ${(value / 1_000_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}M`
  }
  if (value >= 1_000) {
    return `R$ ${(value / 1_000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}K`
  }
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

/** Format a percentage */
export function formatPct(value: number): string {
  return `${value.toFixed(1).replace('.', ',')}%`
}

/** Relative time — "Há 2 min", "Há 1 h", "Há 3 dias" */
export function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime()
  const sec = Math.floor(diff / 1000)
  if (sec < 60) return 'Agora'
  const min = Math.floor(sec / 60)
  if (min < 60) return `Há ${min} min`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `Há ${hr} h`
  const days = Math.floor(hr / 24)
  if (days === 1) return 'Ontem'
  return `Há ${days} dias`
}

/** Format time from ISO string as "14:30" */
export function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Format date as "Qua, 30 abr" */
export function formatShortDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString('pt-BR', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
  })
}

/** Weekday abbr: "Dom" | "Seg" | "Ter" | "Qua" | "Qui" | "Sex" | "Sáb" */
const WEEKDAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb']
export function weekdayAbbr(date: Date): string {
  return WEEKDAYS[date.getDay()]
}

/** Returns ISO date string for a Date (YYYY-MM-DD) */
export function toDateStr(date: Date): string {
  return date.toISOString().slice(0, 10)
}

/** Snooze label for a future ISO string */
export function snoozeLabel(isoString: string): string {
  const d = new Date(isoString)
  const now = new Date()
  const diffMs = d.getTime() - now.getTime()
  const diffHr = diffMs / (1000 * 60 * 60)
  if (diffHr < 2) return 'Em 1 hora'
  const diffDays = Math.floor(diffHr / 24)
  if (diffDays === 0) return 'Hoje à tarde'
  if (diffDays === 1) return 'Amanhã'
  return formatShortDate(isoString)
}
