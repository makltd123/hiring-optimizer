'use client'

import api from '@/lib/api'
import type { OptimizationResult, Vacancy, Candidate } from '@/lib/types'

interface Props {
  result: OptimizationResult
  vacancies: Vacancy[]
  candidates: Candidate[]
  projectId: number
}

export default function ResultTable({ result, vacancies, candidates, projectId }: Props) {
  const candidateMap = Object.fromEntries(candidates.map(c => [c.id, c]))

  const totalCoverage = vacancies.length
    ? Math.round((vacancies.length - result.uncovered_vacancies.length) / vacancies.length * 100)
    : 0

  const handleExportPdf = async () => {
    const res = await api.get(`/projects/${projectId}/export/pdf`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data as Blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `hiring-report-${projectId}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <button
          onClick={handleExportPdf}
          className="text-sm bg-white border border-gray-300 text-gray-600 px-3 py-1.5 rounded-lg hover:bg-gray-50 flex items-center gap-1.5"
        >
          <span>↓</span> Скачать PDF
        </button>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-blue-50 rounded-xl p-4 text-center">
          <p className="text-3xl font-extrabold text-blue-600">{totalCoverage}%</p>
          <p className="text-sm text-gray-500 mt-1">Покрытие команды</p>
        </div>
        {result.total_cost ? (
          <div className="bg-green-50 rounded-xl p-4 text-center">
            <p className="text-3xl font-extrabold text-green-600">{result.total_cost.toLocaleString('ru')} ₽</p>
            <p className="text-sm text-gray-500 mt-1">Суммарный ФОТ</p>
          </div>
        ) : null}
      </div>

      <div className="bg-white rounded-xl border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="text-left px-4 py-3 font-semibold">Вакансия</th>
              <th className="text-left px-4 py-3 font-semibold">Кандидат</th>
              <th className="text-left px-4 py-3 font-semibold">Соответствие</th>
              <th className="text-left px-4 py-3 font-semibold">Зарплата</th>
            </tr>
          </thead>
          <tbody>
            {vacancies.map(v => {
              const candId = result.assignment[String(v.id)]
              const cand = candId != null ? candidateMap[candId] : null
              const score = candId != null
                ? result.match_scores[String(v.id)]?.[String(candId)] ?? 0
                : 0
              const uncovered = result.uncovered_vacancies.includes(v.id)
              return (
                <tr key={v.id} className={`border-b last:border-0 ${uncovered ? 'bg-red-50' : ''}`}>
                  <td className="px-4 py-3 font-medium">{v.title}</td>
                  <td className="px-4 py-3">{cand ? cand.display_name : <span className="text-red-500">Не закрыта</span>}</td>
                  <td className="px-4 py-3">
                    {cand ? (
                      <span className={`font-semibold ${score >= 0.7 ? 'text-green-600' : score >= 0.4 ? 'text-yellow-600' : 'text-red-500'}`}>
                        {Math.round(score * 100)}%
                      </span>
                    ) : '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {cand?.salary_expectation ? `${cand.salary_expectation.toLocaleString('ru')} ₽` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="bg-gray-50 rounded-xl border p-4">
        <p className="text-sm font-semibold text-gray-600 mb-2">Объяснение</p>
        <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">{result.explanation}</pre>
      </div>
    </div>
  )
}
