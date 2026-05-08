import { Moon, Sun, Bookmark } from 'lucide-react'

export type Tab = 'home' | 'charts' | 'map' | 'saved' | 'table' | 'ai'

interface Props {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  onHome: () => void
  darkMode: boolean
  onToggleDark: () => void
}

const TABS: { id: Tab; label: string; icon?: React.ReactNode }[] = [
  { id: 'charts', label: 'Charts' },
  { id: 'map', label: 'Map' },
  { id: 'saved', label: 'Saved', icon: <Bookmark className="w-3 h-3" /> },
  { id: 'table', label: 'Table' },
  { id: 'ai', label: 'Casota AI' },
]

export function Navbar({ activeTab, onTabChange, onHome, darkMode, onToggleDark }: Props) {
  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm z-10">
      <button
        onClick={onHome}
        className="flex items-center gap-2 hover:opacity-75 transition-opacity"
        aria-label="Go to home"
      >
        {/* Monopoly top hat with apartment windows, slightly tilted */}
        <svg width="30" height="30" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
          <g transform="rotate(-8, 16, 20)">
            {/* Hat body */}
            <rect x="10" y="4" width="13" height="20" rx="2" fill="#1e3a8a" />
            {/* Gold band */}
            <rect x="10" y="19" width="13" height="4" rx="0" fill="#f59e0b" />
            {/* Brim — wide, clearly a hat */}
            <rect x="4" y="22" width="25" height="5" rx="2.5" fill="#1e40af" />
            {/* Windows row 1 */}
            <rect x="12" y="7" width="3.5" height="4" rx="0.8" fill="#bfdbfe" />
            <rect x="17.5" y="7" width="3.5" height="4" rx="0.8" fill="#93c5fd" />
            {/* Windows row 2 */}
            <rect x="12" y="13" width="3.5" height="4" rx="0.8" fill="#93c5fd" />
            <rect x="17.5" y="13" width="3.5" height="4" rx="0.8" fill="#bfdbfe" />
          </g>
        </svg>
        <span className="text-xl font-bold text-gray-900 dark:text-white" style={{ fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.03em' }}>Casota</span>
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
            <span className="flex items-center gap-1">
              {tab.icon}{tab.label}
            </span>
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
