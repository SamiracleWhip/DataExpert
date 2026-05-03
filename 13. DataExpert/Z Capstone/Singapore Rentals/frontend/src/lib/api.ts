import type { Filters } from '../types'

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
  const url = params ? `${path}?${params}` : path
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

  trends: (filters: Filters, buildingId?: number, groupByDistrict?: boolean, groupByBuilding?: boolean) => {
    const p = filtersToParams(filters)
    if (buildingId != null) p.set('building_id', String(buildingId))
    if (groupByDistrict) p.set('group_by_district', 'true')
    if (groupByBuilding) p.set('group_by_building', 'true')
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
