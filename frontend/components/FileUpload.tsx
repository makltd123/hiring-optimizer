'use client'

import { useRef, useState } from 'react'
import api from '@/lib/api'
import type { Candidate } from '@/lib/types'
import CandidateStatusBadge from './CandidateStatusBadge'
import HRComments from './HRComments'

interface Props {
  projectId: number
  candidates: Candidate[]
  onUploaded: (c: Candidate) => void
  onRefresh: () => void
}

export default function FileUpload({ projectId, candidates, onUploaded, onRefresh }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [commentsCandidateId, setCommentsCandidateId] = useState<number | null>(null)

  async function uploadFile(file: File) {
    setUploading(true)
    setError('')
    const form = new FormData()
    form.append('file', file)
    try {
      const { data } = await api.post(`/projects/${projectId}/candidates/upload`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      onUploaded(data)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      if (typeof detail === 'object' && detail !== null && 'upgrade_required' in detail) {
        setError('Достигнут лимит кандидатов. Обновите план.')
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError('Ошибка загрузки файла')
      }
    } finally {
      setUploading(false)
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) uploadFile(file)
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) uploadFile(file)
  }

  const statusColor = { parsing: 'text-yellow-600', ready: 'text-green-600', error: 'text-red-500' }
  const statusLabel = { parsing: 'Парсинг...', ready: 'Готов', error: 'Ошибка' }

  return (
    <div className="space-y-6">
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition ${dragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'}`}
      >
        <input ref={inputRef} type="file" accept=".pdf,.txt" onChange={handleChange} className="hidden" />
        {uploading ? (
          <p className="text-blue-600 font-medium">Загрузка и обработка...</p>
        ) : (
          <>
            <p className="text-gray-500 mb-1">Перетащите PDF или TXT сюда</p>
            <p className="text-sm text-gray-400">или кликните для выбора файла</p>
          </>
        )}
      </div>

      {error && <p className="text-red-500 text-sm">{error}</p>}

      {candidates.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold">Кандидаты ({candidates.length})</h3>
            <button onClick={onRefresh} className="text-sm text-blue-600 hover:underline">Обновить статусы</button>
          </div>
          {candidates.map(c => (
            <div key={c.id} className="bg-white rounded-xl border p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="font-medium">{c.display_name}</p>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold ${statusColor[c.parse_status as keyof typeof statusColor]}`}>
                    {statusLabel[c.parse_status as keyof typeof statusLabel]}
                  </span>
                  <CandidateStatusBadge
                    status={c.workflow_status || 'new'}
                    editable
                    onChange={async (newStatus) => {
                      try {
                        await api.patch(`/candidates/${c.id}/status`, { status: newStatus })
                        onRefresh()
                      } catch { /* ignore */ }
                    }}
                  />
                </div>
              </div>
              {c.parsed_skills?.skills && c.parsed_skills.skills.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-2">
                  {c.parsed_skills.skills.slice(0, 10).map(s => (
                    <span key={s} className="bg-green-50 text-green-700 text-xs px-2 py-0.5 rounded">{s}</span>
                  ))}
                  {c.parsed_skills.skills.length > 10 && (
                    <span className="text-xs text-gray-400">+{c.parsed_skills.skills.length - 10}</span>
                  )}
                </div>
              )}
              {c.salary_expectation && (
                <p className="text-sm text-gray-500 mt-1">{c.salary_expectation.toLocaleString('ru')} ₽/мес</p>
              )}
              {c.parsed_skills?.summary && (
                <p className="text-xs text-gray-400 mt-1">{c.parsed_skills.summary}</p>
              )}
              {c.parsed_skills?._possible_duplicates && c.parsed_skills._possible_duplicates.length > 0 && (
                <p className="text-xs text-orange-500 mt-1">
                  ⚠ Возможный дубликат: {c.parsed_skills._possible_duplicates[0].display_name}
                </p>
              )}
              <button
                onClick={() => setCommentsCandidateId(c.id)}
                className="mt-2 text-xs text-blue-500 hover:text-blue-700"
              >
                Комментарии HR
              </button>
            </div>
          ))}
        </div>
      )}
    </div>

    {commentsCandidateId !== null && (
      <HRComments
        candidateId={commentsCandidateId}
        onClose={() => setCommentsCandidateId(null)}
      />
    )}
  </div>
  )
}
