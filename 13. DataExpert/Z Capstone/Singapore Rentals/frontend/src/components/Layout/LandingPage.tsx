import { useState, useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import type { Filters, MrtStation } from '../../types'
import { BuildingSearch } from './BuildingSearch'
import { DateRangeSlider } from './DateRangeSlider'
import { DistrictMap } from './DistrictMap'
import { MrtFilter } from './MrtFilter'

// ── Typewriter ────────────────────────────────────────────────────────────────

const PHRASES = [
  'Hi, what are you looking for?',
  'Find your perfect rental deal.',
  'Compare rents across 28 districts.',
  'Discover Singapore rental trends.',
]

function useTypewriter(phrases: string[]) {
  const [text, setText] = useState('')
  const [phraseIdx, setPhraseIdx] = useState(0)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    const current = phrases[phraseIdx]

    if (!deleting && text === current) {
      const t = setTimeout(() => setDeleting(true), 900)
      return () => clearTimeout(t)
    }
    if (deleting && text === '') {
      setDeleting(false)
      setPhraseIdx(i => (i + 1) % phrases.length)
      return
    }

    const speed = deleting ? 28 : 52
    const next = deleting
      ? text.slice(0, -1)
      : current.slice(0, text.length + 1)
    const t = setTimeout(() => setText(next), speed)
    return () => clearTimeout(t)
  }, [text, deleting, phraseIdx, phrases])

  return text
}

// ── Filter helpers ────────────────────────────────────────────────────────────

const BEDROOM_OPTIONS = [
  { label: 'Studio', value: '00' },
  { label: '1 BR', value: '1' },
  { label: '2 BR', value: '2' },
  { label: '3 BR', value: '3' },
  { label: '4 BR', value: '4' },
  { label: '5 BR+', value: '5' },
]

const PROPERTY_TYPE_OPTIONS = [
  { label: 'Non-landed', value: 'Non-landed Properties' },
  { label: 'Exec Condo', value: 'Executive Condominium' },
  { label: 'Terrace', value: 'Terrace House' },
]

function Label({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-widest mb-2">
      {children}
    </p>
  )
}

function Chip({ active, onClick, children }: {
  active: boolean; onClick: () => void; children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all whitespace-nowrap ${
        active
          ? 'bg-blue-500 text-white border-blue-500'
          : 'bg-transparent text-gray-500 dark:text-gray-400 border-gray-200 dark:border-gray-600 hover:border-blue-400 hover:text-blue-500'
      }`}
    >
      {children}
    </button>
  )
}

// ── Props ─────────────────────────────────────────────────────────────────────

interface Props {
  filters: Filters
  allStations: MrtStation[]
  onToggleArrayItem: (key: 'districts' | 'bedrooms' | 'propertyTypes' | 'stations', item: string) => void
  onUpdateFilter: <K extends keyof Filters>(key: K, value: Filters[K]) => void
  onAddBuilding: (id: number, name: string) => void
  onRemoveBuilding: (id: number) => void
  onReset: () => void
  hasActiveFilters: boolean
  onSearch: () => void
}

// ── Component ─────────────────────────────────────────────────────────────────

export function LandingPage({
  filters,
  allStations,
  onToggleArrayItem,
  onUpdateFilter,
  onAddBuilding,
  onRemoveBuilding,
  onReset,
  hasActiveFilters,
  onSearch,
}: Props) {
  const displayed = useTypewriter(PHRASES)
  const cursorRef = useRef(true)

  // Blinking cursor
  const [showCursor, setShowCursor] = useState(true)
  useEffect(() => {
    const t = setInterval(() => setShowCursor(s => !s), 530)
    return () => clearInterval(t)
  }, [])

  void cursorRef

  return (
    <div className="flex-1 flex overflow-hidden bg-gray-50 dark:bg-gray-900">

      {/* ── Left column: CTA + filters ── */}
      <div className="w-1/2 flex-shrink-0 flex flex-col overflow-y-auto px-8 py-6 gap-4 border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">

        {/* CTA */}
        <div className="mb-1">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white leading-snug min-h-[5rem]">
            {displayed}
            <span className={`inline-block w-0.5 h-7 ml-0.5 align-middle bg-blue-500 transition-opacity ${showCursor ? 'opacity-100' : 'opacity-0'}`} />
          </h1>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            336,751 contracts · 4,230 buildings · 2022–2026
          </p>
        </div>

        <div className="w-full h-px bg-gray-100 dark:bg-gray-800" />

        {/* Building search */}
        <div>
          <Label>Building / Condo</Label>
          <BuildingSearch
            selectedBuildings={filters.selectedBuildings}
            onAdd={onAddBuilding}
            onRemove={onRemoveBuilding}
            wide
          />
        </div>

        {/* Property type */}
        <div>
          <Label>Property Type</Label>
          <div className="flex flex-wrap gap-1.5">
            {PROPERTY_TYPE_OPTIONS.map(opt => (
              <Chip
                key={opt.value}
                active={filters.propertyTypes.includes(opt.value)}
                onClick={() => onToggleArrayItem('propertyTypes', opt.value)}
              >
                {opt.label}
              </Chip>
            ))}
          </div>
        </div>

        {/* Bedrooms */}
        <div>
          <Label>Bedrooms</Label>
          <div className="flex flex-wrap gap-1.5">
            {BEDROOM_OPTIONS.map(opt => (
              <Chip
                key={opt.value}
                active={filters.bedrooms.includes(opt.value)}
                onClick={() => onToggleArrayItem('bedrooms', opt.value)}
              >
                {opt.label}
              </Chip>
            ))}
          </div>
        </div>

        {/* Area */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <Label>Area</Label>
            {/* m² / ft² toggle */}
            <button
              onClick={() => onUpdateFilter('areaUnit', filters.areaUnit === 'sqm' ? 'sqft' : 'sqm')}
              className="flex items-center gap-0.5 text-xs text-gray-400 dark:text-gray-500 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
            >
              <span className={`px-1.5 py-0.5 rounded font-medium ${filters.areaUnit === 'sqm' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400' : ''}`}>m²</span>
              <span className="text-gray-300 dark:text-gray-600">/</span>
              <span className={`px-1.5 py-0.5 rounded font-medium ${filters.areaUnit === 'sqft' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400' : ''}`}>ft²</span>
            </button>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="number"
              placeholder={`Min ${filters.areaUnit === 'sqm' ? '(sqm)' : '(sqft)'}`}
              value={filters.areaMin}
              onChange={e => onUpdateFilter('areaMin', e.target.value)}
              className="flex-1 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:border-blue-400"
            />
            <span className="text-gray-400 text-sm">–</span>
            <input
              type="number"
              placeholder={`Max ${filters.areaUnit === 'sqm' ? '(sqm)' : '(sqft)'}`}
              value={filters.areaMax}
              onChange={e => onUpdateFilter('areaMax', e.target.value)}
              className="flex-1 border border-gray-200 dark:border-gray-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200 placeholder-gray-400 focus:outline-none focus:border-blue-400"
            />
          </div>
        </div>

        {/* MRT proximity */}
        <div>
          <Label>Near MRT Station (≤15 min walk)</Label>
          <MrtFilter
            allStations={allStations}
            selectedStations={filters.stations}
            onToggle={name => onToggleArrayItem('stations', name)}
          />
        </div>

        {/* Date range */}
        <div>
          <Label>Date Range</Label>
          <DateRangeSlider
            dateFrom={filters.dateFrom}
            dateTo={filters.dateTo}
            onChange={(from, to) => {
              onUpdateFilter('dateFrom', from)
              onUpdateFilter('dateTo', to)
            }}
          />
        </div>

        {/* Spacer pushes button to bottom */}
        <div className="flex-1" />

        {/* CTA button */}
        <div className="flex flex-col gap-2 pb-1">
          <button
            onClick={onSearch}
            className="w-full py-3 bg-blue-500 hover:bg-blue-600 active:bg-blue-700 text-white font-semibold text-base rounded-xl shadow transition-all"
          >
            Explore Rentals →
          </button>
          {hasActiveFilters && (
            <button
              onClick={onReset}
              className="flex items-center justify-center gap-1 text-xs text-gray-400 hover:text-red-500 dark:hover:text-red-400 transition-colors"
            >
              <X className="w-3 h-3" />
              Clear all filters
            </button>
          )}
        </div>
      </div>

      {/* ── Right column: district map ── */}
      <div className="w-1/2 flex flex-col overflow-hidden">
        <DistrictMap
          selectedDistricts={filters.districts}
          onToggle={d => onToggleArrayItem('districts', d)}
        />
      </div>

    </div>
  )
}
