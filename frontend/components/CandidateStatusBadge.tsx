'use client'

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  new: { label: 'Новый', className: 'bg-gray-100 text-gray-700' },
  in_review: { label: 'На рассмотрении', className: 'bg-blue-100 text-blue-700' },
  interview: { label: 'Интервью', className: 'bg-purple-100 text-purple-700' },
  offer: { label: 'Оффер', className: 'bg-orange-100 text-orange-700' },
  hired: { label: 'Принят', className: 'bg-green-100 text-green-700' },
  rejected: { label: 'Отказ', className: 'bg-red-100 text-red-700' },
  archived: { label: 'Архив', className: 'bg-gray-200 text-gray-500' },
  merged: { label: 'Объединён', className: 'bg-yellow-100 text-yellow-700' },
}

interface Props {
  status: string
  onChange?: (newStatus: string) => void
  editable?: boolean
}

export default function CandidateStatusBadge({ status, onChange, editable = false }: Props) {
  const cfg = STATUS_CONFIG[status] || { label: status, className: 'bg-gray-100 text-gray-600' }

  if (editable && onChange) {
    return (
      <select
        value={status}
        onChange={e => onChange(e.target.value)}
        className={`text-xs font-medium px-2 py-1 rounded-full border-0 cursor-pointer ${cfg.className}`}
      >
        {Object.entries(STATUS_CONFIG).map(([key, val]) => (
          <option key={key} value={key}>{val.label}</option>
        ))}
      </select>
    )
  }

  return (
    <span className={`text-xs font-medium px-2 py-1 rounded-full ${cfg.className}`}>
      {cfg.label}
    </span>
  )
}
