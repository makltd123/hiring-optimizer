'use client'

import { useState } from 'react'
import api from '@/lib/api'
import type { Vacancy } from '@/lib/types'

interface Props {
  projectId: number
  vacancies: Vacancy[]
  onAdded: (v: Vacancy) => void
  onDeleted: (id: number) => void
}

export default function VacancyForm({ projectId, vacancies, onAdded, onDeleted }: Props) {
  const [title, setTitle] = useState('')
  const [skillInput, setSkillInput] = useState('')
  const [skills, setSkills] = useState<string[]>([])
  const [salaryMax, setSalaryMax] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function addSkill(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && skillInput.trim()) {
      e.preventDefault()
      setSkills(prev => [...prev, skillInput.trim()])
      setSkillInput('')
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      const { data } = await api.post(`/projects/${projectId}/vacancies`, {
        title,
        required_skills: skills,
        salary_max: salaryMax ? parseFloat(salaryMax) : null,
      })
      onAdded(data)
      setTitle('')
      setSkills([])
      setSalaryMax('')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      if (typeof detail === 'object' && detail !== null && 'upgrade_required' in detail) {
        setError('Достигнут лимит вакансий. Обновите план.')
      } else {
        setError('Ошибка сохранения')
      }
    } finally {
      setSaving(false)
    }
  }

  async function deleteVacancy(id: number) {
    await api.delete(`/projects/${projectId}/vacancies/${id}`)
    onDeleted(id)
  }

  return (
    <div className="space-y-6">
      <form onSubmit={submit} className="bg-white rounded-xl border p-5 space-y-4">
        <h3 className="font-semibold text-lg">Добавить вакансию</h3>
        <input
          placeholder="Название роли (напр. Backend Developer)" value={title}
          onChange={e => setTitle(e.target.value)} required
          className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <div>
          <input
            placeholder="Навык (нажмите Enter)" value={skillInput}
            onChange={e => setSkillInput(e.target.value)} onKeyDown={addSkill}
            className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          {skills.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-2">
              {skills.map(s => (
                <span key={s} className="bg-blue-100 text-blue-700 text-xs px-3 py-1 rounded-full flex items-center gap-1">
                  {s}
                  <button type="button" onClick={() => setSkills(prev => prev.filter(x => x !== s))} className="ml-1 hover:text-red-500">×</button>
                </span>
              ))}
            </div>
          )}
        </div>
        <input
          placeholder="Макс. зарплата (₽, необязательно)" value={salaryMax}
          onChange={e => setSalaryMax(e.target.value)} type="number"
          className="w-full border rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button
          type="submit" disabled={saving || !title}
          className="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? 'Сохранение...' : 'Добавить вакансию'}
        </button>
      </form>

      {vacancies.length > 0 && (
        <div className="space-y-3">
          {vacancies.map(v => (
            <div key={v.id} className="bg-white rounded-xl border p-4 flex items-start justify-between">
              <div>
                <p className="font-medium">{v.title}</p>
                <div className="flex flex-wrap gap-1 mt-1">
                  {v.required_skills.map(s => (
                    <span key={s} className="bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded">{s}</span>
                  ))}
                </div>
                {v.salary_max && <p className="text-sm text-gray-500 mt-1">до {v.salary_max.toLocaleString('ru')} ₽</p>}
              </div>
              <button onClick={() => deleteVacancy(v.id)} className="text-gray-400 hover:text-red-500 text-lg ml-4">×</button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
