import { useRColResize } from '../../hooks/useRColResize'

export default function RColResizeHandle() {
  const { handleRef, isDragging, onMouseDown } = useRColResize()

  return (
    <div
      ref={handleRef}
      className={`rcol-resize-handle${isDragging ? ' dragging' : ''}`}
      onMouseDown={onMouseDown}
      title="Arraste para redimensionar"
    />
  )
}
