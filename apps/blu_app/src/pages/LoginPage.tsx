import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { supabase } from '@/api/client'

async function signInWithGoogle() {
  await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin },
  })
}

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname ?? '/'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const { error: authError } = await supabase.auth.signInWithPassword({ email, password })

    if (authError) {
      setError('E-mail ou senha incorretos.')
      setLoading(false)
      return
    }

    navigate(from, { replace: true })
  }

  return (
    <div className="min-h-dvh bg-base flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-display-md font-bold text-white mb-1">blu</div>
          <p className="text-body-sm text-gray-300">Você decide. A gente cuida do resto.</p>
        </div>

        {/* Card */}
        <div className="bg-surface border border-border rounded-md shadow-lg p-6">
          <h1 className="text-heading-md text-white mb-6">Entrar</h1>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-body-sm text-gray-200 mb-1">
                E-mail
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-base border border-border rounded text-white text-body px-4 py-3
                  placeholder:text-gray-400 focus:border-blu-500 focus:shadow-glow-blu
                  focus:outline-none transition-colors duration-normal"
                placeholder="seu@email.com"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-body-sm text-gray-200 mb-1">
                Senha
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-base border border-border rounded text-white text-body px-4 py-3
                  placeholder:text-gray-400 focus:border-blu-500 focus:shadow-glow-blu
                  focus:outline-none transition-colors duration-normal"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p className="text-body-sm text-urgent">{error}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blu-500 hover:bg-blu-400 disabled:bg-gray-600 disabled:text-gray-400
                text-white text-body-sm font-medium rounded py-3
                transition-colors duration-normal cursor-pointer
                focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:outline-none"
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </form>

          <div className="relative my-5">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-border" />
            </div>
            <div className="relative flex justify-center">
              <span className="bg-surface px-3 text-caption text-gray-500">ou</span>
            </div>
          </div>

          <button
            type="button"
            onClick={signInWithGoogle}
            className="w-full flex items-center justify-center gap-3 bg-base hover:bg-elevated
              border border-border rounded py-3 text-body-sm text-gray-200
              transition-colors duration-normal cursor-pointer
              focus-visible:ring-2 focus-visible:ring-blu-500 focus-visible:outline-none"
          >
            <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
              <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z" fill="#4285F4"/>
              <path d="M9 18c2.43 0 4.467-.806 5.956-2.184l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z" fill="#34A853"/>
              <path d="M3.964 10.706A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.706V4.962H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.038l3.007-2.332Z" fill="#FBBC05"/>
              <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.962L3.964 7.294C4.672 5.163 6.656 3.58 9 3.58Z" fill="#EA4335"/>
            </svg>
            Entrar com Google
          </button>
        </div>
      </div>
    </div>
  )
}
