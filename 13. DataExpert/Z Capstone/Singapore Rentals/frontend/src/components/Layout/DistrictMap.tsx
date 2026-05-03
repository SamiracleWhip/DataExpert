import { useMemo, useRef } from 'react'
import { MapContainer, GeoJSON } from 'react-leaflet'
import type { GeoJsonObject, Feature } from 'geojson'
import type * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useQuery } from '../../hooks/useQuery'

// Nautical / territorial boundary — sea background
const NAUTICAL_STYLE = {
  fillColor: '#0d1e30',
  fillOpacity: 1,
  color: '#1e4060',
  weight: 1,
}

// Actual landmass — drawn on top of sea layer
const LANDMASS_STYLE = {
  fillColor: '#1a2e3a',
  fillOpacity: 1,
  color: '#3a8a9a',
  weight: 1.5,
}

interface DistrictFeatureProps {
  district: string
  area_name: string
}

interface Props {
  selectedDistricts: string[]
  onToggle: (district: string) => void
}

const SG_BOUNDS: [[number, number], [number, number]] = [
  [1.22, 103.60],
  [1.50, 104.05],
]

// One distinct colour per district — vivid palette, readable on dark tiles
const DISTRICT_COLORS: Record<string, string> = {
  '01': '#f87171', // red
  '02': '#fb923c', // orange
  '03': '#fbbf24', // amber
  '04': '#facc15', // yellow
  '05': '#a3e635', // lime
  '06': '#4ade80', // green
  '07': '#34d399', // emerald
  '08': '#2dd4bf', // teal
  '09': '#22d3ee', // cyan
  '10': '#38bdf8', // sky
  '11': '#60a5fa', // blue
  '12': '#818cf8', // indigo
  '13': '#a78bfa', // violet
  '14': '#c084fc', // purple
  '15': '#e879f9', // fuchsia
  '16': '#f472b6', // pink
  '17': '#fb7185', // rose
  '18': '#ff8c42', // deep orange
  '19': '#ffe066', // gold
  '20': '#b8e04a', // yellow-green
  '21': '#52e5a0', // mint
  '22': '#4fd1c5', // teal-green
  '23': '#63b3ed', // cornflower
  '24': '#9f7aea', // lavender
  '25': '#ed64a6', // hot pink
  '26': '#fc8181', // salmon
  '27': '#68d391', // sage
  '28': '#76e4f7', // light cyan
}

export function DistrictMap({ selectedDistricts, onToggle }: Props) {
  const { data: nautical } = useQuery<GeoJsonObject>(
    () => fetch('/api/districts/outline').then(r => r.json()),
    [],
  )
  const { data: landmass } = useQuery<GeoJsonObject>(
    () => fetch('/api/districts/landmass').then(r => r.json()),
    [],
  )
  const { data: geojson, loading } = useQuery<GeoJsonObject>(
    () => fetch('/api/districts/boundaries').then(r => r.json()),
    [],
  )

  const selectionKey = selectedDistricts.slice().sort().join(',')
  const selectedRef = useRef<string[]>(selectedDistricts)
  selectedRef.current = selectedDistricts

  function styleFeature(feature?: Feature) {
    if (!feature) return {}
    const district = (feature.properties as DistrictFeatureProps).district
    const isSelected = selectedRef.current.includes(district)
    const color = DISTRICT_COLORS[district] ?? '#94a3b8'
    return {
      fillColor: isSelected ? color : '#94a3b8',
      fillOpacity: isSelected ? 0.65 : 0.22,
      color: isSelected ? color : '#64748b',
      weight: isSelected ? 1.5 : 0.8,
    }
  }

  const onEachFeature = useMemo(() => {
    return (feature: Feature, layer: L.Layer) => {
      const props = feature.properties as DistrictFeatureProps
      const { district } = props
      const areaName = props.area_name.split(',')[0]

      ;(layer as L.Path).bindTooltip(areaName, {
        permanent: false,
        direction: 'center',
        className: 'district-tooltip',
      })

      layer.on({
        click: () => onToggle(district),
        mouseover: (e: L.LeafletMouseEvent) => {
          const path = e.target as L.Path
          const isSelected = selectedRef.current.includes(district)
          const color = DISTRICT_COLORS[district] ?? '#94a3b8'
          path.setStyle({
            fillColor: isSelected ? color : '#cbd5e1',
            fillOpacity: isSelected ? 0.85 : 0.35,
            weight: 2,
          })
        },
        mouseout: (e: L.LeafletMouseEvent) => {
          const path = e.target as L.Path
          path.setStyle(styleFeature(feature))
        },
      })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [onToggle])

  return (
    <div className="district-map-wrap w-full h-full flex flex-col bg-gray-900 border-l border-gray-700">

      {/* Map pane — flex-1 + min-h-0 lets Leaflet fill all available height */}
      <div className="relative flex-1 min-h-0">
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center z-[999] bg-gray-900/70 text-sm text-gray-400">
            Loading map…
          </div>
        )}

        {selectedDistricts.length > 0 && (
          <div className="absolute top-3 left-3 z-[999] flex flex-wrap gap-1 max-w-[65%]">
            {selectedDistricts.map(d => (
              <span
                key={d}
                className="px-2 py-0.5 text-xs font-semibold rounded-full shadow"
                style={{ background: DISTRICT_COLORS[d] ?? '#94a3b8', color: '#0f172a' }}
              >
                D{d}
              </span>
            ))}
          </div>
        )}

        <MapContainer
          bounds={SG_BOUNDS}
          zoomControl={false}
          dragging={false}
          scrollWheelZoom={false}
          doubleClickZoom={false}
          touchZoom={false}
          keyboard={false}
          attributionControl={false}
          className="w-full h-full"
        >
          {/* Layer 1 — nautical / territorial boundary (sea background) */}
          {nautical && (
            <GeoJSON
              key="sg-nautical"
              data={nautical}
              style={() => NAUTICAL_STYLE}
              interactive={false}
            />
          )}
          {/* Layer 2 — actual land mass (coastline) */}
          {landmass && (
            <GeoJSON
              key="sg-landmass"
              data={landmass}
              style={() => LANDMASS_STYLE}
              interactive={false}
            />
          )}
          {/* District polygons */}
          {geojson && (
            <GeoJSON
              key={selectionKey}
              data={geojson}
              style={styleFeature}
              onEachFeature={onEachFeature}
            />
          )}
        </MapContainer>
      </div>

      {/* Footer — fixed height, never squashed */}
      <p className="flex-shrink-0 text-center text-[10px] text-gray-500 py-2">
        {selectedDistricts.length === 0
          ? 'Click any district to filter · multi-select supported'
          : `${selectedDistricts.length} district${selectedDistricts.length > 1 ? 's' : ''} selected · click again to deselect`}
      </p>
    </div>
  )
}
