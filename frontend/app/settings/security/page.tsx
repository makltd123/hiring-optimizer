'use client'

import { useState } from 'react'
import api from '@/lib/api'

export default function SecurityPage() {
  const [setupData, setSetupData] = useState<{ qr_code: string; secret: string; manual_entry: string } | null>(null)
  const [secret, setSecret] = useState('')
  const [code, setCode] = useState('')
  const [backupCodes, setBackupCodes] = useState<string[]>([])
  const [disableCode, setDisableCode] = useState('')
  const [disablePassword, setDisablePassword] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  async function startSetup() {
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/mfa/setup')
      setSetupData(data)
      setSecret(data.secret)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Ошибка при настройке MFA')
    } finally {
      setLoading(false)
    }
  }

  async function confirmMFA(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/mfa/confirm-with-secret', { secret, code })
      setBackupCodes(data.backup_codes || [])
      setSuccess('MFA успешно включён!')
      setSetupData(null)
      setCode('')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Неверный код')
    } finally {
      setLoading(false)
    }
  }

  async function disableMFA(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/mfa/disable', { code: disableCode, password: disablePassword })
      setSuccess('MFA отключён')
      setDisableCode('')
      setDisablePassword('')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Ошибка отключения MFA')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Безопасность — MFA</h1>

      {error && <div className="mb-4 text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">{error}</div>}
      {success && <div className="mb-4 text-green-700 bg-green-50 border border-green-200 rounded-lg p-3">{success}</div>}

      {/* Включить MFA */}
      {!setupData && backupCodes.length === 0 && (
        <div className="bg-white rounded-xl border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-2">Подключить Google Authenticator</h2>
          <p className="text-sm text-gray-600 mb-4">
            MFA защищает ваш аккаунт дополнительным кодом при входе.
          </p>
          <button
            onClick={startSetup}
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Загрузка...' : 'Настроить MFA'}
          </button>
        </div>
      )}

      {/* QR-код */}
      {setupData && (
        <div className="bg-white rounded-xl border p-6 mb-6">
          <h2 className="text-lg font-semibold mb-4">Сканируйте QR-код</h2>
          <div className="flex justify-center mb-4">
            <img src={setupData.qr_code} alt="MFA QR" className="w-48 h-48" />
          </div>
          <p className="text-sm text-gray-600 mb-2 text-center">
            Или введите секрет вручную:
          </p>
          <p className="font-mono text-sm text-center bg-gray-50 rounded p-2 mb-4 select-all">
            {setupData.manual_entry}
          </p>
          <form onSubmit={confirmMFA} className="space-y-3">
            <input
              type="text"
              placeholder="Код из приложения (6 цифр)"
              value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              maxLength={6}
              required
              className="w-full border rounded-lg px-4 py-2 text-center text-xl tracking-widest focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="w-full bg-green-600 text-white py-2 rounded-lg font-semibold hover:bg-green-700 disabled:opacity-50"
            >
              {loading ? 'Проверка...' : 'Подтвердить и включить MFA'}
            </button>
          </form>
        </div>
      )}

      {/* Резервные коды */}
      {backupCodes.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6 mb-6">
          <h2 className="text-lg font-semibold mb-2 text-yellow-800">Резервные коды</h2>
          <p className="text-sm text-yellow-700 mb-4">
            Сохраните эти коды в надёжном месте. Каждый можно использовать только один раз.
          </p>
          <div className="grid grid-cols-2 gap-2">
            {backupCodes.map((c, i) => (
              <code key={i} className="bg-white border rounded px-3 py-1 font-mono text-sm text-center">
                {c}
              </code>
            ))}
          </div>
        </div>
      )}

      {/* Отключить MFA */}
      <div className="bg-white rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-2 text-red-700">Отключить MFA</h2>
        <form onSubmit={disableMFA} className="space-y-3">
          <input
            type="password"
            placeholder="Ваш пароль"
            value={disablePassword}
            onChange={e => setDisablePassword(e.target.value)}
            required
            className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-red-300"
          />
          <input
            type="text"
            placeholder="Код из приложения"
            value={disableCode}
            onChange={e => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
            maxLength={6}
            required
            className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-red-300"
          />
          <button
            type="submit"
            disabled={loading}
            className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? 'Отключение...' : 'Отключить MFA'}
          </button>
        </form>
      </div>
    </div>
  )
}
