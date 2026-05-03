import { X } from 'lucide-react'
import type { Filters, MrtStation } from '../../types'
import { BuildingSearch } from './BuildingSearch'
import { DateRangeSlider } from './DateRangeSlider'
import { MrtFilter } from './MrtFilter'

const DISTRICT_COLORS: Record<string, string> = {
  '01':'#f87171','02':'#fb923c','03':'#fbbf24','04':'#facc15','05':'#a3e635',
  '06':'#4ade80','07':'#34d399','08':'#2dd4bf','09':'#22d3ee','10':'#38bdf8',
  '11':'#60a5fa','12':'#818cf8','13':'#a78bfa','14':'#c084fc','15':'#e879f9',
  '16':'#f472b6','17':'#fb7185','18':'#ff8c42','19':'#ffe066','20':'#b8e04a',
  '21':'#52e5a0','22':'#4fd1c5','23':'#63b3ed','24':'#9f7aea','25':'#ed64a6',
  '26':'#fc8181','27':'#68d391','28':'#76e4f7',
}

interface Props {
  filters: Filters
  allStations: MrtStation[]
  onToggleArrayItem: (key: 'districts' | 'bedrooms' | 'propertyTypes' | 'stations', item: string) => void
  onUpdateFilter: <K extends keyof Filters>(key: K, value: Filters[K]) => void
  onReset: () => void
  hasActiveFilters: boolean
  onAddBuilding: (id: number, name: string) => void
  onRemoveBuilding: (id: number) => void
}

const BEDROOM_OPTIONS = [
  { label: 'Studio', value: '00' },
  { label: '1BR', value: '1' },
  { label: '2BR', value: '2' },
  { label: '3BR', value: '3' },
  { label: '4BR', value: '4' },
  { label: '5BR+', value: '5' },
]

const PROPERTY_TYPE_OPTIONS = [
  { label: 'Non-landed', value: 'Non-landed Properties' },
  { label: 'EC', value: 'Executive Condominium' },
  { label: 'Terrace', value: 'Terrace House' },
]

function ToggleChip({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors whitespace-nowrap ${
        active
          ? 'bg-blue-500 text-white border-blue-500'
          : 'bg-transparent text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-blue-400'
      }`}
    >
      {children}
    </button>
  )
}

export function FilterBar({
  filters,
  allStations,
  onToggleArrayItem,
  onUpdateFilter,
  onReset,
  hasActiveFilters,
  onAddBuilding,
  onRemoveBuilding,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-6 py-3 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 text-sm">

      {/* 0. Selected districts (set via landing page map) */}
      {filters.districts.length > 0 && (
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Districts</span>
          {filters.districts.map(d => (
            <button
              key={d}
              onClick={() => onToggleArrayItem('districts', d)}
              className="flex items-center gap-0.5 px-2 py-0.5 text-xs font-semibold rounded-full transition-opacity hover:opacity-80"
              style={{ background: DISTRICT_COLORS[d] ?? '#94a3b8', color: '#0f172a' }}
            >
              D{d} ×
            </button>
          ))}
        </div>
      )}

      {/* 1. Building search (multi-select) */}
      <BuildingSearch
        selectedBuildings={filters.selectedBuildings}
        onAdd={onAddBuilding}
        onRemove={onRemoveBuilding}
      />

      {/* 2. Property type */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mr-1">Type</span>
        {PROPERTY_TYPE_OPTIONS.map(opt => (
          <ToggleChip
            key={opt.value}
            active={filters.propertyTypes.includes(opt.value)}
            onClick={() => onToggleArrayItem('propertyTypes', opt.value)}
          >
            {opt.label}
          </ToggleChip>
        ))}
      </div>

      {/* 3. Bedrooms */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mr-1">Beds</span>
        {BEDROOM_OPTIONS.map(opt => (
          <ToggleChip
            key={opt.value}
            active={filters.bedrooms.includes(opt.value)}
            onClick={() => onToggleArrayItem('bedrooms', opt.value)}
          >
            {opt.label}
          </ToggleChip>
        ))}
      </div>

      {/* 4. Area with m²/ft² toggle */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Area</span>
        <input
          type="number"
          placeholder="Min"
          value={filters.areaMin}
          onChange={e => onUpdateFilter('areaMin', e.target.value)}
          className="w-16 border border-gray-300 dark:border-gray-600 rounded px-1.5 py-1 text-xs bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
        />
        <span className="text-gray-400">–</span>
        <input
          type="number"
          placeholder="Max"
          value={filters.areaMax}
          onChange={e => onUpdateFilter('areaMax', e.target.value)}
          className="w-16 border border-gray-300 dark:border-gray-600 rounded px-1.5 py-1 text-xs bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200"
        />
        {/* m² / ft² toggle */}
        <button
          onClick={() => onUpdateFilter('areaUnit', filters.areaUnit === 'sqm' ? 'sqft' : 'sqm')}
          className="flex items-center gap-0.5 text-[10px] text-gray-400 dark:text-gray-500 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
        >
          <span className={`px-1 py-0.5 rounded font-medium ${filters.areaUnit === 'sqm' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400' : ''}`}>m²</span>
          <span className="text-gray-300 dark:text-gray-600">/</span>
          <span className={`px-1 py-0.5 rounded font-medium ${filters.areaUnit === 'sqft' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400' : ''}`}>ft²</span>
        </button>
      </div>

      {/* 5. MRT station proximity */}
      <MrtFilter
        allStations={allStations}
        selectedStations={filters.stations}
        onToggle={name => onToggleArrayItem('stations', name)}
        compact
      />

      {/* 6. Date range slider (compact) */}
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Date</span>
        <DateRangeSlider
          dateFrom={filters.dateFrom}
          dateTo={filters.dateTo}
          onChange={(from, to) => {
            onUpdateFilter('dateFrom', from)
            onUpdateFilter('dateTo', to)
          }}
          compact
        />
      </div>

      {/* Reset */}
      {hasActiveFilters && (
        <button
          onClick={onReset}
          className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 dark:hover:text-red-400 transition-colors"
        >
          <X className="w-3 h-3" />
          Clear
        </button>
      )}
    </div>
  )
}
