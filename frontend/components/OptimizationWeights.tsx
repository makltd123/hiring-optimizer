'use client'

import { useState } from 'react'
import type { OptimizationWeights } from '@/lib/types'

const DEFAULTS: OptimizationWeights = { skill_match: 0.6, salary_fit: 0.3, experience: 0.1 }

interface Props {
  onApply: (weights: OptimizationWeights) => void
}

export default function OptimizationWeightsPanel({ onApply }: Props) {
  const [weights, setWeights] = useState<OptimizationWeights>(DEFAULTS)

  const setWeight = (key: keyof OptimizationWeights, value: number) => {
    setWeights(prev => ({ ...prev, [key]: value }))
  }

  const normalizedWeights = (): OptimizationWeights => {
    const total = weights.skill_match + weights.salary_fit + weights.experience
    if (total === 0) return DEFAULTS
    return {
      skill_match: weights.skill_match / total,
      salary_fit: weights.salary_fit / total,
      experience: weights.experience / total,
    }
  }

  const labels: { key: keyof OptimizationWeights; label: string }[] = [
    { key: 'skill_match', label: 'Соответствие скиллов' },
    { key: 'salary_fit', label: 'Зарплата в бюджете' },
    { key: 'experience', label: 'Опыт работы' },
  ]

  return (
    <div className="bg-white rounded-xl border p-5 space-y-4">
      <h3 className="font-semibold text-gray-800">Настройки оптимизации</h3>
      <div className="space-y-3">
        {labels.map(({ key, label }) => (
          <div key={key} className="flex items-center gap-3">
            <div className="w-44 text-sm text-gray-700">{label}</div>
            <input
              type="range"
              min={0}
              max={100}
              value={Math.round(weights[key] * 100)}
              onChange={e => setWeight(key, Number(e.target.value) / 100)}
              className="flex-1 accent-blue-600"
            />
            <div className="w-10 text-right text-sm font-medium text-gray-600">
              {Math.round(weights[key] * 100)}%
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-400">
        Нормализованные веса:{' '}
        {Object.entries(normalizedWeights()).map(([k, v]) => `${k}: ${Math.round(v * 100)}%`).join(', ')}
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => onApply(normalizedWeights())}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          Применить
        </button>
        <button
          onClick={() => setWeights(DEFAULTS)}
          className="bg-white border text-gray-600 px-4 py-2 rounded-lg text-sm hover:bg-gray-50"
        >
          Сбросить
        </button>
      </div>
    </div>
  )
}
