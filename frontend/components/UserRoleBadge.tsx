import { UserRole } from '@/lib/types'

const CONFIG: Record<UserRole, { label: string; className: string }> = {
  admin:        { label: 'Администратор', className: 'bg-red-50 text-red-700 border-red-200' },
  org_admin:    { label: 'HR-директор',   className: 'bg-purple-50 text-purple-700 border-purple-200' },
  dept_manager: { label: 'Рук. отдела',   className: 'bg-blue-50 text-blue-700 border-blue-200' },
  hr_manager:   { label: 'HR-менеджер',   className: 'bg-indigo-50 text-indigo-700 border-indigo-200' },
  viewer:       { label: 'Наблюдатель',   className: 'bg-gray-50 text-gray-500 border-gray-200' },
}

export default function UserRoleBadge({ role }: { role: UserRole }) {
  const cfg = CONFIG[role] ?? CONFIG.viewer
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cfg.className}`}>
      {cfg.label}
    </span>
  )
}
