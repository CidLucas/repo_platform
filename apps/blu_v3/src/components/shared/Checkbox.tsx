import React, { useEffect, useRef } from 'react'

interface CheckboxProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
  indeterminate?: boolean
  id?: string
}

export default function Checkbox({
  checked,
  onChange,
  label,
  disabled,
  indeterminate,
  id,
}: CheckboxProps): React.JSX.Element {
  const uid = id ?? `cb-${Math.random().toString(36).slice(2, 9)}`
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.indeterminate = indeterminate ?? false
    }
  }, [indeterminate])

  return (
    <label
      htmlFor={uid}
      className={`checkbox${disabled ? ' disabled' : ''}`}
    >
      <input
        ref={inputRef}
        id={uid}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={e => onChange(e.target.checked)}
      />
      <span className="checkbox-box" />
      {label && <span>{label}</span>}
    </label>
  )
}
