import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { useMemo, useState } from 'react'
import type { Filters, Stats, TrendPoint, DistrictStat, HistogramBucket, Deal, BuildingEnrichment } from '../../types'
import { useQuery } from '../../hooks/useQuery'
import { api } from '../../lib/api'

interface BuildingTrendPoint {
  building_id: number
  project: string
  year: number
  month: number
  avg_rent: number
  avg_psm: number | null
  contracts: number
}

interface BedroomTrendPoint {
  year: number
  month: number
  bedrooms: string
  avg_rent: number
  median_rent: number | null
  contracts: number
}

function bedroomLabel(br: string) {
  if (br === 'unknown') return 'Unknown'
  return `${br} BR`
}

function fmtRent(v: number) {
  return `$${v.toLocaleString()}`
}

function StatCard({ label, value }: { label: string; value: string | null }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-100 dark:border-gray-700">
      <p className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wide font-medium">{label}</p>
      <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">{value ?? '—'}</p>
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wide mb-3">
      {children}
    </h2>
  )
}

const CHART_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#06b6d4', '#f97316', '#84cc16', '#ec4899', '#14b8a6',
]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const rentFmt = (v: any) => [fmtRent(Number(v ?? 0)), 'Avg Rent'] as [string, string]
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const countFmt = (v: any) => [Number(v ?? 0).toLocaleString(), 'Contracts'] as [string, string]
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const pctFmt = (v: any) => { const n = Number(v ?? 0); return [`${n >= 0 ? '+' : ''}${n.toFixed(1)}%`, 'Change'] as [string, string] }
const pctAxis = (v: unknown) => { const n = Number(v); return `${n >= 0 ? '+' : ''}${n.toFixed(1)}%` }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function applyPctChange(data: any[], mode: 'mom' | 'qoq'): any[] {
  if (data.length === 0) return data
  const labelToIdx = new Map<string, number>(data.map((d, i) => [d.label as string, i]))
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return data.map((row, i) => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const result: any = { label: row.label }
    for (const [key, current] of Object.entries(row)) {
      if (key === 'label') continue
      if (typeof current !== 'number') { result[key] = null; continue }
      let prevRow = null
      if (mode === 'mom') {
        prevRow = i > 0 ? data[i - 1] : null
      } else {
        const [yr, mo] = (row.label as string).split('-').map(Number)
        let pm = mo - 3, py = yr
        if (pm <= 0) { pm += 12; py -= 1 }
        const prevLabel = `${py}-${String(pm).padStart(2, '0')}`
        const idx = labelToIdx.get(prevLabel)
        prevRow = idx != null ? data[idx] : null
      }
      const prev = prevRow?.[key]
      result[key] = (prev == null || prev === 0)
        ? null
        : parseFloat(((current - prev) / Math.abs(prev) * 100).toFixed(1))
    }
    return result
  })
}

// Truncate long building names for chart labels
function shortName(name: string, max = 22) {
  return name.length > max ? name.slice(0, max) + '…' : name
}

interface Props {
  filters: Filters
}

export function ChartsView({ filters }: Props) {
  const [rentMetric, setRentMetric] = useState<'avg' | 'median'>('avg')
  const [splitType, setSplitType] = useState<'buildings' | 'bedrooms'>('buildings')
  const [viewMode, setViewMode] = useState<'price' | 'mom' | 'qoq'>('price')
  const filtersKey = JSON.stringify(filters)
  const multiBuilding = filters.selectedBuildings.length >= 2
  const hasAnyBuilding = filters.selectedBuildings.length >= 1
  const multiDistrict = !multiBuilding && filters.districts.length > 1

  const { data: stats, loading: statsLoading } = useQuery<Stats>(
    () => api.stats(filters) as Promise<Stats>,
    [filtersKey],
  )

  const { data: trends, loading: trendsLoading } = useQuery<TrendPoint[] | BuildingTrendPoint[] | BedroomTrendPoint[]>(
    () => api.trends(
      filters, undefined, multiDistrict,
      multiBuilding && splitType === 'buildings',
      hasAnyBuilding && splitType === 'bedrooms',
    ) as Promise<TrendPoint[]>,
    [filtersKey, multiDistrict, multiBuilding, hasAnyBuilding, splitType],
  )

  const { data: districtStats } = useQuery<DistrictStat[]>(
    () => api.districtBreakdown(filters) as Promise<DistrictStat[]>,
    [filtersKey],
  )

  const { data: histogram } = useQuery<HistogramBucket[]>(
    () => api.histogram(filters) as Promise<HistogramBucket[]>,
    [filtersKey],
  )

  const { data: deals } = useQuery<Deal[]>(
    () => api.deals(filters) as Promise<Deal[]>,
    [filtersKey],
  )

  // Fetch enrichment data for each selected building (parallel, in comparison mode)
  const enrichmentKey = filters.selectedBuildings.map(b => b.id).join(',')
  const { data: enrichments } = useQuery<BuildingEnrichment[]>(
    () => multiBuilding
      ? Promise.all(
          filters.selectedBuildings.map(b =>
            api.buildingEnrich(b.id) as Promise<BuildingEnrichment>
          )
        )
      : Promise.resolve([]),
    [enrichmentKey, multiBuilding],
  )

  // ── Pivot trend data ──────────────────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const trendChartData: any[] = (() => {
    if (!trends || trends.length === 0) return []

    if (hasAnyBuilding && splitType === 'bedrooms') {
      const byLabel: Record<string, Record<string, string | number>> = {}
      ;(trends as BedroomTrendPoint[]).forEach(d => {
        const label = `${d.year}-${String(d.month).padStart(2, '0')}`
        if (!byLabel[label]) byLabel[label] = { label }
        byLabel[label][`br_${d.bedrooms}`] = rentMetric === 'median'
          ? (d.median_rent ?? d.avg_rent)
          : d.avg_rent
      })
      return Object.values(byLabel).sort((a, b) =>
        (a.label as string) < (b.label as string) ? -1 : 1
      )
    }

    if (multiBuilding) {
      // One column per building_id
      const byLabel: Record<string, Record<string, string | number>> = {}
      ;(trends as BuildingTrendPoint[]).forEach(d => {
        const label = `${d.year}-${String(d.month).padStart(2, '0')}`
        if (!byLabel[label]) byLabel[label] = { label }
        byLabel[label][String(d.building_id)] = d.avg_rent
      })
      return Object.values(byLabel).sort((a, b) =>
        (a.label as string) < (b.label as string) ? -1 : 1
      )
    }

    if (multiDistrict) {
      const byLabel: Record<string, Record<string, string | number>> = {}
      ;(trends as TrendPoint[]).forEach(d => {
        const label = `${d.year}-${String(d.month).padStart(2, '0')}`
        if (!byLabel[label]) byLabel[label] = { label }
        byLabel[label][`D${d.district}`] = d.avg_rent
      })
      return Object.values(byLabel).sort((a, b) =>
        (a.label as string) < (b.label as string) ? -1 : 1
      )
    }

    return (trends as TrendPoint[]).map(d => ({
      label: `${d.year}-${String(d.month).padStart(2, '0')}`,
      avg_rent: d.avg_rent,
      median_rent: d.median_rent ?? d.avg_rent,
    }))
  })()

  // ── Y-axis domain for trend chart ────────────────────────────────────────
  const trendYDomain = useMemo(() => {
    if (viewMode !== 'price' || !trendChartData.length) return ['auto', 'auto'] as const
    let min = Infinity, max = -Infinity
    trendChartData.forEach(d => {
      Object.entries(d).forEach(([k, v]) => {
        if (k !== 'label' && typeof v === 'number') {
          if (v < min) min = v
          if (v > max) max = v
        }
      })
    })
    if (min === Infinity) return ['auto', 'auto'] as const
    const cushion = Math.max((max - min) * 0.08, 300)
    return [
      Math.max(0, Math.floor((min - cushion) / 500) * 500),
      Math.ceil((max + cushion) / 500) * 500,
    ] as [number, number]
  }, [trendChartData, viewMode])

  // ── Bedroom keys (bedroom split mode) ────────────────────────────────────
  const bedroomKeys = useMemo(() => {
    if (!hasAnyBuilding || splitType !== 'bedrooms' || !trends || trends.length === 0) return []
    const keys = new Set<string>()
    ;(trends as BedroomTrendPoint[]).forEach(d => keys.add(d.bedrooms))
    return Array.from(keys).sort((a, b) => {
      if (a === 'unknown') return 1
      if (b === 'unknown') return -1
      return Number(a) - Number(b)
    })
  }, [trends, hasAnyBuilding, splitType])

  const bedroomBarData = useMemo(() => {
    if (!hasAnyBuilding || splitType !== 'bedrooms' || !trends || trends.length === 0) return null
    const totals: Record<string, { sum: number; count: number }> = {}
    ;(trends as BedroomTrendPoint[]).forEach(d => {
      if (!totals[d.bedrooms]) totals[d.bedrooms] = { sum: 0, count: 0 }
      totals[d.bedrooms].sum += d.avg_rent
      totals[d.bedrooms].count += 1
    })
    return Object.entries(totals)
      .map(([br, { sum, count }]) => ({ name: bedroomLabel(br), avg_rent: Math.round(sum / count), br }))
      .sort((a, b) => {
        if (a.br === 'unknown') return 1
        if (b.br === 'unknown') return -1
        return Number(a.br) - Number(b.br)
      })
  }, [trends, hasAnyBuilding, splitType])

  // ── PSM chart data (all modes except bedroom split) ──────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const psfChartData: any[] = useMemo(() => {
    if (!trends || trends.length === 0) return []
    if (hasAnyBuilding && splitType === 'bedrooms') return []

    if (multiBuilding && splitType === 'buildings') {
      const byLabel: Record<string, Record<string, string | number>> = {}
      ;(trends as BuildingTrendPoint[]).forEach(d => {
        if (d.avg_psm == null) return
        const label = `${d.year}-${String(d.month).padStart(2, '0')}`
        if (!byLabel[label]) byLabel[label] = { label }
        byLabel[label][`psf_${d.building_id}`] = d.avg_psm
      })
      return Object.values(byLabel).sort((a, b) =>
        (a.label as string) < (b.label as string) ? -1 : 1
      )
    }

    if (multiDistrict) {
      const byLabel: Record<string, Record<string, string | number>> = {}
      ;(trends as TrendPoint[]).forEach(d => {
        if (d.avg_psm == null) return
        const label = `${d.year}-${String(d.month).padStart(2, '0')}`
        if (!byLabel[label]) byLabel[label] = { label }
        byLabel[label][`D${d.district}`] = d.avg_psm
      })
      return Object.values(byLabel).sort((a, b) =>
        (a.label as string) < (b.label as string) ? -1 : 1
      )
    }

    // Standard / single-building
    return (trends as TrendPoint[])
      .filter(d => d.avg_psm != null)
      .map(d => ({
        label: `${d.year}-${String(d.month).padStart(2, '0')}`,
        avg_psm: d.avg_psm,
      }))
  }, [trends, multiBuilding, multiDistrict, hasAnyBuilding, splitType])

  // ── Contract volume chart data ────────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const contractChartData: any[] = useMemo(() => {
    if (!trends || trends.length === 0) return []
    if (hasAnyBuilding && splitType === 'bedrooms') {
      const byLabel: Record<string, Record<string, string | number>> = {}
      ;(trends as BedroomTrendPoint[]).forEach(d => {
        const label = `${d.year}-${String(d.month).padStart(2, '0')}`
        if (!byLabel[label]) byLabel[label] = { label }
        byLabel[label][`br_${d.bedrooms}`] = d.contracts
      })
      return Object.values(byLabel).sort((a, b) =>
        (a.label as string) < (b.label as string) ? -1 : 1
      )
    }
    if (multiBuilding) {
      const byLabel: Record<string, Record<string, string | number>> = {}
      ;(trends as BuildingTrendPoint[]).forEach(d => {
        const label = `${d.year}-${String(d.month).padStart(2, '0')}`
        if (!byLabel[label]) byLabel[label] = { label }
        byLabel[label][String(d.building_id)] = d.contracts
      })
      return Object.values(byLabel).sort((a, b) =>
        (a.label as string) < (b.label as string) ? -1 : 1
      )
    }
    return (trends as TrendPoint[]).map(d => ({
      label: `${d.year}-${String(d.month).padStart(2, '0')}`,
      contracts: d.contracts,
    }))
  }, [trends, multiBuilding])

  // ── % change transformed display data (must come after all source memos) ──
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const displayTrendData: any[] = useMemo(() =>
    viewMode === 'price' ? trendChartData : applyPctChange(trendChartData, viewMode),
  [trendChartData, viewMode])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const displayContractData: any[] = useMemo(() =>
    viewMode === 'price' ? contractChartData : applyPctChange(contractChartData, viewMode),
  [contractChartData, viewMode])
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const displayPsmData: any[] = useMemo(() =>
    viewMode === 'price' ? psfChartData : applyPctChange(psfChartData, viewMode),
  [psfChartData, viewMode])

  // ── Building comparison bar data ──────────────────────────────────────────
  // Avg rent per building (aggregate over date range)
  const buildingBarData = (() => {
    if (!multiBuilding || !trends || trends.length === 0) return null
    const totals: Record<number, { sum: number; count: number; project: string }> = {}
    ;(trends as BuildingTrendPoint[]).forEach(d => {
      if (!totals[d.building_id]) totals[d.building_id] = { sum: 0, count: 0, project: d.project }
      totals[d.building_id].sum += d.avg_rent
      totals[d.building_id].count += 1
    })
    return filters.selectedBuildings.map(b => ({
      id: b.id,
      name: shortName(b.name),
      fullName: b.name,
      avg_rent: totals[b.id]
        ? Math.round(totals[b.id].sum / totals[b.id].count)
        : 0,
    }))
  })()

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-8">

      {/* Stats cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Avg Rent" value={stats ? fmtRent(stats.avg_rent ?? 0) : statsLoading ? '…' : null} />
        <StatCard label="Median Rent" value={stats ? fmtRent(stats.median_rent ?? 0) : statsLoading ? '…' : null} />
        <StatCard label="Min Rent" value={stats ? fmtRent(stats.min_rent ?? 0) : statsLoading ? '…' : null} />
        <StatCard label="Max Rent" value={stats ? fmtRent(stats.max_rent ?? 0) : statsLoading ? '…' : null} />
      </div>

      {/* Building comparison snapshot — shown in multi-building mode */}
      {multiBuilding && enrichments && enrichments.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 dark:border-gray-700">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Building</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Avg Rent</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Avg PSM</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Nearest MRT</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">MRT Distance</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Schools (1km)</th>
              </tr>
            </thead>
            <tbody>
              {filters.selectedBuildings.map((b, i) => {
                const e = enrichments.find(x => x.building_id === b.id)
                const color = CHART_COLORS[i % CHART_COLORS.length]
                return (
                  <tr key={b.id} className="border-b border-gray-50 dark:border-gray-700/50">
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: color }} />
                        <span className="font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{b.name}</span>
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-blue-600 dark:text-blue-400">
                      {buildingBarData?.find(x => x.id === b.id)
                        ? `$${(buildingBarData.find(x => x.id === b.id)!.avg_rent).toLocaleString()}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                      {e?.avg_psm ? `$${e.avg_psm}/sqm` : '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                      {e?.nearest_mrt ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                      {e?.mrt_distance_m != null
                        ? e.mrt_distance_m < 1000
                          ? `${e.mrt_distance_m}m`
                          : `${(e.mrt_distance_m / 1000).toFixed(1)}km`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                      {e?.schools_1km != null ? e.schools_1km : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Trend Chart */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <SectionTitle>
            {viewMode === 'price'
              ? `${rentMetric === 'avg' ? 'Avg' : 'Median'} Rent Over Time`
              : `Rent ${viewMode === 'mom' ? 'MoM' : 'QoQ'} % Change`}
          </SectionTitle>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-gray-400 dark:text-gray-500">Mode</span>
              <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-full p-0.5">
                {(['price', 'mom', 'qoq'] as const).map(v => (
                  <button key={v} type="button" onClick={() => setViewMode(v)}
                    className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                      viewMode === v
                        ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                        : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                    }`}>
                    {v === 'price' ? 'Price' : v === 'mom' ? 'MoM %' : 'QoQ %'}
                  </button>
                ))}
              </div>
            </div>
            {hasAnyBuilding && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-400 dark:text-gray-500">Split by</span>
                <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-full p-0.5">
                  {(['buildings', 'bedrooms'] as const).map(s => (
                    <button key={s} type="button" onClick={() => setSplitType(s)}
                      className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                        splitType === s
                          ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                      }`}>
                      {s === 'buildings' ? 'Buildings' : 'Bedrooms'}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {!multiDistrict && (
              <div className="flex items-center gap-1.5">
                <span className="text-xs text-gray-400 dark:text-gray-500">View</span>
                <div className="flex items-center gap-1 bg-gray-100 dark:bg-gray-700 rounded-full p-0.5">
                  {(['avg', 'median'] as const).map(m => (
                    <button key={m} type="button" onClick={() => setRentMetric(m)}
                      className={`text-xs px-3 py-1 rounded-full font-medium transition-colors ${
                        rentMetric === m
                          ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow-sm'
                          : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
                      }`}>
                      {m === 'avg' ? 'Avg' : 'Median'}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
        {trendsLoading ? (
          <div className="h-64 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
        ) : trendChartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-gray-400 text-sm">No data for current filters.</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={displayTrendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={5} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={viewMode === 'price' ? (v => `$${(Number(v) / 1000).toFixed(1)}k`) : pctAxis} width={55} domain={trendYDomain} />
              <Tooltip formatter={viewMode === 'price' ? rentFmt : pctFmt} contentStyle={{ fontSize: 12 }} />
              {hasAnyBuilding && splitType === 'bedrooms' ? (
                bedroomKeys.map((br, i) => (
                  <Line key={br} type="monotone" dataKey={`br_${br}`} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} strokeWidth={2} name={bedroomLabel(br)} />
                ))
              ) : multiBuilding ? (
                filters.selectedBuildings.map((b, i) => (
                  <Line key={b.id} type="monotone" dataKey={String(b.id)} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} strokeWidth={2} name={shortName(b.name)} />
                ))
              ) : multiDistrict ? (
                filters.districts.map((d, i) => (
                  <Line
                    key={d}
                    type="monotone"
                    dataKey={`D${d}`}
                    stroke={CHART_COLORS[i % CHART_COLORS.length]}
                    dot={false}
                    strokeWidth={2}
                    name={`D${d}`}
                  />
                ))
              ) : (
                <Line
                  type="monotone"
                  dataKey={rentMetric === 'avg' ? 'avg_rent' : 'median_rent'}
                  stroke="#3b82f6"
                  dot={false}
                  strokeWidth={2}
                  name={rentMetric === 'avg' ? 'Avg Rent' : 'Median Rent'}
                />
              )}
              {(multiBuilding || multiDistrict || (hasAnyBuilding && splitType === 'bedrooms')) && <Legend wrapperStyle={{ fontSize: 11 }} />}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Contract Volume */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
        <SectionTitle>{viewMode === 'price' ? 'Monthly Deal Count' : `Deal Count ${viewMode === 'mom' ? 'MoM' : 'QoQ'} % Change`}</SectionTitle>
        {contractChartData.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={displayContractData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={5} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={viewMode === 'price' ? (v => Number(v).toLocaleString()) : pctAxis} width={50} />
              <Tooltip formatter={viewMode === 'price' ? countFmt : pctFmt} contentStyle={{ fontSize: 12 }} />
              {hasAnyBuilding && splitType === 'bedrooms' ? (
                <>
                  {bedroomKeys.map((br, i) => (
                    <Line key={br} type="monotone" dataKey={`br_${br}`} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} strokeWidth={2} name={bedroomLabel(br)} />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </>
              ) : multiBuilding ? (
                <>
                  {filters.selectedBuildings.map((b, i) => (
                    <Line key={b.id} type="monotone" dataKey={String(b.id)} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} strokeWidth={2} name={shortName(b.name)} />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </>
              ) : (
                <Line type="monotone" dataKey="contracts" stroke="#6366f1" dot={false} strokeWidth={2} name="Contracts" />
              )}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* PSM Over Time — always shown except in bedroom split mode */}
      {psfChartData.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
          <SectionTitle>{viewMode === 'price' ? 'Avg PSM (Price per sqm) Over Time' : `PSM ${viewMode === 'mom' ? 'MoM' : 'QoQ'} % Change`}</SectionTitle>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={displayPsmData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={5} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={viewMode === 'price' ? (v => `$${Number(v).toFixed(1)}`) : pctAxis} width={55} />
              <Tooltip
                formatter={viewMode === 'price'
                  ? ((v: unknown) => [`$${Number(v).toFixed(2)}/sqm`, 'Avg PSM'])
                  : pctFmt}
                contentStyle={{ fontSize: 12 }}
              />
              {multiBuilding && splitType === 'buildings' ? (
                <>
                  {filters.selectedBuildings.map((b, i) => (
                    <Line key={b.id} type="monotone" dataKey={`psf_${b.id}`} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} strokeWidth={2} name={shortName(b.name)} connectNulls />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </>
              ) : multiDistrict ? (
                <>
                  {filters.districts.map((d, i) => (
                    <Line key={d} type="monotone" dataKey={`D${d}`} stroke={CHART_COLORS[i % CHART_COLORS.length]} dot={false} strokeWidth={2} name={`D${d}`} connectNulls />
                  ))}
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </>
              ) : (
                <Line type="monotone" dataKey="avg_psm" stroke="#10b981" dot={false} strokeWidth={2} name="Avg PSM" connectNulls />
              )}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* District Bar OR Building Comparison Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
        <SectionTitle>
          {hasAnyBuilding && splitType === 'bedrooms' ? 'Bedroom Comparison — Avg Rent'
            : multiBuilding ? 'Building Comparison — Avg Rent'
            : 'Avg Rent by District'}
        </SectionTitle>
        {hasAnyBuilding && splitType === 'bedrooms' ? (
          bedroomBarData && bedroomBarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={bedroomBarData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `$${(Number(v) / 1000).toFixed(0)}k`} width={45} />
                <Tooltip formatter={rentFmt} contentStyle={{ fontSize: 12 }} />
                <Bar dataKey="avg_rent" radius={[3, 3, 0, 0]}>
                  {bedroomBarData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-56 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
          )
        ) : multiBuilding ? (
          buildingBarData && buildingBarData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={buildingBarData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `$${(Number(v) / 1000).toFixed(0)}k`} width={45} />
                <Tooltip
                  formatter={rentFmt}
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  labelFormatter={(_: unknown, payload: any) => payload?.[0]?.payload?.fullName ?? ''}
                  contentStyle={{ fontSize: 12 }}
                />
                <Bar dataKey="avg_rent" radius={[3, 3, 0, 0]}>
                  {buildingBarData.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-56 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
          )
        ) : !districtStats ? (
          <div className="h-56 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={districtStats.slice(0, 28)}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="district" tickFormatter={d => `D${d}`} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `$${(Number(v) / 1000).toFixed(0)}k`} width={45} />
              <Tooltip
                formatter={rentFmt}
                labelFormatter={d => `District ${d}`}
                contentStyle={{ fontSize: 12 }}
              />
              <Bar dataKey="avg_rent" radius={[3, 3, 0, 0]}>
                {districtStats.slice(0, 28).map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Deal Finder */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
        <div className="flex items-baseline gap-3 mb-3">
          <SectionTitle>Potential Deals</SectionTitle>
          <span className="text-xs text-gray-400 dark:text-gray-500">
            buildings where latest month avg is ≥10% below 12-month average
          </span>
        </div>
        {!deals ? (
          <div className="text-sm text-gray-400">Loading…</div>
        ) : deals.length === 0 ? (
          <div className="text-sm text-gray-400">No deals found for current filters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                  <th className="pb-2 font-medium">Building</th>
                  <th className="pb-2 font-medium">District</th>
                  <th className="pb-2 font-medium text-right">Latest Avg</th>
                  <th className="pb-2 font-medium text-right">Latest Count</th>
                  <th className="pb-2 font-medium text-right">12-mo Avg</th>
                  <th className="pb-2 font-medium text-right">12-mo Count</th>
                  <th className="pb-2 font-medium text-right">% Below</th>
                </tr>
              </thead>
              <tbody>
                {deals.map(d => (
                  <tr key={d.id} className="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
                    <td className="py-2 pr-4">
                      <p className="font-medium text-gray-900 dark:text-white truncate max-w-[200px]">{d.project}</p>
                      <p className="text-xs text-gray-400">{d.street}</p>
                    </td>
                    <td className="py-2 text-gray-600 dark:text-gray-300">D{d.district}</td>
                    <td className="py-2 text-right text-blue-600 dark:text-blue-400 font-medium">{fmtRent(d.recent_avg)}</td>
                    <td className="py-2 text-right text-gray-500 dark:text-gray-400">{d.recent_count}</td>
                    <td className="py-2 text-right text-gray-500 dark:text-gray-400">{fmtRent(d.trailing_avg)}</td>
                    <td className="py-2 text-right text-gray-500 dark:text-gray-400">{d.trailing_count}</td>
                    <td className="py-2 text-right">
                      <span className="px-2 py-0.5 bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-400 rounded-full text-xs font-medium">
                        -{d.pct_below}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Rent Distribution */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
        <SectionTitle>Rent Distribution</SectionTitle>
        {!histogram ? (
          <div className="h-56 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={histogram}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="bucket_start" tickFormatter={v => `$${(Number(v) / 1000).toFixed(0)}k`} tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={v => Number(v).toLocaleString()} width={50} />
              <Tooltip
                formatter={countFmt}
                labelFormatter={v => `$${Number(v).toLocaleString()} – $${(Number(v) + 499).toLocaleString()}`}
                contentStyle={{ fontSize: 12 }}
              />
              <Bar dataKey="count" fill="#6366f1" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
