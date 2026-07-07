import { useCallback, useEffect, useRef, useState } from 'react'
import { useAuth } from '@blu/auth'

const MIN_W = 240
const MAX_W = 400
const DEFAULT_W = 260

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v))
}

function readStored(key: string): number {
  try {
    const raw = localStorage.getItem(key)
    if (raw) {
      const n = parseInt(raw, 10)
      if (!isNaN(n)) return clamp(n, MIN_W, MAX_W)
    }
  } catch {
    // localStorage may be unavailable; fall back to DEFAULT_W
  }
  return DEFAULT_W
}

function applyWidth(w: number) {
  document.documentElement.style.setProperty('--rcol-w', `${w}px`)
}

export function useRColResize() {
  const { clientId } = useAuth()
  const [isDragging, setIsDragging] = useState(false)
  // Ref so the mouseup closure always sees the current scoped key without re-binding
  const storageKeyRef = useRef<string | null>(null)

  useEffect(() => {
    storageKeyRef.current = clientId ? `blu-rcol-w:${clientId}` : null
    applyWidth(clientId ? readStored(`blu-rcol-w:${clientId}`) : DEFAULT_W)
  }, [clientId])

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    const startX = e.clientX
    const startW = parseInt(
      getComputedStyle(document.documentElement).getPropertyValue('--rcol-w'),
      10
    ) || DEFAULT_W

    setIsDragging(true)

    function onMove(ev: MouseEvent) {
      const delta = startX - ev.clientX
      applyWidth(clamp(startW + delta, MIN_W, MAX_W))
    }

    function onUp() {
      setIsDragging(false)
      const finalW = parseInt(
        getComputedStyle(document.documentElement).getPropertyValue('--rcol-w'),
        10
      )
      const key = storageKeyRef.current
      try { if (key) localStorage.setItem(key, String(finalW)) } catch {
        // localStorage may be unavailable; width is still applied via CSS var
      }
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [])

  return { handleRef: useRef<HTMLDivElement>(null), isDragging, onMouseDown }
}
