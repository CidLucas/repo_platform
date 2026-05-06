import { useAppStore } from '../../store/appStore'

export default function Topbar() {
  const { breadcrumb, go } = useAppStore()
  const isHome = breadcrumb === 'Bom dia, Carlos ☀️'

  return (
    <header className="topbar">
      <div className="logo">
        <div className="logo-mark">B</div>
        <span className="logo-name">blu</span>
      </div>
      <div className="topbar-mid">
        {isHome ? (
          <span id="bc">Bom dia, Carlos ☀️</span>
        ) : (
          <span id="bc">
            <span
              style={{ cursor: 'pointer', color: 'var(--mu)' }}
              onClick={() => go('home', 'Início')}
            >
              Início
            </span>
            {' '}
            <span style={{ color: 'var(--mu)', opacity: 0.5 }}>/</span>
            {' '}
            {breadcrumb}
          </span>
        )}
      </div>
      <div className="topbar-end">
        <button className="ibtn">
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" />
          </svg>
        </button>
        <button className="ibtn">
          <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          <span className="rdot" />
        </button>
        <div className="av">CL</div>
      </div>
    </header>
  )
}
