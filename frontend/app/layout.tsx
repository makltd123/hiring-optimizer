import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Оптимизатор найма',
  description: 'Оптимальный состав команды за 2 минуты',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru">
      <body className="bg-gray-50 text-gray-900 min-h-screen">{children}</body>
    </html>
  )
}
