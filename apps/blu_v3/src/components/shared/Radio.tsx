import React from 'react'

interface RadioProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  disabled?: boolean
  id?: string
  name?: string
}

export default function Radio({
  checked,
  onChange,
  label,
  disabled,
  id,
  name,
}: RadioProps): React.JSX.Element {
  const uid = id ?? `rd-${Math.random().toString(36).slice(2, 9)}`

  return (
    <label
      htmlFor={uid}
      className={`radio${disabled ? ' disabled' : ''}`}
    >
      <input
        id={uid}
        type="radio"
        checked={checked}
        disabled={disabled}
        name={name}
        onChange={e => onChange(e.target.checked)}
      />
      <span className="radio-circle" />
      {label && <span>{label}</span>}
    </label>
  )
}
