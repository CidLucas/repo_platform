// Re-export types and context from the canonical @blu/auth package.
// This file adds blu_app-specific callbacks: telemetry identification and calendar token capture.
export { AuthContext } from '@blu/auth'
export type { AuthContextValue } from '@blu/auth'

import type { ReactNode } from 'react'
import { AuthProvider as BluAuthProvider } from '@blu/auth'
import { captureCalendarToken } from '@/api/agenda'
import { identifyTelemetryUser, resetTelemetry } from '@/lib/telemetry'

export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <BluAuthProvider
      onCalendarToken={captureCalendarToken}
      onIdentifyUser={identifyTelemetryUser}
      onResetUser={resetTelemetry}
    >
      {children}
    </BluAuthProvider>
  )
}
