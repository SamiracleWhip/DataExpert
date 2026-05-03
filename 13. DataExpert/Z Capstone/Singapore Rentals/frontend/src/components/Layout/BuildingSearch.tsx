import { useState, useRef, useEffect, useCallback } from 'react'
import { Search, X, Clock, Sparkles } from 'lucide-react'
import type { BuildingSuggestion, RecommendedBuilding, SelectedBuilding } from '../../types'
import { MAX_BUILDINGS } from '../../types'
import { api } from '../../lib/api'

const HISTORY_KEY = 'shedza_search_history'
const MAX_HISTORY = 20

interface HistoryEntry {
  id: number
  name: string
  ts: number
}

function loadHistory(): HistoryEntry[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? '[]')
  } catch {
    return []
  }
}

function saveToHistory(id: number, name: string) {
  const existing = loadHistory().filter(h => h.id !== id)
  const updated = [{ id, name, ts: Date.now() }, ...existing].slice(0, MAX_HISTORY)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(updated))
}

function timeAgo(ts: number): string {
  const mins = Math.floor((Date.now() - ts) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function useDebounce<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return debounced
}

interface Props {
  selectedBuildings: SelectedBuilding[]
  onAdd: (id: number, name: string) => void
  onRemove: (id: number) => void
  wide?: boolean
}

export function BuildingSearch({ selectedBuildings, onAdd, onRemove, wide = false }: Props) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState<BuildingSuggestion[]>([])
  const [recommendations, setRecommendations] = useState<RecommendedBuilding[]>([])
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [open, setOpen] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const debouncedQuery = useDebounce(query, 150)
  const atMax = selectedBuildings.length >= MAX_BUILDINGS

  // Fetch search suggestions
  useEffect(() => {
    if (!debouncedQuery.trim() || atMax) {
      setSuggestions([])
      return
    }
    let cancelled = false
    ;(api.buildingSearch(debouncedQuery, 8) as Promise<BuildingSuggestion[]>).then(results => {
      if (!cancelled) {
        setSuggestions(results.filter(r => !selectedBuildings.some(s => s.id === r.id)))
        setActiveIndex(0)
      }
    })
    return () => { cancelled = true }
  }, [debouncedQuery, atMax, selectedBuildings])

  // Fetch recommendations whenever selectedBuildings changes
  useEffect(() => {
    if (selectedBuildings.length === 0) { setRecommendations([]); return }
    const ref = selectedBuildings[selectedBuildings.length - 1]
    const excludeIds = selectedBuildings.map(b => b.id)
    ;(api.buildingRecommend(ref.id, excludeIds, 5) as Promise<RecommendedBuilding[]>)
      .then(setRecommendations)
      .catch(() => setRecommendations([]))
  }, [selectedBuildings])

  const dropdownOpen = open && (suggestions.length > 0 || (!debouncedQuery && history.length > 0))

  const topSuggestion = suggestions[0]
  const ghostSuffix = (() => {
    if (!topSuggestion || !query) return ''
    const proj = topSuggestion.project
    if (proj.toLowerCase().startsWith(query.toLowerCase())) return proj.slice(query.length)
    return ''
  })()

  const commit = useCallback((id: number, name: string) => {
    onAdd(id, name)
    saveToHistory(id, name)
    setHistory(loadHistory())
    setQuery('')
    setSuggestions([])
    setOpen(false)
    inputRef.current?.focus()
  }, [onAdd])

  const handleFocus = () => {
    setHistory(loadHistory())
    setOpen(true)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Tab' && ghostSuffix && suggestions.length > 0) {
      e.preventDefault()
      commit(suggestions[0].id, suggestions[0].project)
      return
    }
    if (!dropdownOpen) return
    const items = debouncedQuery ? suggestions : history
    if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIndex(i => Math.min(i + 1, items.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIndex(i => Math.max(i - 1, 0)) }
    else if (e.key === 'Enter') {
      e.preventDefault()
      if (debouncedQuery && suggestions[activeIndex]) {
        commit(suggestions[activeIndex].id, suggestions[activeIndex].project)
      } else if (!debouncedQuery && history[activeIndex]) {
        const h = history[activeIndex]
        if (!selectedBuildings.some(s => s.id === h.id)) commit(h.id, h.name)
      }
    } else if (e.key === 'Escape') setOpen(false)
  }

  const chipClass = wide
    ? 'flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-400/30'
    : 'flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-400/30'

  const inputCls = wide
    ? 'w-full border border-gray-200 dark:border-gray-600 rounded-xl bg-gray-50 dark:bg-gray-700 text-gray-800 dark:text-gray-100 text-sm px-4 py-2.5 pr-10 outline-none focus:border-blue-400 focus:bg-white dark:focus:bg-gray-600 transition-colors'
    : 'w-44 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 text-xs px-2.5 py-1 pr-6 outline-none focus:border-blue-400 transition-colors'

  const dropdownCls = wide
    ? 'absolute left-0 right-0 top-full mt-1 z-[2000] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl shadow-xl overflow-hidden'
    : 'absolute left-0 top-full mt-1 z-[2000] w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg overflow-hidden'

  const itemCls = (active: boolean) =>
    `px-4 py-2.5 cursor-pointer ${wide ? 'text-sm' : 'text-xs'} ${
      active ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
             : 'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'
    }`

  return (
    <div className={`flex flex-col gap-2 ${wide ? 'w-full' : ''}`}>

      {/* Selected chips */}
      {selectedBuildings.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedBuildings.map(b => (
            <span key={b.id} className={chipClass}>
              <span className="truncate max-w-[180px]">{b.name}</span>
              <button onClick={() => onRemove(b.id)} className="hover:opacity-70 flex-shrink-0">
                <X className={wide ? 'w-3.5 h-3.5' : 'w-3 h-3'} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input */}
      {!atMax ? (
        <div className="flex flex-col gap-0">
          <div className={`relative flex items-center gap-1.5`}>
            {!wide && (
              <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide shrink-0">
                Building
              </span>
            )}
            <div className={`relative ${wide ? 'w-full' : ''}`}>
              {/* Ghost text */}
              <div aria-hidden className={`absolute inset-0 flex items-center ${wide ? 'px-4' : 'px-2.5'} pointer-events-none ${wide ? 'text-sm' : 'text-xs'} whitespace-nowrap overflow-hidden`}>
                <span className="invisible">{query}</span>
                <span className="text-gray-400 dark:text-gray-500">{ghostSuffix}</span>
              </div>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={handleFocus}
                onBlur={() => setTimeout(() => setOpen(false), 150)}
                placeholder={wide ? 'Search condo or building name…' : 'Add building…'}
                className={inputCls}
              />
              <Search className={`absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none ${wide ? 'w-4 h-4' : 'w-3 h-3'}`} />

              {/* Dropdown: live suggestions OR history */}
              {dropdownOpen && (
                <ul ref={listRef} className={dropdownCls}>
                  {debouncedQuery ? (
                    <>
                      {suggestions.map((s, i) => (
                        <li key={s.id} onMouseDown={() => commit(s.id, s.project)} onMouseEnter={() => setActiveIndex(i)} className={itemCls(i === activeIndex)}>
                          <span className="font-medium">{s.project}</span>
                          <span className="text-gray-400 dark:text-gray-500 ml-2">{s.street}</span>
                        </li>
                      ))}
                      {ghostSuffix && (
                        <li className={`px-4 py-2 border-t border-gray-100 dark:border-gray-700 ${wide ? 'text-xs' : 'text-[10px]'} text-gray-400`}>
                          Press <kbd className="font-mono bg-gray-100 dark:bg-gray-700 px-1 rounded">Tab</kbd> to complete
                        </li>
                      )}
                    </>
                  ) : (
                    <>
                      <li className="px-4 pt-2.5 pb-1 flex items-center gap-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider">
                        <Clock className="w-3 h-3" /> Recent
                      </li>
                      {history.filter(h => !selectedBuildings.some(s => s.id === h.id)).slice(0, 5).map((h, i) => (
                        <li key={h.id} onMouseDown={() => commit(h.id, h.name)} onMouseEnter={() => setActiveIndex(i)} className={itemCls(i === activeIndex)}>
                          <span className="font-medium truncate">{h.name}</span>
                          <span className="text-gray-400 dark:text-gray-500 ml-2 text-[10px]">{timeAgo(h.ts)}</span>
                        </li>
                      ))}
                    </>
                  )}
                </ul>
              )}
            </div>
            {wide && selectedBuildings.length > 0 && (
              <span className="text-xs text-gray-400 whitespace-nowrap">{selectedBuildings.length}/{MAX_BUILDINGS}</span>
            )}
          </div>
        </div>
      ) : (
        <p className={`text-gray-400 dark:text-gray-500 ${wide ? 'text-sm' : 'text-xs'}`}>
          Max {MAX_BUILDINGS} buildings selected
        </p>
      )}

      {/* Recommendations — shown below search when ≥1 building selected */}
      {wide && recommendations.length > 0 && !atMax && (
        <div className="mt-1">
          <p className="flex items-center gap-1.5 text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1.5">
            <Sparkles className="w-3 h-3 text-yellow-500" /> Similar buildings to compare
          </p>
          <div className="flex flex-wrap gap-1.5">
            {recommendations.map(r => (
              <button
                key={r.id}
                onMouseDown={() => commit(r.id, r.project)}
                className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-700 hover:bg-amber-100 dark:hover:bg-amber-900/40 transition-colors"
              >
                <Sparkles className="w-2.5 h-2.5" />
                <span className="truncate max-w-[160px]">{r.project}</span>
                <span className="text-amber-500 dark:text-amber-500">${Math.round(r.avg_rent / 1000)}k</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
