'use client'

import type { OptimizationResult, Vacancy, Candidate } from '@/lib/types'

interface Props {
  result: OptimizationResult
  vacancies: Vacancy[]
  candidates: Candidate[]
}

function scoreColor(score: number): string {
  if (score >= 0.7) return 'bg-green-500 text-white'
  if (score >= 0.4) return 'bg-yellow-400 text-gray-900'
  if (score > 0) return 'bg-orange-200 text-gray-700'
  return 'bg-gray-100 text-gray-400'
}

export default function MatchMatrix({ result, vacancies, candidates }: Props) {
  if (!vacancies.length || !candidates.length) return null

  return (
    <div className="bg-white rounded-xl border p-4 overflow-x-auto">
      <h3 className="font-semibold mb-3 text-sm text-gray-600">Матрица соответствия</h3>
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="px-2 py-1 text-left text-gray-400 font-normal min-w-[100px]"></th>
            {vacancies.map(v => (
              <th key={v.id} className="px-2 py-1 text-center font-medium text-gray-600 max-w-[80px] truncate" title={v.title}>
                {v.title.length > 12 ? v.title.slice(0, 12) + '…' : v.title}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {candidates.map(c => (
            <tr key={c.id}>
              <td className="px-2 py-1 text-gray-600 font-medium">{c.display_name}</td>
              {vacancies.map(v => {
                const score = result.match_scores[String(v.id)]?.[String(c.id)] ?? 0
                const isAssigned = result.assignment[String(v.id)] === c.id
                return (
                  <td key={v.id} className="px-1 py-1 text-center">
                    <div className={`rounded px-2 py-1 font-semibold ${scoreColor(score)} ${isAssigned ? 'ring-2 ring-blue-500' : ''}`}>
                      {Math.round(score * 100)}%
                    </div>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-gray-400 mt-2">Синяя рамка — выбранное назначение</p>
    </div>
  )
}
