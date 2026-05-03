export interface District {
  district: string
  area_name: string
}

export interface Building {
  id: number
  project: string
  street: string
  lat: number
  lng: number
  avg_rent: number
  contract_count: number
  nearest_mrt: string | null
  nearest_mrt_m: number | null
}

export interface Bookmark {
  id: number
  project: string
  street: string
  district: string
  avg_rent: number
  lat: number
  lng: number
  nearest_mrt: string | null
  nearest_mrt_m: number | null
  savedAt: number
}

export interface TrendPoint {
  year: number
  month: number
  avg_rent: number
  avg_psm: number | null
  contracts: number
  district?: string
}

export interface BuildingEnrichment {
  building_id: number
  nearest_mrt: string
  mrt_distance_m: number
  schools_1km: number
  school_names: string[]
  avg_psm: number | null
  year_built: number | null
}

export interface RecommendedBuilding {
  id: number
  project: string
  street: string
  avg_rent: number
}

export interface Stats {
  avg_rent: number | null
  median_rent: number | null
  min_rent: number | null
  max_rent: number | null
  total_contracts: number
  total_buildings: number
}

export interface DistrictStat {
  district: string
  area_name: string
  avg_rent: number
  contracts: number
}

export interface HistogramBucket {
  bucket_start: number
  count: number
}

export interface Deal {
  id: number
  project: string
  street: string
  district: string
  recent_avg: number
  trailing_avg: number
  pct_below: number
}

export interface Contract {
  id: number
  project: string
  street: string
  district: string
  bedrooms: string | null
  area_sqm_min: number | null
  area_sqm_max: number | null
  rent: number
  lease_year: number
  lease_month: number
  property_type: string | null
}

export interface ContractsResponse {
  total: number
  limit: number
  offset: number
  data: Contract[]
}

export interface BuildingSuggestion {
  id: number
  project: string
  street: string
}

export interface SelectedBuilding {
  id: number
  name: string
}

export const MAX_BUILDINGS = 10

export interface MrtStation {
  name: string
  building_count: number
}

export interface Filters {
  districts: string[]
  stations: string[]
  bedrooms: string[]
  propertyTypes: string[]
  areaMin: string
  areaMax: string
  areaUnit: 'sqm' | 'sqft'
  dateFrom: string           // "YYYY-MM"
  dateTo: string             // "YYYY-MM"
  selectedBuildings: SelectedBuilding[]
}
