'use client'

import { useEffect, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import api from '@/lib/api'
import type { BudgetAnalysisResponse } from '@/lib/types'

interface Props {
  projectId: number
}

function fmt(n: number) {
  return n >= 1_000_000
    ? `${(n / 1_000_000).toFixed(1)}млн`
    : `${Math.round(n / 1000)}к`
}

export default function BudgetChart({ projectId }: Props) {
  const [data, setData] = useState<BudgetAnalysisResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get<BudgetAnalysisResponse>(`/projects/${projectId}/budget-analysis`)
      .then(r => setData(r.data))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [projectId])

  if (loading) return <div className="text-sm text-gray-400 py-4">Загрузка анализа бюджета...</div>
  if (!data || data.scenarios.length === 0) return null

  const chartData = data.scenarios.map(s => ({
    fot: s.fot_limit,
    coverage: Math.round(s.coverage * 100),
    label: fmt(s.fot_limit),
  }))

  return (
    <div className="bg-white rounded-xl border p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">Анализ бюджета найма</h3>
        {data.full_coverage_fot && data.current_fot && data.delta_to_full != null && data.delta_to_full > 0 && (
          <p className="text-xs text-gray-500">
            Для 100% покрытия нужно ещё{' '}
            <span className="font-semibold text-blue-600">+{fmt(data.delta_to_full)} ₽</span>
          </p>
        )}
      </div>

      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="fot"
            tickFormatter={fmt}
            tick={{ fontSize: 11 }}
            label={{ value: 'Бюджет ФОТ', position: 'insideBottom', offset: -2, fontSize: 11 }}
          />
          <YAxis
            domain={[0, 100]}
            tickFormatter={v => `${v}%`}
            tick={{ fontSize: 11 }}
            width={40}
          />
          <Tooltip
            formatter={(v) => [`${v}%`, 'Покрытие']}
            labelFormatter={v => `Бюджет: ${fmt(Number(v))} ₽`}
          />
          {data.current_fot != null && (
            <ReferenceLine
              x={data.current_fot}
              stroke="#3b82f6"
              strokeDasharray="4 2"
              label={{ value: 'Текущий', position: 'top', fontSize: 10, fill: '#3b82f6' }}
            />
          )}
          <Line
            type="monotone"
            dataKey="coverage"
            stroke="#2563eb"
            strokeWidth={2}
            dot={{ r: 3, fill: '#2563eb' }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>

      {data.current_fot != null && (
        <p className="text-xs text-gray-500 text-center">
          Текущий бюджет: <span className="font-medium">{fmt(data.current_fot)} ₽</span>
          {data.full_coverage_fot && (
            <> &nbsp;·&nbsp; 100% покрытие при: <span className="font-medium">{fmt(data.full_coverage_fot)} ₽</span></>
          )}
        </p>
      )}
    </div>
  )
}
