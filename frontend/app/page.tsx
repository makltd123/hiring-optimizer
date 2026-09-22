import Link from 'next/link'

export default function Landing() {
  return (
    <main className="min-h-screen flex flex-col">
      <header className="flex items-center justify-between px-8 py-4 bg-white shadow-sm">
        <span className="text-xl font-bold text-blue-600">HireOpt</span>
        <div className="flex gap-4">
          <Link href="/auth/login" className="text-sm text-gray-600 hover:text-gray-900">Войти</Link>
          <Link href="/auth/register" className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
            Попробовать бесплатно
          </Link>
        </div>
      </header>

      <section className="flex-1 flex flex-col items-center justify-center text-center px-4 py-24">
        <h1 className="text-5xl font-extrabold text-gray-900 mb-6 max-w-2xl leading-tight">
          Оптимальный состав команды за 2 минуты
        </h1>
        <p className="text-xl text-gray-500 mb-10 max-w-xl">
          Загрузите резюме, задайте вакансии — система подберёт лучший состав с помощью венгерского алгоритма.
        </p>
        <Link href="/auth/register" className="bg-blue-600 text-white px-8 py-4 rounded-xl text-lg font-semibold hover:bg-blue-700 transition">
          Попробовать бесплатно
        </Link>
      </section>

      <section className="bg-white py-16 px-4">
        <h2 className="text-2xl font-bold text-center mb-12">Как это работает</h2>
        <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { step: '1', title: 'Загрузите резюме', desc: 'Drag & drop PDF-файлы. Система анонимизирует ПДн перед обработкой.' },
            { step: '2', title: 'Задайте вакансии', desc: 'Укажите роли, требуемые навыки и зарплатный бюджет.' },
            { step: '3', title: 'Получите результат', desc: 'Алгоритм подбирает оптимальный состав команды с объяснением.' },
          ].map(({ step, title, desc }) => (
            <div key={step} className="text-center p-6 rounded-xl border border-gray-100">
              <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xl font-bold mx-auto mb-4">{step}</div>
              <h3 className="font-semibold text-lg mb-2">{title}</h3>
              <p className="text-gray-500 text-sm">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-16 px-4 text-center bg-gray-50">
        <h2 className="text-2xl font-bold mb-8">Тарифы</h2>
        <div className="max-w-3xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { name: 'Бесплатно', price: '0 ₽', features: ['1 проект', '3 вакансии', '10 кандидатов'] },
            { name: 'Старт', price: '2 900 ₽/мес', features: ['Безлимит проектов', '50 вакансий', '200 кандидатов'], highlight: true },
            { name: 'Бизнес', price: '7 900 ₽/мес', features: ['Безлимит проектов', '50 вакансий', '200 кандидатов'] },
          ].map(({ name, price, features, highlight }) => (
            <div key={name} className={`p-6 rounded-xl border ${highlight ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white'}`}>
              <h3 className="font-bold text-lg mb-1">{name}</h3>
              <p className="text-2xl font-extrabold text-blue-600 mb-4">{price}</p>
              <ul className="text-sm text-gray-600 space-y-1">
                {features.map(f => <li key={f}>• {f}</li>)}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <footer className="text-center py-6 text-sm text-gray-400">
        © 2024 HireOpt
      </footer>
    </main>
  )
}
