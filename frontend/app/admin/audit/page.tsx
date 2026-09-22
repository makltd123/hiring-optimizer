'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import { AuditLogEntry, AuditLogResponse } from '@/lib/types'

const ACTION_LABELS: Record<string, string> = {
  'user.login': 'Вход',
  'user.created': 'Создан пользователь',
  'user.role_changed': 'Смена роли',
  'project.created': 'Создан проект',
  'project.deleted': 'Удалён проект',
  'candidate.added': 'Добавлен кандидат',
  'optimization.run': 'Запуск оптимизации',
  'result.viewed': 'Просмотр результата',
  'report.exported': 'Экспорт отчёта',
  'integration.configured': 'Настройка интеграции',
  'import.started': 'Импорт резюме',
}

export default function AuditPage() {
  const router = useRouter()
  const [data, setData] = useState<AuditLogResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionFilter, setActionFilter] = useState('')
  const [exporting, setExporting] = useState(false)

  const load = async (action?: string) => {
    setLoading(true)
    try {
      const params: Record<string, string> = { limit: '200' }
      if (action) params.action = action
      const res = await api.get('/admin/audit-log', { params })
      setData(res.data)
    } catch (e: any) {
      if (e.response?.status === 403) {
        setError('Недостаточно прав для просмотра аудит-лога')
      } else {
        setError('Ошибка загрузки аудит-лога')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const exportCsv = async () => {
    setExporting(true)
    try {
      const res = await api.get('/admin/audit-log/export', { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = 'audit-log.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      alert('Ошибка экспорта')
    } finally {
      setExporting(false)
    }
  }

  if (error) return <div className="p-8 text-red-500">{error}</div>

  return (
    <div className="max-w-5xl mx-auto p-8">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <button onClick={() => router.back()} className="text-gray-500 hover:text-gray-700">←</button>
          <h1 className="text-2xl font-bold">Аудит-лог</h1>
          {data && <span className="text-sm text-gray-400">{data.total} записей</span>}
        </div>
        <button
          onClick={exportCsv}
          disabled={exporting}
          className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium"
        >
          {exporting ? 'Экспортируем...' : 'Экспорт CSV'}
        </button>
      </div>

      {/* Фильтр по действию */}
      <div className="mb-4 flex gap-2 flex-wrap">
        <button
          onClick={() => { setActionFilter(''); load() }}
          className={`px-3 py-1 rounded-full text-xs font-medium border ${!actionFilter ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-300 text-gray-600'}`}
        >
          Все
        </button>
        {Object.entries(ACTION_LABELS).map(([key, label]) => (
          <button
            key={key}
            onClick={() => { setActionFilter(key); load(key) }}
            className={`px-3 py-1 rounded-full text-xs font-medium border ${actionFilter === key ? 'bg-indigo-600 text-white border-indigo-600' : 'border-gray-300 text-gray-600'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-gray-400 py-8 text-center">Загрузка...</div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Время</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Действие</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Сущность</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">IP</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Детали</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map(entry => (
                <tr key={entry.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-2 text-gray-500 whitespace-nowrap text-xs">
                    {new Date(entry.created_at).toLocaleString('ru')}
                  </td>
                  <td className="px-4 py-2">
                    <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded text-xs font-medium">
                      {ACTION_LABELS[entry.action] || entry.action}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-gray-500 text-xs">
                    {entry.entity_type}{entry.entity_id ? ` #${entry.entity_id}` : ''}
                  </td>
                  <td className="px-4 py-2 text-gray-400 text-xs font-mono">{entry.ip_address || '—'}</td>
                  <td className="px-4 py-2 text-gray-400 text-xs font-mono max-w-xs truncate">
                    {Object.keys(entry.details).length > 0 ? JSON.stringify(entry.details) : '—'}
                  </td>
                </tr>
              ))}
              {!data?.items.length && (
                <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Записей нет</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
