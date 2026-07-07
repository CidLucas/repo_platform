import React from 'react'

interface FieldProps {
  label: string
  error?: string
  warning?: string
  success?: string
  hint?: string
  children: React.ReactNode
  required?: boolean
  className?: string
  style?: React.CSSProperties
}

export default function Field({
  label,
  error,
  warning,
  success,
  hint,
  children,
  required,
  className,
  style,
}: FieldProps): React.JSX.Element {
  const valState = error ? 'error' : warning ? 'warning' : success ? 'success' : ''
  const child = React.Children.only(children) as React.ReactElement

  const enhanced = React.cloneElement(child, {
    className: [child.props.className, 'input', valState].filter(Boolean).join(' '),
  })

  return (
    <div className={`field${className ? ' ' + className : ''}`} style={style}>
      <label>
        {label}
        {required && <span style={{ color: 'var(--urg)', marginLeft: 3 }}>*</span>}
      </label>
      {enhanced}
      {(error || warning || success) && (
        <div className={`val-msg ${valState}`}>
          {error && '✕ '}
          {warning && '⚠ '}
          {success && '✓ '}
          {error || warning || success}
        </div>
      )}
      {hint && !error && !warning && (
        <div style={{ fontSize: 10.5, color: 'var(--mu)', marginTop: 3 }}>{hint}</div>
      )}
    </div>
  )
}
