'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { isAuthenticated, removeToken } from '@/lib/auth'
import type { Project } from '@/lib/types'

export default function DashboardPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newFot, setNewFot] = useState('')
  const [creating, setCreating] = useState(false)
  const [limitError, setLimitError] = useState('')

  useEffect(() => {
    if (!isAuthenticated()) {
      router.push('/auth/login')
      return
    }
    api.get('/projects').then(r => setProjects(r.data)).finally(() => setLoading(false))
  }, [router])

  async function createProject() {
    setCreating(true)
    setLimitError('')
    try {
      const { data } = await api.post('/projects', {
        title: newTitle,
        fot_limit: newFot ? parseFloat(newFot) : null,
      })
      setProjects(prev => [...prev, data])
      setShowModal(false)
      setNewTitle('')
      setNewFot('')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      if (typeof detail === 'object' && detail !== null && 'upgrade_required' in detail) {
        setLimitError('Достигнут лимит проектов. Обновите план.')
      } else {
        setLimitError('Ошибка создания проекта')
      }
    } finally {
      setCreating(false)
    }
  }

  function logout() {
    removeToken()
    router.push('/')
  }

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Загрузка...</div>

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm px-8 py-4 flex items-center justify-between">
        <span className="text-xl font-bold text-blue-600">HireOpt</span>
        <button onClick={logout} className="text-sm text-gray-500 hover:text-gray-900">Выйти</button>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold">Мои проекты</h1>
          <button
            onClick={() => setShowModal(true)}
            className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-semibold hover:bg-blue-700"
          >
            + Новый проект
          </button>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <p className="text-lg mb-2">Нет проектов</p>
            <p className="text-sm">Создайте первый проект найма</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {projects.map(p => (
              <Link key={p.id} href={`/project/${p.id}`}>
                <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition cursor-pointer">
                  <h2 className="font-semibold text-lg mb-1">{p.title}</h2>
                  {p.fot_limit && (
                    <p className="text-sm text-gray-500">ФОТ: {p.fot_limit.toLocaleString('ru')} ₽</p>
                  )}
                  <p className="text-xs text-gray-400 mt-2">{new Date(p.created_at).toLocaleDateString('ru')}</p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>

      {showModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 w-full max-w-md shadow-xl">
            <h2 className="text-xl font-bold mb-5">Новый проект</h2>
            <div className="space-y-4">
              <input
                placeholder="Название проекта" value={newTitle}
                onChange={e => setNewTitle(e.target.value)}
                className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <input
                placeholder="Лимит ФОТ (₽, необязательно)" value={newFot}
                onChange={e => setNewFot(e.target.value)} type="number"
                className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              {limitError && <p className="text-red-500 text-sm">{limitError}</p>}
              <div className="flex gap-3 justify-end">
                <button onClick={() => setShowModal(false)} className="text-gray-500 px-4 py-2 rounded-lg hover:bg-gray-100">
                  Отмена
                </button>
                <button
                  onClick={createProject} disabled={creating || !newTitle}
                  className="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
                >
                  {creating ? 'Создание...' : 'Создать'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
