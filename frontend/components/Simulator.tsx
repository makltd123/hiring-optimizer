'use client'

import { useState, useCallback, useRef } from 'react'
import api from '@/lib/api'
import type { Candidate, Vacancy, OptimizationResult, SimulateResponse } from '@/lib/types'

interface Props {
  projectId: number
  candidates: Candidate[]
  vacancies: Vacancy[]
  baseResult: OptimizationResult
}

export default function Simulator({ projectId, candidates, vacancies, baseResult }: Props) {
  const [excludedIds, setExcludedIds] = useState<Set<number>>(new Set())
  const [simResult, setSimResult] = useState<SimulateResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const candidateMap = Object.fromEntries(candidates.map(c => [c.id, c]))

  const runSimulate = useCallback(async (excluded: Set<number>) => {
    setLoading(true)
    try {
      const { data } = await api.post<SimulateResponse>(`/projects/${projectId}/simulate`, {
        excluded_candidate_ids: Array.from(excluded),
        excluded_vacancy_ids: [],
      })
      setSimResult(data)
    } catch {
      setSimResult(null)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  const toggle = (candidateId: number) => {
    setExcludedIds(prev => {
      const next = new Set(prev)
      if (next.has(candidateId)) {
        next.delete(candidateId)
      } else {
        next.add(candidateId)
      }
      if (debounceRef.current) clearTimeout(debounceRef.current)
      debounceRef.current = setTimeout(() => runSimulate(next), 300)
      return next
    })
  }

  const assignment = simResult?.assignment ?? baseResult.assignment
  const matchScores = simResult?.match_scores ?? baseResult.match_scores

  const baseCoverage = Math.round(
    (vacancies.length - baseResult.uncovered_vacancies.length) / vacancies.length * 100
  )

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">Симулятор "Что если"</h3>
        {loading && <span className="text-sm text-blue-500">Пересчёт...</span>}
      </div>

      {simResult && (
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-blue-50 rounded-lg p-3 text-center">
            <p className="text-sm text-gray-500">Покрытие</p>
            <p className="font-bold text-blue-700">
              было {baseCoverage}% → стало {Math.round(simResult.coverage * 100)}%
            </p>
            {simResult.diff.coverage_delta !== 0 && (
              <p className={`text-xs font-medium ${simResult.diff.coverage_delta < 0 ? 'text-red-500' : 'text-green-600'}`}>
                {simResult.diff.coverage_delta > 0 ? '+' : ''}{Math.round(simResult.diff.coverage_delta * 100)}%
              </p>
            )}
          </div>
          <div className="bg-green-50 rounded-lg p-3 text-center">
            <p className="text-sm text-gray-500">ФОТ</p>
            <p className="font-bold text-green-700">
              {simResult.total_cost.toLocaleString('ru')} ₽
            </p>
            {simResult.diff.cost_delta !== 0 && (
              <p className={`text-xs font-medium ${simResult.diff.cost_delta > 0 ? 'text-red-500' : 'text-green-600'}`}>
                {simResult.diff.cost_delta > 0 ? '+' : ''}{simResult.diff.cost_delta.toLocaleString('ru')} ₽
              </p>
            )}
          </div>
        </div>
      )}

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-semibold w-12">Вкл</th>
              <th className="text-left px-4 py-3 font-semibold">Кандидат</th>
              <th className="text-left px-4 py-3 font-semibold">Вакансия</th>
              <th className="text-left px-4 py-3 font-semibold">Score</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map(c => {
              const excluded = excludedIds.has(c.id)
              const assignedVacancyEntry = Object.entries(assignment).find(
                ([, cId]) => cId === c.id
              )
              const vacancy = assignedVacancyEntry
                ? vacancies.find(v => String(v.id) === assignedVacancyEntry[0])
                : null
              const score = assignedVacancyEntry && vacancy
                ? matchScores[String(vacancy.id)]?.[String(c.id)] ?? 0
                : 0

              return (
                <tr
                  key={c.id}
                  className={`border-b last:border-0 transition-colors ${excluded ? 'bg-gray-100 opacity-50' : ''}`}
                >
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggle(c.id)}
                      className={`w-10 h-5 rounded-full transition-colors relative ${excluded ? 'bg-gray-300' : 'bg-blue-500'}`}
                    >
                      <span
                        className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${excluded ? 'left-0.5' : 'left-5'}`}
                      />
                    </button>
                  </td>
                  <td className={`px-4 py-3 font-medium ${excluded ? 'line-through text-gray-400' : ''}`}>
                    {c.display_name}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {excluded ? '—' : vacancy ? vacancy.title : <span className="text-gray-400">Не назначен</span>}
                  </td>
                  <td className="px-4 py-3">
                    {!excluded && vacancy ? (
                      <span className={`font-semibold ${score >= 0.7 ? 'text-green-600' : score >= 0.4 ? 'text-yellow-600' : 'text-red-500'}`}>
                        {Math.round(score * 100)}%
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
