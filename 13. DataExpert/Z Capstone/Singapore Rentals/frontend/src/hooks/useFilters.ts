import { useState, useCallback } from 'react'
import type { Filters, SelectedBuilding } from '../types'

export const DATE_MIN = '2022-01'
export const DATE_MAX = '2026-03'

const DEFAULT_FILTERS: Filters = {
  districts: [],
  stations: [],
  bedrooms: [],
  propertyTypes: ['Non-landed Properties'],
  areaMin: '',
  areaMax: '',
  areaUnit: 'sqm',
  dateFrom: DATE_MIN,
  dateTo: DATE_MAX,
  selectedBuildings: [],
}

export function useFilters() {
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS)

  const updateFilter = useCallback(<K extends keyof Filters>(key: K, value: Filters[K]) => {
    setFilters(prev => {
      // When the area unit changes, clear the area values so stale numbers aren't sent
      if (key === 'areaUnit') {
        return { ...prev, [key]: value, areaMin: '', areaMax: '' }
      }
      return { ...prev, [key]: value }
    })
  }, [])

  const toggleArrayItem = useCallback((key: 'districts' | 'bedrooms' | 'propertyTypes' | 'stations', item: string) => {
    setFilters(prev => {
      const arr = prev[key]
      return {
        ...prev,
        [key]: arr.includes(item) ? arr.filter(x => x !== item) : [...arr, item],
      }
    })
  }, [])

  const addBuilding = useCallback((id: number, name: string) => {
    setFilters(prev => {
      if (prev.selectedBuildings.length >= 10) return prev
      if (prev.selectedBuildings.some(b => b.id === id)) return prev
      return { ...prev, selectedBuildings: [...prev.selectedBuildings, { id, name }] }
    })
  }, [])

  const removeBuilding = useCallback((id: number) => {
    setFilters(prev => ({
      ...prev,
      selectedBuildings: prev.selectedBuildings.filter(b => b.id !== id),
    }))
  }, [])

  const resetFilters = useCallback(() => setFilters(DEFAULT_FILTERS), [])

  const hasActiveFilters = Object.entries(filters).some(([k, v]) => {
    if (k === 'areaUnit') return false  // unit toggle is a mode, not a filter
    if (k === 'dateFrom') return v !== DATE_MIN
    if (k === 'dateTo') return v !== DATE_MAX
    if (k === 'selectedBuildings') return (v as SelectedBuilding[]).length > 0
    return Array.isArray(v) ? v.length > 0 : v !== ''
  })

  return { filters, updateFilter, toggleArrayItem, addBuilding, removeBuilding, resetFilters, hasActiveFilters }
}
