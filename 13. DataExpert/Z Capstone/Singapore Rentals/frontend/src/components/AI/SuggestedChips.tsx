const SUGGESTIONS = [
  "What's the average rent for a 2BR in District 10?",
  "Which districts have the best value right now?",
  "Show me buildings near Orchard MRT",
  "How have rents trended in 2024 vs 2023?",
  "Find deals — buildings priced 10%+ below market",
  "How does District 15 compare to District 16?",
]

export function SuggestedChips({ onSelect }: { onSelect: (q: string) => void }) {
  return (
    <div className="flex flex-col items-center gap-4 py-10 px-4">
      <p className="text-sm text-gray-400 dark:text-gray-500">Try asking…</p>
      <div className="flex flex-wrap justify-center gap-2 max-w-xl">
        {SUGGESTIONS.map(q => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="px-3 py-2 text-sm rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-750 hover:border-blue-300 dark:hover:border-blue-600 transition-colors text-left"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
