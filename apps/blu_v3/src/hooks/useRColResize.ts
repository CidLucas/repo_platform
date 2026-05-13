import { useCallback, useEffect, useRef, useState } from 'react'

const STORAGE_KEY = 'blu-rcol-w'
const MIN_W = 240
const MAX_W = 400
const DEFAULT_W = 260

function clamp(v: number, min: number, max: number) {
  return Math.max(min, Math.min(max, v))
}

function readStored(): number {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const n = parseInt(raw, 10)
      if (!isNaN(n)) return clamp(n, MIN_W, MAX_W)
    }
  } catch {}
  return DEFAULT_W
}

function applyWidth(w: number) {
  document.documentElement.style.setProperty('--rcol-w', `${w}px`)
}

export function useRColResize() {
  const [isDragging, setIsDragging] = useState(false)
  const handleRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    applyWidth(readStored())
  }, [])

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
      const newW = clamp(startW + delta, MIN_W, MAX_W)
      applyWidth(newW)
    }

    function onUp() {
      setIsDragging(false)
      const finalW = parseInt(
        getComputedStyle(document.documentElement).getPropertyValue('--rcol-w'),
        10
      )
      try { localStorage.setItem(STORAGE_KEY, String(finalW)) } catch {}
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }

    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }, [])

  return { handleRef, isDragging, onMouseDown }
}
