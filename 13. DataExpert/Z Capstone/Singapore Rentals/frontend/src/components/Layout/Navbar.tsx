import { Moon, Sun, MapPin } from 'lucide-react'

export type Tab = 'home' | 'map' | 'charts' | 'table'

interface Props {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  onHome: () => void
  darkMode: boolean
  onToggleDark: () => void
}

const TABS: { id: Tab; label: string }[] = [
  { id: 'charts', label: 'Charts' },
  { id: 'map', label: 'Map' },
  { id: 'table', label: 'Table' },
]

export function Navbar({ activeTab, onTabChange, onHome, darkMode, onToggleDark }: Props) {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm z-10">
      <button
        onClick={onHome}
        className="flex items-center gap-2 hover:opacity-75 transition-opacity"
        aria-label="Go to home"
      >
        <MapPin className="w-6 h-6 text-blue-500" />
        <span className="text-xl font-bold text-gray-900 dark:text-white" style={{ fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.03em' }}>Shedza</span>
      </button>

      <nav className="flex gap-1">
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? 'bg-blue-500 text-white'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <button
        onClick={onToggleDark}
        className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300 transition-colors"
        aria-label="Toggle dark mode"
      >
        {darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
      </button>
    </header>
  )
}
