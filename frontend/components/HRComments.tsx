'use client'

import { useState, useEffect } from 'react'
import api from '@/lib/api'

interface Comment {
  id: number
  candidate_id: number
  user_id: number
  text: string
  is_private: boolean
  created_at: string
  updated_at?: string
}

interface Props {
  candidateId: number
  onClose: () => void
}

export default function HRComments({ candidateId, onClose }: Props) {
  const [comments, setComments] = useState<Comment[]>([])
  const [text, setText] = useState('')
  const [isPrivate, setIsPrivate] = useState(false)
  const [loading, setLoading] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editText, setEditText] = useState('')

  useEffect(() => {
    loadComments()
  }, [candidateId])

  async function loadComments() {
    try {
      const { data } = await api.get(`/candidates/${candidateId}/comments`)
      setComments(data)
    } catch {
      // ignore
    }
  }

  async function addComment(e: React.FormEvent) {
    e.preventDefault()
    if (!text.trim()) return
    setLoading(true)
    try {
      await api.post(`/candidates/${candidateId}/comments`, { text, is_private: isPrivate })
      setText('')
      await loadComments()
    } finally {
      setLoading(false)
    }
  }

  async function deleteComment(id: number) {
    try {
      await api.delete(`/candidates/${candidateId}/comments/${id}`)
      setComments(c => c.filter(x => x.id !== id))
    } catch {
      // ignore
    }
  }

  async function saveEdit(id: number) {
    try {
      await api.put(`/candidates/${candidateId}/comments/${id}`, { text: editText })
      setEditingId(null)
      await loadComments()
    } catch {
      // ignore
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 flex flex-col max-h-[80vh]">
        <div className="flex items-center justify-between px-6 py-4 border-b">
          <h2 className="text-lg font-semibold">Комментарии HR</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        {/* Список комментариев */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
          {comments.length === 0 && (
            <p className="text-gray-400 text-sm text-center py-4">Комментариев пока нет</p>
          )}
          {comments.map(c => (
            <div key={c.id} className={`rounded-lg p-3 ${c.is_private ? 'bg-yellow-50 border border-yellow-200' : 'bg-gray-50 border'}`}>
              {editingId === c.id ? (
                <div className="space-y-2">
                  <textarea
                    value={editText}
                    onChange={e => setEditText(e.target.value)}
                    className="w-full border rounded px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
                    rows={3}
                  />
                  <div className="flex gap-2">
                    <button onClick={() => saveEdit(c.id)} className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700">
                      Сохранить
                    </button>
                    <button onClick={() => setEditingId(null)} className="text-xs text-gray-500 hover:text-gray-700">
                      Отмена
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{c.text}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-gray-400">
                      {new Date(c.created_at).toLocaleString('ru-RU')}
                      {c.is_private && <span className="ml-2 text-yellow-600">🔒 Приватный</span>}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => { setEditingId(c.id); setEditText(c.text) }}
                        className="text-xs text-blue-500 hover:text-blue-700"
                      >
                        Изменить
                      </button>
                      <button onClick={() => deleteComment(c.id)} className="text-xs text-red-400 hover:text-red-600">
                        Удалить
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>

        {/* Форма добавления */}
        <div className="border-t px-6 py-4">
          <form onSubmit={addComment} className="space-y-3">
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              placeholder="Добавить комментарий..."
              rows={3}
              required
              className="w-full border rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-400"
            />
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={isPrivate}
                  onChange={e => setIsPrivate(e.target.checked)}
                  className="w-4 h-4"
                />
                Приватный (только для меня)
              </label>
              <button
                type="submit"
                disabled={loading || !text.trim()}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? 'Отправка...' : 'Добавить'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
