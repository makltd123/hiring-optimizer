'use client'

import { useState, useEffect } from 'react'
import api from '@/lib/api'

export default function NotificationsPage() {
  const [notifyEmail, setNotifyEmail] = useState(true)
  const [telegramChatId, setTelegramChatId] = useState('')
  const [webhookUrl, setWebhookUrl] = useState('')
  const [webhookSecret, setWebhookSecret] = useState('')
  const [success, setSuccess] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)

  async function saveNotifications(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      await api.put('/org/me/notifications', {
        notify_email: notifyEmail,
        telegram_chat_id: telegramChatId || null,
      })
      setSuccess('Настройки уведомлений сохранены')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Ошибка сохранения')
    } finally {
      setLoading(false)
    }
  }

  async function saveWebhook(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    setSuccess('')
    try {
      await api.put('/org/webhooks', {
        webhook_url: webhookUrl || null,
        webhook_secret: webhookSecret || null,
      })
      setSuccess('Настройки вебхука сохранены')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Ошибка сохранения вебхука')
    } finally {
      setLoading(false)
    }
  }

  async function testWebhook() {
    setTesting(true)
    setError('')
    setSuccess('')
    try {
      await api.post('/org/webhooks/test')
      setSuccess('Тестовый вебхук отправлен')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(typeof msg === 'string' ? msg : 'Ошибка отправки вебхука')
    } finally {
      setTesting(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold mb-6">Уведомления</h1>

      {error && <div className="mb-4 text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">{error}</div>}
      {success && <div className="mb-4 text-green-700 bg-green-50 border border-green-200 rounded-lg p-3">{success}</div>}

      {/* Личные уведомления */}
      <div className="bg-white rounded-xl border p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4">Личные уведомления</h2>
        <form onSubmit={saveNotifications} className="space-y-4">
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={notifyEmail}
              onChange={e => setNotifyEmail(e.target.checked)}
              className="w-4 h-4"
            />
            <span className="text-sm">Email-уведомления (завершение оптимизации, согласования)</span>
          </label>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Telegram Chat ID
            </label>
            <input
              type="text"
              placeholder="Например: 123456789"
              value={telegramChatId}
              onChange={e => setTelegramChatId(e.target.value)}
              className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <p className="text-xs text-gray-500 mt-1">
              Получите Chat ID через бот @userinfobot в Telegram
            </p>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? 'Сохранение...' : 'Сохранить'}
          </button>
        </form>
      </div>

      {/* Вебхук организации */}
      <div className="bg-white rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">Вебхук организации</h2>
        <p className="text-sm text-gray-600 mb-4">
          Получайте события (завершение оптимизации) на ваш корпоративный URL.
        </p>
        <form onSubmit={saveWebhook} className="space-y-3">
          <input
            type="url"
            placeholder="https://your-company.ru/webhook"
            value={webhookUrl}
            onChange={e => setWebhookUrl(e.target.value)}
            className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <input
            type="text"
            placeholder="Секрет для подписи (опционально)"
            value={webhookSecret}
            onChange={e => setWebhookSecret(e.target.value)}
            className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Сохранение...' : 'Сохранить'}
            </button>
            <button
              type="button"
              onClick={testWebhook}
              disabled={testing || !webhookUrl}
              className="border border-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              {testing ? 'Отправка...' : 'Тест'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
