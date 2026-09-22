'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import api from '@/lib/api'
import { OrgUser, UserRole } from '@/lib/types'
import UserRoleBadge from '@/components/UserRoleBadge'

const ROLES: UserRole[] = ['admin', 'org_admin', 'dept_manager', 'hr_manager', 'viewer']
const ROLE_LABELS: Record<UserRole, string> = {
  admin: 'Администратор',
  org_admin: 'HR-директор',
  dept_manager: 'Рук. отдела',
  hr_manager: 'HR-менеджер',
  viewer: 'Наблюдатель',
}

export default function UsersPage() {
  const router = useRouter()
  const [users, setUsers] = useState<OrgUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [newEmail, setNewEmail] = useState('')
  const [newRole, setNewRole] = useState<UserRole>('hr_manager')
  const [creating, setCreating] = useState(false)

  const load = async () => {
    try {
      const res = await api.get('/org/users')
      setUsers(res.data)
    } catch (e: any) {
      if (e.response?.status === 403) {
        setError('Недостаточно прав для просмотра пользователей')
      } else {
        setError('Ошибка загрузки пользователей')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const changeRole = async (userId: number, role: UserRole) => {
    try {
      await api.put(`/org/users/${userId}/role`, { role })
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, role } : u))
    } catch {
      alert('Ошибка изменения роли')
    }
  }

  const createUser = async () => {
    if (!newEmail) return
    setCreating(true)
    try {
      const res = await api.post('/org/users', { email: newEmail, role: newRole })
      setUsers(prev => [...prev, { ...res.data, dept_id: null, last_login: null, created_at: new Date().toISOString() }])
      setNewEmail('')
      if (res.data.temp_password) {
        alert(`Пользователь создан.\nВременный пароль: ${res.data.temp_password}\nПопросите пользователя сменить его при первом входе.`)
      }
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка создания пользователя')
    } finally {
      setCreating(false)
    }
  }

  if (loading) return <div className="p-8 text-gray-500">Загрузка...</div>
  if (error) return <div className="p-8 text-red-500">{error}</div>

  return (
    <div className="max-w-4xl mx-auto p-8">
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => router.back()} className="text-gray-500 hover:text-gray-700">←</button>
        <h1 className="text-2xl font-bold">Управление пользователями</h1>
      </div>

      {/* Создать пользователя */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
        <h2 className="font-semibold mb-3">Добавить пользователя</h2>
        <div className="flex gap-3">
          <input
            type="email"
            value={newEmail}
            onChange={e => setNewEmail(e.target.value)}
            placeholder="email@company.ru"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm"
          />
          <select
            value={newRole}
            onChange={e => setNewRole(e.target.value as UserRole)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
          >
            {ROLES.filter(r => r !== 'admin').map(r => (
              <option key={r} value={r}>{ROLE_LABELS[r]}</option>
            ))}
          </select>
          <button
            onClick={createUser}
            disabled={creating || !newEmail}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {creating ? 'Создаём...' : 'Добавить'}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-2">Случайный временный пароль будет показан после создания пользователя.</p>
      </div>

      {/* Таблица */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Email</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Роль</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Последний вход</th>
              <th className="px-4 py-3 text-left font-medium text-gray-600">Изменить роль</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{u.email}</td>
                <td className="px-4 py-3"><UserRoleBadge role={u.role} /></td>
                <td className="px-4 py-3 text-gray-500">
                  {u.last_login ? new Date(u.last_login).toLocaleDateString('ru') : '—'}
                </td>
                <td className="px-4 py-3">
                  <select
                    value={u.role}
                    onChange={e => changeRole(u.id, e.target.value as UserRole)}
                    className="border border-gray-300 rounded px-2 py-1 text-xs"
                  >
                    {ROLES.map(r => (
                      <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-gray-400">Пользователи не найдены</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
