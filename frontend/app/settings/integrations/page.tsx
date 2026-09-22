'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import { IntegrationStatus } from '@/lib/types'

export default function IntegrationsPage() {
  const router = useRouter()
  const [status, setStatus] = useState<IntegrationStatus | null>(null)
  const [emailForm, setEmailForm] = useState({ host: '', port: '993', user: '', password: '', sender_filter: 'noreply@hh.ru' })
  const [avitoForm, setAvitoForm] = useState({ client_id: '', client_secret: '' })
  const [emailSaving, setEmailSaving] = useState(false)
  const [avitoSaving, setAvitoSaving] = useState(false)
  const [emailMsg, setEmailMsg] = useState('')
  const [avitoMsg, setAvitoMsg] = useState('')

  useEffect(() => {
    api.get('/integrations/status').then(r => setStatus(r.data)).catch(() => {})
  }, [])

  const saveEmail = async () => {
    setEmailSaving(true)
    setEmailMsg('')
    try {
      await api.post('/integrations/email/configure', {
        ...emailForm,
        port: parseInt(emailForm.port),
      })
      setEmailMsg('✓ Подключено успешно')
      setStatus(prev => prev ? { ...prev, email: 'configured' } : prev)
    } catch (e: any) {
      setEmailMsg(`Ошибка: ${e.response?.data?.detail || 'Не удалось подключиться'}`)
    } finally {
      setEmailSaving(false)
    }
  }

  const saveAvito = async () => {
    setAvitoSaving(true)
    setAvitoMsg('')
    try {
      await api.post('/integrations/avito/connect', avitoForm)
      setAvitoMsg('✓ Авито подключён успешно')
      setStatus(prev => prev ? { ...prev, avito: 'configured' } : prev)
    } catch (e: any) {
      setAvitoMsg(`Ошибка: ${e.response?.data?.detail || 'Неверные credentials'}`)
    } finally {
      setAvitoSaving(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-8">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => router.back()} className="text-gray-500 hover:text-gray-700">←</button>
        <h1 className="text-2xl font-bold">Интеграции</h1>
      </div>

      {/* Статус */}
      {status && (
        <div className="flex gap-4 mb-6">
          <StatusChip label="Email IMAP" ok={status.email === 'configured'} />
          <StatusChip label="Авито API" ok={status.avito === 'configured'} />
        </div>
      )}

      {/* Email IMAP */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 mb-5">
        <h2 className="font-semibold text-lg mb-1">Email (IMAP)</h2>
        <p className="text-sm text-gray-500 mb-4">
          HH.ru отправляет PDF резюме откликнувшихся кандидатов на почту HR-менеджера.
          Введите параметры IMAP вашего корпоративного ящика.
        </p>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">IMAP хост</label>
            <input value={emailForm.host} onChange={e => setEmailForm(f => ({ ...f, host: e.target.value }))}
              placeholder="imap.mail.ru" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Порт</label>
            <input value={emailForm.port} onChange={e => setEmailForm(f => ({ ...f, port: e.target.value }))}
              placeholder="993" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
            <input value={emailForm.user} onChange={e => setEmailForm(f => ({ ...f, user: e.target.value }))}
              placeholder="hr@company.ru" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Пароль</label>
            <input type="password" value={emailForm.password} onChange={e => setEmailForm(f => ({ ...f, password: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div className="col-span-2">
            <label className="block text-xs font-medium text-gray-600 mb-1">Фильтр отправителя</label>
            <input value={emailForm.sender_filter} onChange={e => setEmailForm(f => ({ ...f, sender_filter: e.target.value }))}
              placeholder="noreply@hh.ru" className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={saveEmail} disabled={emailSaving}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50">
            {emailSaving ? 'Проверяем...' : 'Подключить и сохранить'}
          </button>
          {emailMsg && <span className={`text-sm ${emailMsg.startsWith('✓') ? 'text-green-600' : 'text-red-500'}`}>{emailMsg}</span>}
        </div>
      </div>

      {/* Авито */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="font-semibold text-lg mb-1">Авито Работа API</h2>
        <p className="text-sm text-gray-500 mb-4">
          Получите Client ID и Client Secret в личном кабинете Авито через{' '}
          <span className="font-medium">Инструменты → API</span>.
        </p>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Client ID</label>
            <input value={avitoForm.client_id} onChange={e => setAvitoForm(f => ({ ...f, client_id: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Client Secret</label>
            <input type="password" value={avitoForm.client_secret} onChange={e => setAvitoForm(f => ({ ...f, client_secret: e.target.value }))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm" />
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={saveAvito} disabled={avitoSaving}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50">
            {avitoSaving ? 'Проверяем...' : 'Подключить'}
          </button>
          {avitoMsg && <span className={`text-sm ${avitoMsg.startsWith('✓') ? 'text-green-600' : 'text-red-500'}`}>{avitoMsg}</span>}
        </div>
      </div>
    </div>
  )
}

function StatusChip({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium border ${ok ? 'bg-green-50 border-green-200 text-green-700' : 'bg-gray-50 border-gray-200 text-gray-500'}`}>
      <span className={`w-2 h-2 rounded-full ${ok ? 'bg-green-500' : 'bg-gray-400'}`} />
      {label}
    </div>
  )
}
