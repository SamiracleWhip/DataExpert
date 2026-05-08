import type { Filters } from '../types'

const BASE = import.meta.env.VITE_API_URL ?? ''

export interface SseEvent {
  type: string
  text?: string
  tool?: string
  message?: string
}

export async function* chatStream(
  message: string,
  history: { role: string; content: string }[],
  filters: Filters,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent> {
  const f: Record<string, unknown> = {}
  if (filters.districts.length) f.district = filters.districts
  if (filters.stations.length) f.station = filters.stations
  if (filters.bedrooms.length) f.bedrooms = filters.bedrooms
  if (filters.propertyTypes.length) f.property_type = filters.propertyTypes
  if (filters.areaMin) f.area_min = filters.areaMin
  if (filters.areaMax) f.area_max = filters.areaMax
  f.area_unit = filters.areaUnit
  if (filters.dateFrom) f.date_from = filters.dateFrom
  if (filters.dateTo) f.date_to = filters.dateTo
  if (filters.selectedBuildings.length) {
    f.building_id = filters.selectedBuildings.map(b => b.id)
  }

  const res = await fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history, filters: f }),
    signal,
  })
  if (!res.ok) throw new Error(`Chat API error ${res.status}`)
  if (!res.body) return

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const lines = buf.split('\n')
    buf = lines.pop() ?? ''
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (raw) {
          try { yield JSON.parse(raw) } catch { /* skip malformed */ }
        }
      }
    }
  }
}

function filtersToParams(filters: Filters): URLSearchParams {
  const p = new URLSearchParams()
  filters.districts.forEach(d => p.append('district', d))
  filters.stations.forEach(s => p.append('station', s))
  filters.bedrooms.forEach(b => p.append('bedrooms', b))
  filters.propertyTypes.forEach(t => p.append('property_type', t))
  if (filters.areaMin) p.set('area_min', filters.areaMin)
  if (filters.areaMax) p.set('area_max', filters.areaMax)
  p.set('area_unit', filters.areaUnit)
  if (filters.dateFrom) p.set('date_from', filters.dateFrom)
  if (filters.dateTo) p.set('date_to', filters.dateTo)
  filters.selectedBuildings.forEach(b => p.append('building_id', String(b.id)))
  return p
}

async function get<T>(path: string, params?: URLSearchParams): Promise<T> {
  const url = params ? `${BASE}${path}?${params}` : `${BASE}${path}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`API error ${res.status}: ${url}`)
  return res.json()
}

export const api = {
  districts: () => get('/api/districts'),
  stations: () => get('/api/stations'),

  buildingSearch: (q: string, limit = 10) => {
    const p = new URLSearchParams({ q, limit: String(limit) })
    return get('/api/buildings/search', p)
  },

  buildingEnrich: (buildingId: number) =>
    get(`/api/buildings/enrich?building_id=${buildingId}`),

  buildingRecommend: (buildingId: number, excludeIds: number[], limit = 5) => {
    const p = new URLSearchParams({ building_id: String(buildingId), limit: String(limit) })
    excludeIds.forEach(id => p.append('exclude', String(id)))
    return get('/api/buildings/recommend', p)
  },

  buildings: (filters: Filters) =>
    get('/api/buildings', filtersToParams(filters)),

  trends: (filters: Filters, buildingId?: number, groupByDistrict?: boolean, groupByBuilding?: boolean, groupByBedrooms?: boolean) => {
    const p = filtersToParams(filters)
    if (buildingId != null) p.set('building_id', String(buildingId))
    if (groupByDistrict) p.set('group_by_district', 'true')
    if (groupByBuilding) p.set('group_by_building', 'true')
    if (groupByBedrooms) p.set('group_by_bedrooms', 'true')
    return get('/api/trends', p)
  },

  stats: (filters: Filters) =>
    get('/api/stats', filtersToParams(filters)),

  districtBreakdown: (filters: Filters) =>
    get('/api/stats/district-breakdown', filtersToParams(filters)),

  histogram: (filters: Filters, bucketSize = 500) => {
    const p = filtersToParams(filters)
    p.set('bucket_size', String(bucketSize))
    return get('/api/stats/histogram', p)
  },

  deals: (filters: Filters, thresholdPct = 10) => {
    const p = filtersToParams(filters)
    p.set('threshold_pct', String(thresholdPct))
    return get('/api/stats/deals', p)
  },

  contracts: (
    filters: Filters,
    sortBy = 'lease_year',
    sortDir = 'desc',
    limit = 50,
    offset = 0,
  ) => {
    const p = filtersToParams(filters)
    p.set('sort_by', sortBy)
    p.set('sort_dir', sortDir)
    p.set('limit', String(limit))
    p.set('offset', String(offset))
    return get('/api/contracts', p)
  },
}
