import type { Bookmark, Building } from '../types'

const KEY = 'shedza_bookmarks'

export function getBookmarks(): Bookmark[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? '[]')
  } catch {
    return []
  }
}

export function isBookmarked(id: number): boolean {
  return getBookmarks().some(b => b.id === id)
}

export function addBookmark(building: Building, district: string): void {
  const existing = getBookmarks().filter(b => b.id !== building.id)
  const bookmark: Bookmark = {
    id: building.id,
    project: building.project,
    street: building.street,
    district,
    avg_rent: building.avg_rent,
    lat: building.lat,
    lng: building.lng,
    nearest_mrt: building.nearest_mrt ?? null,
    nearest_mrt_m: building.nearest_mrt_m ?? null,
    savedAt: Date.now(),
  }
  localStorage.setItem(KEY, JSON.stringify([bookmark, ...existing]))
}

export function removeBookmark(id: number): void {
  const updated = getBookmarks().filter(b => b.id !== id)
  localStorage.setItem(KEY, JSON.stringify(updated))
}

export function mrtMinutes(distanceM: number | null): string {
  if (distanceM == null) return ''
  return `${Math.round(distanceM / 80)} min walk`
}
