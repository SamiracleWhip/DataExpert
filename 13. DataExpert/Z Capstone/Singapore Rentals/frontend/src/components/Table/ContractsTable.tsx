import { useState } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown } from 'lucide-react'
import type { Contract, ContractsResponse, Filters } from '../../types'
import { useQuery } from '../../hooks/useQuery'
import { api } from '../../lib/api'

const PAGE_SIZE = 50

const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

const COLUMNS: { key: string; label: string; sortable: boolean }[] = [
  { key: 'project', label: 'Building', sortable: false },
  { key: 'district', label: 'District', sortable: true },
  { key: 'no_of_bedrooms', label: 'Beds', sortable: true },
  { key: 'area_sqm_min', label: 'Area min (sqm)', sortable: true },
  { key: 'area_sqm_max', label: 'Area max (sqm)', sortable: true },
  { key: 'rent', label: 'Rent (SGD)', sortable: true },
  { key: 'lease_date', label: 'Lease Date', sortable: true },
  { key: 'property_type', label: 'Type', sortable: false },
]

interface Props {
  filters: Filters
}

export function ContractsTable({ filters }: Props) {
  const [page, setPage] = useState(0)
  const [sortBy, setSortBy] = useState('lease_year')
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>('desc')

  const handleSort = (col: string) => {
    const apiCol = col === 'lease_date' ? 'lease_year' : col
    if (sortBy === apiCol) {
      setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    } else {
      setSortBy(apiCol)
      setSortDir('desc')
    }
    setPage(0)
  }

  const { data, loading, error } = useQuery<ContractsResponse>(
    () => api.contracts(filters, sortBy, sortDir, PAGE_SIZE, page * PAGE_SIZE) as Promise<ContractsResponse>,
    [JSON.stringify(filters), sortBy, sortDir, page],
  )

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0

  function SortIcon({ col }: { col: string }) {
    const apiCol = col === 'lease_date' ? 'lease_year' : col
    if (sortBy !== apiCol) return <ChevronsUpDown className="w-3 h-3 text-gray-400" />
    return sortDir === 'desc'
      ? <ChevronDown className="w-3 h-3 text-blue-500" />
      : <ChevronUp className="w-3 h-3 text-blue-500" />
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-6">
      {error && (
        <div className="mb-4 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 px-4 py-2 rounded">
          {error}
        </div>
      )}

      <div className="flex items-center justify-between mb-3">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {data ? `${data.total.toLocaleString()} contracts` : '—'}
        </p>
        <div className="flex items-center gap-2">
          <button
            disabled={page === 0}
            onClick={() => setPage(p => p - 1)}
            className="px-3 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          >
            ← Prev
          </button>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {page + 1} / {totalPages || 1}
          </span>
          <button
            disabled={!data || page >= totalPages - 1}
            onClick={() => setPage(p => p + 1)}
            className="px-3 py-1 text-xs border border-gray-300 dark:border-gray-600 rounded disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300"
          >
            Next →
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-auto rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-gray-50 dark:bg-gray-700 z-10">
            <tr>
              {COLUMNS.map(col => (
                <th
                  key={col.key}
                  className={`px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide whitespace-nowrap ${col.sortable ? 'cursor-pointer hover:text-gray-800 dark:hover:text-gray-200 select-none' : ''}`}
                  onClick={() => col.sortable && handleSort(col.key)}
                >
                  <span className="flex items-center gap-1">
                    {col.label}
                    {col.sortable && <SortIcon col={col.key} />}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={COLUMNS.length} className="px-4 py-10 text-center text-gray-400 text-sm">
                  Loading…
                </td>
              </tr>
            ) : data?.data.length === 0 ? (
              <tr>
                <td colSpan={COLUMNS.length} className="px-4 py-10 text-center text-gray-400 text-sm">
                  No contracts match the current filters.
                </td>
              </tr>
            ) : (
              data?.data.map((row: Contract) => (
                <tr
                  key={row.id}
                  className="border-t border-gray-100 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/40"
                >
                  <td className="px-4 py-2.5">
                    <p className="font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{row.project}</p>
                    <p className="text-xs text-gray-400">{row.street}</p>
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">D{row.district}</td>
                  <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">
                    {row.bedrooms == null ? '—' : row.bedrooms === '00' ? 'Studio' : row.bedrooms}
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">{row.area_sqm_min ?? '—'}</td>
                  <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">{row.area_sqm_max ?? '—'}</td>
                  <td className="px-4 py-2.5 font-medium text-blue-600 dark:text-blue-400">
                    ${row.rent.toLocaleString()}
                  </td>
                  <td className="px-4 py-2.5 text-gray-600 dark:text-gray-300">
                    {MONTH_NAMES[row.lease_month - 1]} {row.lease_year}
                  </td>
                  <td className="px-4 py-2.5 text-gray-500 dark:text-gray-400 text-xs">{row.property_type ?? '—'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
