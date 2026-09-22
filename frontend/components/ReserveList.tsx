'use client'

import { useEffect, useState } from 'react'
import api from '@/lib/api'
import type { ReserveResponse, ReserveItem } from '@/lib/types'

interface Props {
  projectId: number
  onSwap?: (excludeId: number) => void
}

export default function ReserveList({ projectId, onSwap }: Props) {
  const [data, setData] = useState<ReserveResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<ReserveResponse>(`/projects/${projectId}/reserve`)
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return <div className="text-sm text-gray-400 py-4">Загрузка резервного списка...</div>
  if (!data || data.reserve.length === 0) return null

  return (
    <div className="bg-white rounded-xl border p-5 space-y-3">
      <h3 className="font-semibold text-gray-800">Резервный список ({data.reserve.length})</h3>
      <div className="space-y-3">
        {data.reserve.map((item: ReserveItem) => (
          <div key={item.candidate_id} className="border rounded-lg p-3 bg-gray-50">
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-gray-400">#{item.rank}</span>
                  <span className="font-medium text-sm text-gray-800">{item.display_name}</span>
                  <span className={`text-xs font-semibold ${item.best_score >= 0.7 ? 'text-green-600' : item.best_score >= 0.4 ? 'text-yellow-600' : 'text-red-500'}`}>
                    {Math.round(item.best_score * 100)}%
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5">
                  Мог закрыть: <span className="font-medium text-gray-700">{item.best_vacancy_title}</span>
                </p>
                <p className="text-xs text-gray-400 mt-0.5">{item.rejection_reason}</p>
              </div>
              {onSwap && item.competitor_candidate_id != null && (
                <button
                  onClick={() => onSwap(item.competitor_candidate_id!)}
                  className="text-xs bg-white border border-blue-300 text-blue-600 px-2.5 py-1.5 rounded-lg hover:bg-blue-50 whitespace-nowrap"
                >
                  Заменить
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
