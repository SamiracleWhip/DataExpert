import { useState, useMemo } from 'react'
import { MapContainer, TileLayer, CircleMarker, Tooltip, Polyline } from 'react-leaflet'
import { X } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartTooltip,
  ResponsiveContainer,
} from 'recharts'
import 'leaflet/dist/leaflet.css'
import type { Building, Filters, TrendPoint } from '../../types'
import { useQuery } from '../../hooks/useQuery'
import { api } from '../../lib/api'

const SG_CENTER: [number, number] = [1.3521, 103.8198]

interface MrtLine {
  type: string
  features: Array<{
    properties: { line: string; color: string }
    geometry: { coordinates: [number, number][] }
  }>
}

interface MrtStop {
  type: string
  features: Array<{
    properties: { name: string; color: string }
    geometry: { coordinates: [number, number] }
  }>
}

function rentColor(rent: number, min: number, max: number): string {
  const t = Math.max(0, Math.min(1, (rent - min) / (max - min || 1)))
  const hue = Math.round(120 * (1 - t))
  return `hsl(${hue}, 80%, 45%)`
}

function fmtRent(v: number) { return `$${v.toLocaleString()}` }
function fmtMonth(year: number, month: number) {
  return `${year}-${String(month).padStart(2, '0')}`
}

// ── Building drawer ───────────────────────────────────────────────────────────

function BuildingDrawer({ building, filters, onClose }: {
  building: Building; filters: Filters; onClose: () => void
}) {
  const { data, loading } = useQuery<TrendPoint[]>(
    () => api.trends(filters, building.id) as Promise<TrendPoint[]>,
    [building.id, JSON.stringify(filters)],
  )
  return (
    <div className="absolute top-0 right-0 h-full w-80 bg-white dark:bg-gray-900 shadow-xl z-[1000] flex flex-col border-l border-gray-200 dark:border-gray-700">
      <div className="flex items-start justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm leading-tight">{building.project}</h3>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{building.street}</p>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded">
          <X className="w-4 h-4 text-gray-500" />
        </button>
      </div>
      <div className="p-4 grid grid-cols-2 gap-3 border-b border-gray-200 dark:border-gray-700">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Avg Rent</p>
          <p className="text-lg font-bold text-blue-600 dark:text-blue-400">{fmtRent(building.avg_rent)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">Contracts</p>
          <p className="text-lg font-bold text-gray-900 dark:text-white">{building.contract_count.toLocaleString()}</p>
        </div>
      </div>
      <div className="flex-1 p-4">
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-3">Rent Trend</p>
        {loading ? (
          <div className="flex items-center justify-center h-40 text-gray-400 text-sm">Loading…</div>
        ) : data && data.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data.map(d => ({ ...d, label: fmtMonth(d.year, d.month) }))}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" tick={{ fontSize: 9 }} interval={5} />
              <YAxis tick={{ fontSize: 9 }} tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} width={40} />
              <RechartTooltip
                formatter={(v) => [fmtRent(Number(v ?? 0)), 'Avg Rent']}
                labelStyle={{ fontSize: 11 }} contentStyle={{ fontSize: 11 }}
              />
              <Line type="monotone" dataKey="avg_rent" stroke="#3b82f6" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <p className="text-sm text-gray-400 mt-4">No trend data for current filters.</p>
        )}
      </div>
    </div>
  )
}

// ── Main map view ─────────────────────────────────────────────────────────────

interface Props { filters: Filters }

export function MapView({ filters }: Props) {
  const [selectedBuilding, setSelectedBuilding] = useState<Building | null>(null)
  const [markerScale, setMarkerScale] = useState(1)
  const [showLines, setShowLines] = useState(true)

  const { data: buildings, loading, error } = useQuery<Building[]>(
    () => api.buildings(filters) as Promise<Building[]>,
    [JSON.stringify(filters)],
  )

  const { data: mrtLines } = useQuery<MrtLine>(
    () => fetch('/api/stations/lines').then(r => r.json()),
    [],
  )

  const { data: mrtStops } = useQuery<MrtStop>(
    () => fetch('/api/stations/stops').then(r => r.json()),
    [],
  )

  const { minRent, maxRent } = useMemo(() => {
    if (!buildings || buildings.length === 0) return { minRent: 0, maxRent: 1 }
    const rents = buildings.map(b => b.avg_rent)
    return { minRent: Math.min(...rents), maxRent: Math.max(...rents) }
  }, [buildings])

  return (
    <div className="relative flex-1 overflow-hidden">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/60 dark:bg-gray-900/60 z-[999]">
          <span className="text-sm text-gray-500">Loading buildings…</span>
        </div>
      )}
      {error && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-red-100 text-red-700 text-sm px-4 py-2 rounded z-[999]">
          {error}
        </div>
      )}

      <MapContainer center={SG_CENTER} zoom={12} className="h-full w-full" zoomControl>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        />

        {/* MRT lines */}
        {showLines && mrtLines?.features.map((f, i) => (
          <Polyline
            key={i}
            positions={f.geometry.coordinates.map(([lng, lat]) => [lat, lng] as [number, number])}
            pathOptions={{
              color: f.properties.color,
              weight: 4,
              opacity: 0.85,
            }}
          />
        ))}

        {/* MRT stops */}
        {showLines && mrtStops?.features.map((f, i) => (
          <CircleMarker
            key={`stop-${i}`}
            center={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
            radius={5}
            pathOptions={{
              fillColor: f.properties.color,
              fillOpacity: 1,
              color: '#ffffff',
              weight: 1.5,
            }}
          >
            <Tooltip direction="top" offset={[0, -5]}>
              <span className="text-xs font-medium">{f.properties.name}</span>
            </Tooltip>
          </CircleMarker>
        ))}

        {/* Building markers */}
        {buildings?.map(b => (
          <CircleMarker
            key={b.id}
            center={[b.lat, b.lng]}
            radius={Math.max(3, Math.min(14, 4 + b.contract_count / 20)) * markerScale}
            pathOptions={{
              fillColor: rentColor(b.avg_rent, minRent, maxRent),
              fillOpacity: 0.85,
              color: '#ffffff',
              weight: 1,
            }}
            eventHandlers={{ click: () => setSelectedBuilding(b) }}
          >
            <Tooltip direction="top" offset={[0, -6]}>
              <span className="text-xs">
                <strong>{b.project}</strong><br />
                Avg: {fmtRent(b.avg_rent)} · {b.contract_count} contracts
              </span>
            </Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>

      {/* Controls panel — bottom left */}
      <div className="absolute bottom-6 left-4 z-[999] flex flex-col gap-2">

        {/* Rent legend */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow px-3 py-2 text-xs">
          <p className="font-semibold text-gray-700 dark:text-gray-200 mb-1">Avg Rent</p>
          <div className="w-24 h-2 rounded" style={{ background: 'linear-gradient(to right, hsl(120,80%,45%), hsl(60,80%,45%), hsl(0,80%,45%))' }} />
          <div className="flex justify-between mt-0.5 text-gray-500 dark:text-gray-400">
            <span>{fmtRent(Math.round(minRent))}</span>
            <span>{fmtRent(Math.round(maxRent))}</span>
          </div>
        </div>

        {/* Marker size slider */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow px-3 py-2 text-xs">
          <div className="flex items-center justify-between mb-1">
            <p className="font-semibold text-gray-700 dark:text-gray-200">Marker size</p>
            <span className="text-gray-400 dark:text-gray-500">{markerScale.toFixed(1)}×</span>
          </div>
          <input
            type="range"
            min={0.3}
            max={3}
            step={0.1}
            value={markerScale}
            onChange={e => setMarkerScale(Number(e.target.value))}
            className="w-24 accent-blue-500"
          />
        </div>

        {/* MRT lines toggle */}
        <button
          onClick={() => setShowLines(s => !s)}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg shadow text-xs font-medium transition-colors ${
            showLines
              ? 'bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-200'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500'
          }`}
        >
          <span className={`w-3 h-1 rounded-full ${showLines ? 'bg-red-500' : 'bg-gray-300'}`} />
          MRT lines
        </button>
      </div>

      {selectedBuilding && (
        <BuildingDrawer
          building={selectedBuilding}
          filters={filters}
          onClose={() => setSelectedBuilding(null)}
        />
      )}
    </div>
  )
}
