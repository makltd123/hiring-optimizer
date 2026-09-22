'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import api from '@/lib/api'
import { isAuthenticated } from '@/lib/auth'
import VacancyForm from '@/components/VacancyForm'
import FileUpload from '@/components/FileUpload'
import ResultTable from '@/components/ResultTable'
import MatchMatrix from '@/components/MatchMatrix'
import Simulator from '@/components/Simulator'
import SkillGap from '@/components/SkillGap'
import ReserveList from '@/components/ReserveList'
import OptimizationWeightsPanel from '@/components/OptimizationWeights'
import BudgetChart from '@/components/BudgetChart'
import type { ProjectDetail, Vacancy, Candidate, OptimizationResult, OptimizationWeights, IntegrationStatus, AsyncTaskStatus } from '@/lib/types'

type Tab = 'vacancies' | 'candidates' | 'result' | 'simulator'

export default function ProjectPage() {
  const router = useRouter()
  const params = useParams()
  const projectId = Number(params.id)

  const [project, setProject] = useState<ProjectDetail | null>(null)
  const [vacancies, setVacancies] = useState<Vacancy[]>([])
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [result, setResult] = useState<OptimizationResult | null>(null)
  const [tab, setTab] = useState<Tab>('vacancies')
  const [optimizing, setOptimizing] = useState(false)
  const [optError, setOptError] = useState('')
  const [loading, setLoading] = useState(true)

  const loadProject = useCallback(async () => {
    try {
      const { data } = await api.get<ProjectDetail>(`/projects/${projectId}`)
      setProject(data)
      setVacancies(data.vacancies)
      setCandidates(data.candidates)
    } catch {
      router.push('/dashboard')
    } finally {
      setLoading(false)
    }
  }, [projectId, router])

  useEffect(() => {
    if (!isAuthenticated()) { router.push('/auth/login'); return }
    loadProject()
    api.get(`/projects/${projectId}/results`).then(r => setResult(r.data)).catch(() => {})
  }, [projectId, router, loadProject])

  async function refreshCandidates() {
    const { data } = await api.get(`/projects/${projectId}/candidates`)
    setCandidates(data)
  }

  const [pendingWeights, setPendingWeights] = useState<OptimizationWeights | null>(null)
  const [integrations, setIntegrations] = useState<IntegrationStatus | null>(null)
  const [importingEmail, setImportingEmail] = useState(false)
  const [asyncTask, setAsyncTask] = useState<AsyncTaskStatus | null>(null)

  useEffect(() => {
    api.get('/integrations/status').then(r => setIntegrations(r.data)).catch(() => {})
  }, [projectId])

  async function importFromEmail() {
    setImportingEmail(true)
    try {
      const res = await api.post(`/integrations/projects/${projectId}/import/email`)
      alert(`Импортировано: ${res.data.imported_count} кандидатов`)
      await refreshCandidates()
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка импорта')
    } finally {
      setImportingEmail(false)
    }
  }

  async function optimizeAsync(weights?: OptimizationWeights) {
    setOptimizing(true)
    setOptError('')
    setAsyncTask({ state: 'queued', progress: 0 })
    try {
      const body = weights ? { weights } : {}
      const res = await api.post(`/projects/${projectId}/optimize/async`, body)
      const taskId: string = res.data.task_id
      // Polling статуса каждые 2 секунды
      const poll = setInterval(async () => {
        try {
          const statusRes = await api.get(`/projects/${projectId}/optimize/status/${taskId}`)
          const st: AsyncTaskStatus = statusRes.data
          setAsyncTask(st)
          if (st.state === 'done') {
            clearInterval(poll)
            setOptimizing(false)
            const resultRes = await api.get(`/projects/${projectId}/results`)
            setResult(resultRes.data)
            setTab('result')
          } else if (st.state === 'error') {
            clearInterval(poll)
            setOptimizing(false)
            setOptError(st.error || 'Ошибка асинхронной оптимизации')
          }
        } catch {
          clearInterval(poll)
          setOptimizing(false)
        }
      }, 2000)
    } catch (e: any) {
      setOptError(e.response?.data?.detail || 'Ошибка запуска задачи')
      setOptimizing(false)
      setAsyncTask(null)
    }
  }

  async function optimize(weights?: OptimizationWeights) {
    setOptimizing(true)
    setOptError('')
    try {
      const body = weights ? { weights } : {}
      const { data } = await api.post(`/projects/${projectId}/optimize`, body)
      setResult(data)
      setTab('result')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setOptError(typeof detail === 'string' ? detail : 'Ошибка оптимизации')
    } finally {
      setOptimizing(false)
    }
  }

  const canOptimize = vacancies.length > 0 && candidates.filter(c => c.parse_status === 'ready').length > 0

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Загрузка...</div>

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm px-8 py-4 flex items-center gap-4">
        <Link href="/dashboard" className="text-gray-400 hover:text-gray-700 text-sm">← Назад</Link>
        <h1 className="font-bold text-lg">{project?.title}</h1>
        {project?.fot_limit && (
          <span className="text-sm text-gray-400">ФОТ: {project.fot_limit.toLocaleString('ru')} ₽</span>
        )}
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex border-b mb-6">
          {([
            ['vacancies', `Вакансии (${vacancies.length})`],
            ['candidates', `Кандидаты (${candidates.length})`],
            ['result', 'Результат'],
            ['simulator', 'Симулятор'],
          ] as [Tab, string][]).map(([t, label]) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-5 py-3 text-sm font-medium border-b-2 -mb-px transition ${tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'vacancies' && (
          <VacancyForm
            projectId={projectId}
            vacancies={vacancies}
            onAdded={v => setVacancies(prev => [...prev, v])}
            onDeleted={id => setVacancies(prev => prev.filter(v => v.id !== id))}
          />
        )}

        {tab === 'candidates' && (
          <div className="space-y-4">
            {/* Кнопки импорта (если интеграции настроены) */}
            {(integrations?.email === 'configured') && (
              <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-xl border border-blue-100">
                <span className="text-sm text-blue-700 font-medium">Email IMAP подключён</span>
                <button
                  onClick={importFromEmail}
                  disabled={importingEmail}
                  className="bg-blue-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium disabled:opacity-50"
                >
                  {importingEmail ? 'Импортируем...' : 'Импортировать с почты'}
                </button>
              </div>
            )}
            <FileUpload
              projectId={projectId}
              candidates={candidates}
              onUploaded={c => setCandidates(prev => [...prev, c])}
              onRefresh={refreshCandidates}
            />
          </div>
        )}

        {tab === 'result' && (
          <div className="space-y-6">
            <OptimizationWeightsPanel
              onApply={w => {
                setPendingWeights(w)
                optimize(w)
              }}
            />

            <div className="flex items-center gap-4 flex-wrap">
              <button
                onClick={() => optimize(pendingWeights ?? undefined)}
                disabled={!canOptimize || optimizing}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {optimizing && !asyncTask ? 'Оптимизация...' : 'Оптимизировать'}
              </button>
              {candidates.filter(c => c.parse_status === 'ready').length >= 200 && (
                <button
                  onClick={() => optimizeAsync(pendingWeights ?? undefined)}
                  disabled={!canOptimize || optimizing}
                  className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Асинхронная оптимизация через Celery — для больших проектов"
                >
                  {optimizing && asyncTask ? `${asyncTask.stage || 'Обработка'}... ${asyncTask.progress}%` : 'Запустить асинхронно'}
                </button>
              )}
              {!canOptimize && (
                <p className="text-sm text-gray-400">Нужна минимум 1 вакансия и 1 готовый кандидат</p>
              )}
              {optError && <p className="text-red-500 text-sm">{optError}</p>}
            </div>
            {asyncTask && asyncTask.state === 'running' && (
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-indigo-600 h-2 rounded-full transition-all" style={{ width: `${asyncTask.progress}%` }} />
              </div>
            )}

            {result && (
              <>
                <ResultTable result={result} vacancies={vacancies} candidates={candidates} projectId={projectId} />
                <MatchMatrix result={result} vacancies={vacancies} candidates={candidates} />
                <SkillGap projectId={projectId} />
                <ReserveList projectId={projectId} />
                <BudgetChart projectId={projectId} />
              </>
            )}

            {!result && !optimizing && (
              <div className="text-center py-16 text-gray-400">
                <p>Нажмите «Оптимизировать» для получения результата</p>
              </div>
            )}
          </div>
        )}

        {tab === 'simulator' && (
          <div className="space-y-6">
            {result ? (
              <Simulator
                projectId={projectId}
                candidates={candidates.filter(c => c.parse_status === 'ready')}
                vacancies={vacancies}
                baseResult={result}
              />
            ) : (
              <div className="text-center py-16 text-gray-400">
                <p>Сначала запустите оптимизацию во вкладке «Результат»</p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
