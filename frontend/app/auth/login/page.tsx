'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { setTokenPair } from '@/lib/auth'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [tempToken, setTempToken] = useState('')
  const [mfaPending, setMfaPending] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { data } = await api.post('/auth/login', { email, password })
      if (data.mfa_required) {
        setTempToken(data.temp_token)
        setMfaPending(true)
      } else {
        setTokenPair(data.access_token, data.refresh_token)
        router.push('/dashboard')
      }
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Неверный email или пароль')
    } finally {
      setLoading(false)
    }
  }

  async function handleMfaVerify(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const { data } = await api.post('/auth/mfa/verify', { temp_token: tempToken, code: mfaCode })
      setTokenPair(data.access_token, data.refresh_token)
      router.push('/dashboard')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Неверный код')
    } finally {
      setLoading(false)
    }
  }

  if (mfaPending) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-2xl shadow-md w-full max-w-sm">
          <h1 className="text-2xl font-bold mb-2 text-center">Двухфакторная аутентификация</h1>
          <p className="text-sm text-gray-500 text-center mb-6">
            Введите 6-значный код из приложения Google Authenticator
          </p>
          <form onSubmit={handleMfaVerify} className="space-y-4">
            <input
              type="text"
              placeholder="000000"
              value={mfaCode}
              onChange={e => setMfaCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              required
              maxLength={6}
              className="w-full border rounded-lg px-4 py-2 text-center text-2xl tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-400"
              autoFocus
            />
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button
              type="submit" disabled={loading || mfaCode.length !== 6}
              className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Проверка...' : 'Подтвердить'}
            </button>
            <button
              type="button"
              onClick={() => { setMfaPending(false); setMfaCode(''); setTempToken(''); setError('') }}
              className="w-full text-sm text-gray-500 hover:text-gray-700"
            >
              Назад к форме входа
            </button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-8 rounded-2xl shadow-md w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6 text-center">Вход</h1>
        <form onSubmit={handleLogin} className="space-y-4">
          <input
            type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)}
            required className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <input
            type="password" placeholder="Пароль" value={password} onChange={e => setPassword(e.target.value)}
            required className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button
            type="submit" disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Вход...' : 'Войти'}
          </button>
        </form>
        <p className="text-center text-sm text-gray-500 mt-4">
          Нет аккаунта?{' '}
          <Link href="/auth/register" className="text-blue-600 hover:underline">Зарегистрироваться</Link>
        </p>
      </div>
    </div>
  )
}
