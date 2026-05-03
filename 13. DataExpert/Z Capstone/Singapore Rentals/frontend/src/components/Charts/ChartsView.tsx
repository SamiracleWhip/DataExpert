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
import { useMemo } from 'react'
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

// Truncate long building names for chart labels
function shortName(name: string, max = 22) {
  return name.length > max ? name.slice(0, max) + '…' : name
}

interface Props {
  filters: Filters
}

export function ChartsView({ filters }: Props) {
  const filtersKey = JSON.stringify(filters)
  const multiBuilding = filters.selectedBuildings.length >= 2
  const multiDistrict = !multiBuilding && filters.districts.length > 1

  const { data: stats, loading: statsLoading } = useQuery<Stats>(
    () => api.stats(filters) as Promise<Stats>,
    [filtersKey],
  )

  const { data: trends, loading: trendsLoading } = useQuery<TrendPoint[] | BuildingTrendPoint[]>(
    () => api.trends(filters, undefined, multiDistrict, multiBuilding) as Promise<TrendPoint[]>,
    [filtersKey, multiDistrict, multiBuilding],
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
    }))
  })()

  // ── Y-axis domain for trend chart ────────────────────────────────────────
  const trendYDomain = useMemo(() => {
    if (!trendChartData.length) return ['auto', 'auto'] as const
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
  }, [trendChartData])

  // ── PSM chart data (comparison mode only) ────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const psfChartData: any[] = useMemo(() => {
    if (!trends || trends.length === 0 || !multiBuilding) return []
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
  }, [trends, multiBuilding])

  // ── Contract volume chart data ────────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const contractChartData: any[] = useMemo(() => {
    if (!trends || trends.length === 0) return []
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
        <SectionTitle>Avg Rent Over Time</SectionTitle>
        {trendsLoading ? (
          <div className="h-64 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
        ) : trendChartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-gray-400 text-sm">No data for current filters.</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trendChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={5} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `$${(Number(v) / 1000).toFixed(1)}k`} width={50} domain={trendYDomain} />
              <Tooltip formatter={rentFmt} contentStyle={{ fontSize: 12 }} />
              {multiBuilding ? (
                filters.selectedBuildings.map((b, i) => (
                  <Line
                    key={b.id}
                    type="monotone"
                    dataKey={String(b.id)}
                    stroke={CHART_COLORS[i % CHART_COLORS.length]}
                    dot={false}
                    strokeWidth={2}
                    name={shortName(b.name)}
                  />
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
                <Line type="monotone" dataKey="avg_rent" stroke="#3b82f6" dot={false} strokeWidth={2} name="Avg Rent" />
              )}
              {(multiBuilding || multiDistrict) && <Legend wrapperStyle={{ fontSize: 11 }} />}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Contract Volume */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
        <SectionTitle>Monthly Deal Count</SectionTitle>
        {contractChartData.length === 0 ? (
          <div className="h-48 flex items-center justify-center text-gray-400 text-sm">Loading…</div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={contractChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={5} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={v => Number(v).toLocaleString()} width={45} />
              <Tooltip formatter={countFmt} contentStyle={{ fontSize: 12 }} />
              {multiBuilding ? (
                <>
                  {filters.selectedBuildings.map((b, i) => (
                    <Line
                      key={b.id}
                      type="monotone"
                      dataKey={String(b.id)}
                      stroke={CHART_COLORS[i % CHART_COLORS.length]}
                      dot={false}
                      strokeWidth={2}
                      name={shortName(b.name)}
                    />
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

      {/* PSM Comparison — only in multi-building mode */}
      {multiBuilding && psfChartData.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
          <SectionTitle>Avg PSM (Price per sqm) Over Time</SectionTitle>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={psfChartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="label" tick={{ fontSize: 10 }} interval={5} />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `$${Number(v).toFixed(1)}`} width={50} />
              <Tooltip
                formatter={(v: unknown) => [`$${Number(v).toFixed(2)}/sqm`, 'Avg PSM']}
                contentStyle={{ fontSize: 12 }}
              />
              {filters.selectedBuildings.map((b, i) => (
                <Line
                  key={b.id}
                  type="monotone"
                  dataKey={`psf_${b.id}`}
                  stroke={CHART_COLORS[i % CHART_COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                  name={shortName(b.name)}
                  connectNulls
                />
              ))}
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* District Bar OR Building Comparison Bar */}
      <div className="bg-white dark:bg-gray-800 rounded-xl p-5 shadow-sm border border-gray-100 dark:border-gray-700">
        <SectionTitle>
          {multiBuilding ? 'Building Comparison — Avg Rent' : 'Avg Rent by District'}
        </SectionTitle>
        {multiBuilding ? (
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
                  <th className="pb-2 font-medium text-right">12-mo Avg</th>
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
                    <td className="py-2 text-right text-gray-500 dark:text-gray-400">{fmtRent(d.trailing_avg)}</td>
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
    </div>
  )
}
