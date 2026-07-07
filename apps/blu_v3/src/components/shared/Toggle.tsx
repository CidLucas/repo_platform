import React from 'react'

interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
  id?: string
}

export default function Toggle({
  checked,
  onChange,
  label,
  disabled,
  id,
}: ToggleProps): React.JSX.Element {
  const uid = id ?? `tog-${Math.random().toString(36).slice(2, 9)}`

  return (
    <label
      htmlFor={uid}
      className={`toggle${disabled ? ' disabled' : ''}`}
    >
      <input
        id={uid}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={e => onChange(e.target.checked)}
      />
      <span className="toggle-track" />
      {label && <span>{label}</span>}
    </label>
  )
}
