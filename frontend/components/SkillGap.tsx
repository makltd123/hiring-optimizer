'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import type { SkillGapResponse } from '@/lib/types'

interface Props {
  projectId: number
}

export default function SkillGap({ projectId }: Props) {
  const [data, setData] = useState<SkillGapResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<SkillGapResponse>(`/projects/${projectId}/skill-gap`)
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return <div className="text-sm text-gray-400 py-4">Загрузка дефицита скиллов...</div>
  if (!data) return null
  if (data.gaps.length === 0 && data.fully_covered.length === 0) return null

  return (
    <div className="bg-white rounded-xl border p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">Дефицит скиллов</h3>
        <span className="text-sm text-gray-500">
          Общее покрытие: <span className={`font-semibold ${data.overall_coverage >= 0.8 ? 'text-green-600' : 'text-yellow-600'}`}>
            {Math.round(data.overall_coverage * 100)}%
          </span>
        </span>
      </div>

      {data.gaps.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Не покрыты полностью</p>
          {data.gaps.map(g => (
            <div key={g.skill} className="flex items-center gap-3">
              <div className="w-28 text-sm font-medium text-gray-700 truncate">{g.skill}</div>
              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-2 rounded-full transition-all ${g.critical ? 'bg-red-500' : g.coverage < 0.5 ? 'bg-orange-400' : 'bg-yellow-400'}`}
                  style={{ width: `${Math.round(g.coverage * 100)}%` }}
                />
              </div>
              <div className="w-10 text-right text-sm text-gray-600">{Math.round(g.coverage * 100)}%</div>
              {g.critical && (
                <span className="text-xs text-red-500 font-medium">критично</span>
              )}
            </div>
          ))}
        </div>
      )}

      {data.fully_covered.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Полностью покрыты</p>
          <div className="flex flex-wrap gap-2">
            {data.fully_covered.map(skill => (
              <span key={skill} className="bg-green-50 text-green-700 border border-green-200 text-xs px-2.5 py-1 rounded-full">
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
