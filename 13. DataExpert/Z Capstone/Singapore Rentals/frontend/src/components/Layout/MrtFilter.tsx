import { useState, useRef, useMemo } from 'react'
import { Train, X, Search } from 'lucide-react'
import type { MrtStation } from '../../types'

// Official Singapore MRT line colours.
// Interchange stations are assigned their primary / most recognisable line.
const LINE_COLOR: Record<string, string> = {
  // NS Line — Red
  'Jurong East':'#D42E12','Bukit Batok':'#D42E12','Bukit Gombak':'#D42E12',
  'Choa Chu Kang':'#D42E12','Yew Tee':'#D42E12','Kranji':'#D42E12',
  'Marsiling':'#D42E12','Woodlands':'#D42E12','Admiralty':'#D42E12',
  'Sembawang':'#D42E12','Canberra':'#D42E12','Yishun':'#D42E12',
  'Khatib':'#D42E12','Yio Chu Kang':'#D42E12','Ang Mo Kio':'#D42E12',
  'Bishan':'#D42E12','Braddell':'#D42E12','Toa Payoh':'#D42E12',
  'Novena':'#D42E12','Newton':'#D42E12','Orchard':'#D42E12',
  'Somerset':'#D42E12','Dhoby Ghaut':'#D42E12','City Hall':'#D42E12',
  'Raffles Place':'#D42E12','Marina Bay':'#D42E12','Marina South Pier':'#D42E12',

  // EW Line — Green
  'Pasir Ris':'#009645','Tampines':'#009645','Simei':'#009645',
  'Tanah Merah':'#009645','Bedok':'#009645','Kembangan':'#009645',
  'Eunos':'#009645','Paya Lebar':'#009645','Aljunied':'#009645',
  'Kallang':'#009645','Lavender':'#009645','Bugis':'#009645',
  'Tanjong Pagar':'#009645','Outram Park':'#009645','Tiong Bahru':'#009645',
  'Redhill':'#009645','Queenstown':'#009645','Commonwealth':'#009645',
  'Buona Vista':'#009645','Dover':'#009645','Clementi':'#009645',
  'Chinese Garden':'#009645','Lakeside':'#009645','Boon Lay':'#009645',
  'Pioneer':'#009645','Joo Koon':'#009645','Gul Circle':'#009645',
  'Tuas Crescent':'#009645','Tuas West Road':'#009645','Tuas Link':'#009645',
  'Expo':'#009645','Changi Airport':'#009645',

  // NE Line — Purple
  'HarbourFront':'#9900AA','Chinatown':'#9900AA','Clarke Quay':'#9900AA',
  'Little India':'#9900AA','Farrer Park':'#9900AA','Boon Keng':'#9900AA',
  'Potong Pasir':'#9900AA','Woodleigh':'#9900AA','Serangoon':'#9900AA',
  'Kovan':'#9900AA','Hougang':'#9900AA','Buangkok':'#9900AA',
  'Sengkang':'#9900AA','Punggol':'#9900AA',

  // CC Line — Orange
  'Bras Basah':'#FA9E0D','Esplanade':'#FA9E0D','Promenade':'#FA9E0D',
  'Nicoll Highway':'#FA9E0D','Stadium':'#FA9E0D','Mountbatten':'#FA9E0D',
  'Dakota':'#FA9E0D','MacPherson':'#FA9E0D','Tai Seng':'#FA9E0D',
  'Bartley':'#FA9E0D','Lorong Chuan':'#FA9E0D','Marymount':'#FA9E0D',
  'Caldecott':'#FA9E0D','Botanic Gardens':'#FA9E0D','Farrer Road':'#FA9E0D',
  'Holland Village':'#FA9E0D','one-north':'#FA9E0D','Kent Ridge':'#FA9E0D',
  'Haw Par Villa':'#FA9E0D','Pasir Panjang':'#FA9E0D','Labrador Park':'#FA9E0D',
  'Telok Blangah':'#FA9E0D','Bayfront':'#FA9E0D',

  // DT Line — Dark Blue
  'Bukit Panjang':'#005EC4','Cashew':'#005EC4','Hillview':'#005EC4',
  'Beauty World':'#005EC4','King Albert Park':'#005EC4','Sixth Avenue':'#005EC4',
  'Tan Kah Kee':'#005EC4','Stevens':'#005EC4','Rochor':'#005EC4',
  'Downtown':'#005EC4','Telok Ayer':'#005EC4','Fort Canning':'#005EC4',
  'Bencoolen':'#005EC4','Jalan Besar':'#005EC4','Bendemeer':'#005EC4',
  'Geylang Bahru':'#005EC4','Mattar':'#005EC4','Ubi':'#005EC4',
  'Kaki Bukit':'#005EC4','Bedok North':'#005EC4','Bedok Reservoir':'#005EC4',
  'Tampines West':'#005EC4','Tampines East':'#005EC4','Upper Changi':'#005EC4',

  // TE Line — Brown
  'Woodlands North':'#9D5B25','Woodlands South':'#9D5B25','Springleaf':'#9D5B25',
  'Lentor':'#9D5B25','Mayflower':'#9D5B25','Bright Hill':'#9D5B25',
  'Upper Thomson':'#9D5B25','Napier':'#9D5B25','Orchard Boulevard':'#9D5B25',
  'Great World':'#9D5B25','Havelock':'#9D5B25','Maxwell':'#9D5B25',
  'Shenton Way':'#9D5B25','Gardens by the Bay':'#9D5B25','Tanjong Rhu':'#9D5B25',
  'Katong Park':'#9D5B25','Tanjong Katong':'#9D5B25','Marine Parade':'#9D5B25',
  'Marine Terrace':'#9D5B25','Siglap':'#9D5B25','Bayshore':'#9D5B25',
  'Bedok South':'#9D5B25','Sungei Bedok':'#9D5B25',
}

const DEFAULT_COLOR = '#6b7280'

function stationColor(name: string): string {
  return LINE_COLOR[name] ?? DEFAULT_COLOR
}

// Use white text on all line colours (they're all dark enough)
function chipStyle(name: string) {
  const bg = stationColor(name)
  return { background: bg, borderColor: bg, color: '#ffffff' }
}

interface Props {
  allStations: MrtStation[]
  selectedStations: string[]
  onToggle: (name: string) => void
  compact?: boolean
}

export function MrtFilter({ allStations, selectedStations, onToggle, compact = false }: Props) {
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = useMemo(() => {
    if (!query.trim()) return allStations
    const q = query.toLowerCase()
    return allStations.filter(s => s.name.toLowerCase().includes(q))
  }, [query, allStations])

  const baseChip = compact
    ? 'flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold border'
    : 'flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold border'

  return (
    <div className={`flex flex-col gap-1.5 ${compact ? '' : 'w-full'}`}>

      {/* Selected station chips — coloured by line */}
      {selectedStations.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {selectedStations.map(name => (
            <span key={name} className={baseChip} style={chipStyle(name)}>
              <Train className={compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} />
              <span>{name}</span>
              <button onClick={() => onToggle(name)} className="hover:opacity-70">
                <X className={compact ? 'w-2.5 h-2.5' : 'w-3 h-3'} />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Search input */}
      <div className="relative">
        <div className={`flex items-center gap-1.5 ${compact ? '' : 'w-full'}`}>
          {compact && (
            <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide shrink-0">MRT</span>
          )}
          <div className={`relative ${compact ? '' : 'w-full'}`}>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={e => { setQuery(e.target.value); setOpen(true) }}
              onFocus={() => setOpen(true)}
              onBlur={() => setTimeout(() => setOpen(false), 150)}
              placeholder={compact ? 'Search station…' : 'Search MRT/LRT station…'}
              className={compact
                ? 'w-36 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-100 text-xs px-2.5 py-1 pr-6 outline-none focus:border-blue-400 transition-colors'
                : 'w-full border border-gray-200 dark:border-gray-600 rounded-xl bg-gray-50 dark:bg-gray-700 text-gray-800 dark:text-gray-100 text-sm px-4 py-2.5 pr-10 outline-none focus:border-blue-400 focus:bg-white dark:focus:bg-gray-600 transition-colors'
              }
            />
            <Search className={`absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none ${compact ? 'w-3 h-3' : 'w-4 h-4'}`} />

            {/* Dropdown */}
            {open && filtered.length > 0 && (
              <ul className={`absolute z-[2000] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl shadow-xl overflow-y-auto ${
                compact
                  ? 'left-0 top-full mt-1 w-56 max-h-48'
                  : 'left-0 right-0 top-full mt-1 max-h-56'
              }`}>
                {filtered.map(s => {
                  const selected = selectedStations.includes(s.name)
                  const color = stationColor(s.name)
                  return (
                    <li
                      key={s.name}
                      onMouseDown={() => { onToggle(s.name); setQuery(''); inputRef.current?.focus() }}
                      className={`flex items-center justify-between px-4 py-2 cursor-pointer text-sm ${
                        selected
                          ? 'bg-gray-50 dark:bg-gray-700'
                          : 'text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700'
                      }`}
                    >
                      <span className="flex items-center gap-2">
                        {/* Colour dot matching the line */}
                        <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                        <span className={selected ? 'font-semibold' : ''}>{s.name}</span>
                      </span>
                      <span className="text-xs text-gray-400 dark:text-gray-500">{s.building_count}</span>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </div>
      </div>

      {!compact && selectedStations.length === 0 && (
        <p className="text-xs text-gray-400 dark:text-gray-500">
          Shows buildings within ≤15 min walk of selected station
        </p>
      )}
    </div>
  )
}
