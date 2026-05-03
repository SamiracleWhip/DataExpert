import { useState, useEffect } from 'react'
import { Bookmark, Trash2, Train, MapPin } from 'lucide-react'
import type { Bookmark as BookmarkType } from '../../types'
import { getBookmarks, removeBookmark, mrtMinutes } from '../../lib/bookmarks'

function fmtRent(v: number) { return `$${v.toLocaleString()}` }

function timeAgo(ts: number): string {
  const mins = Math.floor((Date.now() - ts) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

export function SavedView() {
  const [bookmarks, setBookmarks] = useState<BookmarkType[]>([])

  useEffect(() => { setBookmarks(getBookmarks()) }, [])

  const handleRemove = (id: number) => {
    removeBookmark(id)
    setBookmarks(getBookmarks())
  }

  if (bookmarks.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4 text-gray-400 dark:text-gray-500">
        <Bookmark className="w-12 h-12 opacity-30" />
        <p className="text-lg font-medium">No saved properties yet</p>
        <p className="text-sm">Hover over a building on the Map tab and click the bookmark icon to save it.</p>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            Saved Properties
            <span className="ml-2 text-sm font-normal text-gray-400">({bookmarks.length})</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {bookmarks.map(b => (
            <div
              key={b.id}
              className="bg-white dark:bg-gray-800 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm p-5 flex flex-col gap-3"
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900 dark:text-white leading-tight truncate">
                    {b.project}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">{b.street}</p>
                </div>
                <button
                  onClick={() => handleRemove(b.id)}
                  className="flex-shrink-0 p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-500 transition-colors"
                  title="Remove bookmark"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>

              {/* Stats */}
              <div className="flex items-center gap-4 text-sm">
                <div>
                  <p className="text-xs text-gray-400 dark:text-gray-500">Avg Rent</p>
                  <p className="font-bold text-blue-600 dark:text-blue-400">{fmtRent(b.avg_rent)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-400 dark:text-gray-500">District</p>
                  <p className="font-semibold text-gray-700 dark:text-gray-300">D{b.district}</p>
                </div>
              </div>

              {/* MRT */}
              {b.nearest_mrt && (
                <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
                  <Train className="w-3 h-3 flex-shrink-0" />
                  <span>{b.nearest_mrt}</span>
                  {b.nearest_mrt_m != null && (
                    <span className="text-gray-400">· {mrtMinutes(b.nearest_mrt_m)}</span>
                  )}
                </div>
              )}

              {/* Location */}
              <div className="flex items-center gap-1.5 text-xs text-gray-400 dark:text-gray-500">
                <MapPin className="w-3 h-3 flex-shrink-0" />
                <span>{b.lat.toFixed(4)}°N, {b.lng.toFixed(4)}°E</span>
                <span className="ml-auto">{timeAgo(b.savedAt)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
