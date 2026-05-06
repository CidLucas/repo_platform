import { useState, useCallback } from 'react'

type DrawerSide = 'left' | 'right' | null

interface UseDrawerReturn {
  openDrawer: DrawerSide
  isLeftOpen: boolean
  isRightOpen: boolean
  openLeft: () => void
  openRight: () => void
  close: () => void
  toggle: (side: 'left' | 'right') => void
}

/**
 * Manages which mobile bottom-sheet drawer is open.
 * Only one drawer can be open at a time.
 */
export function useDrawer(): UseDrawerReturn {
  const [openDrawer, setOpenDrawer] = useState<DrawerSide>(null)

  const openLeft = useCallback(() => setOpenDrawer('left'), [])
  const openRight = useCallback(() => setOpenDrawer('right'), [])
  const close = useCallback(() => setOpenDrawer(null), [])

  const toggle = useCallback((side: 'left' | 'right') => {
    setOpenDrawer((prev) => (prev === side ? null : side))
  }, [])

  return {
    openDrawer,
    isLeftOpen: openDrawer === 'left',
    isRightOpen: openDrawer === 'right',
    openLeft,
    openRight,
    close,
    toggle,
  }
}
