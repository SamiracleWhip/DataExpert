import { useState, useEffect } from 'react'
import { DATE_MIN, DATE_MAX } from '../../hooks/useFilters'

// Data spans Jan 2022 (index 0) → Mar 2026 (index 50)
const MONTH_COUNT = 51
const MONTH_MAX = MONTH_COUNT - 1   // 50

// 17 quarters: Q1 2022 (0) → Q1 2026 (16)
const QUARTER_MAX = 16

const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

function yyyymmToMonthIdx(s: string): number {
  const year = parseInt(s.slice(0, 4))
  const month = parseInt(s.slice(5, 7))
  return (year - 2022) * 12 + (month - 1)
}

function monthIdxToYYYYMM(i: number): string {
  const year = 2022 + Math.floor(i / 12)
  const month = (i % 12) + 1
  return `${year}-${String(month).padStart(2, '0')}`
}

function monthIdxToLabel(i: number): string {
  const year = 2022 + Math.floor(i / 12)
  const month = (i % 12) + 1
  return `${MONTH_NAMES[month - 1]} ${year}`
}

function quarterIdxToLabel(q: number): string {
  const year = 2022 + Math.floor(q / 4)
  const quarter = (q % 4) + 1
  return `Q${quarter} ${year}`
}

// Quarter start month (1-indexed)
function quarterIdxToStartMonth(q: number): number { return (q % 4) * 3 + 1 }
function quarterIdxToEndMonth(q: number): number   { return (q % 4) * 3 + 3 }
function quarterIdxToYear(q: number): number       { return 2022 + Math.floor(q / 4) }

function monthIdxToQuarterIdx(i: number): number { return Math.floor(i / 3) }

interface Props {
  dateFrom: string
  dateTo: string
  onChange: (from: string, to: string) => void
  compact?: boolean
}

export function DateRangeSlider({ dateFrom, dateTo, onChange, compact = false }: Props) {
  const [mode, setMode] = useState<'month' | 'quarter'>('month')

  // Underlying state is always in month indices for precision
  const [low, setLow] = useState(() => yyyymmToMonthIdx(dateFrom))
  const [high, setHigh] = useState(() => yyyymmToMonthIdx(dateTo))

  // Sync when props change externally (e.g. reset)
  useEffect(() => { setLow(yyyymmToMonthIdx(dateFrom)) }, [dateFrom])
  useEffect(() => { setHigh(yyyymmToMonthIdx(dateTo)) }, [dateTo])

  // In quarter mode, display indices are quarter-based
  const qLow  = monthIdxToQuarterIdx(low)
  const qHigh = monthIdxToQuarterIdx(high)
  const displayLow  = mode === 'month' ? low  : qLow
  const displayHigh = mode === 'month' ? high : qHigh
  const maxIdx      = mode === 'month' ? MONTH_MAX : QUARTER_MAX

  const fromLabel = mode === 'month' ? monthIdxToLabel(low)  : quarterIdxToLabel(qLow)
  const toLabel   = mode === 'month' ? monthIdxToLabel(high) : quarterIdxToLabel(qHigh)

  const leftPct  = (displayLow  / maxIdx) * 100
  const rightPct = (displayHigh / maxIdx) * 100

  const commit = (newLow: number, newHigh: number) => {
    // Convert display indices back to YYYY-MM
    const from = mode === 'month'
      ? monthIdxToYYYYMM(newLow)
      : `${quarterIdxToYear(newLow)}-${String(quarterIdxToStartMonth(newLow)).padStart(2, '0')}`
    const to = mode === 'month'
      ? monthIdxToYYYYMM(newHigh)
      : `${quarterIdxToYear(newHigh)}-${String(quarterIdxToEndMonth(newHigh)).padStart(2, '0')}`
    onChange(from, to)
  }

  const handleLow = (v: number) => {
    const clamped = Math.min(v, displayHigh)
    const monthIdx = mode === 'month' ? clamped : clamped * 3
    setLow(monthIdx)
    commit(clamped, displayHigh)
  }

  const handleHigh = (v: number) => {
    const clamped = Math.max(v, displayLow)
    const monthIdx = mode === 'month' ? clamped : clamped * 3 + 2
    setHigh(monthIdx)
    commit(displayLow, clamped)
  }

  const toggleMode = () => {
    setMode(m => m === 'month' ? 'quarter' : 'month')
  }

  const isFullRange = dateFrom === DATE_MIN && dateTo === DATE_MAX

  const trackH  = compact ? 'h-1' : 'h-1.5'
  const wrapH   = compact ? 'h-4' : 'h-5'
  const labelSz = compact ? 'text-[10px]' : 'text-xs'

  return (
    <div className={compact ? 'w-48' : 'w-full'}>
      {/* From / To labels */}
      <div className={`flex justify-between mb-1.5 ${labelSz}`}>
        <span className={`font-medium ${isFullRange ? 'text-gray-400 dark:text-gray-500' : 'text-blue-500 dark:text-blue-400'}`}>
          {fromLabel}
        </span>
        <span className={`font-medium ${isFullRange ? 'text-gray-400 dark:text-gray-500' : 'text-blue-500 dark:text-blue-400'}`}>
          {toLabel}
        </span>
      </div>

      {/* Slider track */}
      <div className={`range-slider relative ${wrapH} w-full select-none`}>
        {/* Track background */}
        <div className={`absolute top-1/2 -translate-y-1/2 left-0 right-0 ${trackH} rounded-full bg-gray-200 dark:bg-gray-600`} />
        {/* Fill between handles */}
        <div
          className={`absolute top-1/2 -translate-y-1/2 ${trackH} rounded-full bg-blue-500 dark:bg-blue-400`}
          style={{ left: `${leftPct}%`, right: `${100 - rightPct}%` }}
        />
        {/* Low handle — z-index flipped when low is at max so it stays draggable */}
        <input
          type="range"
          min={0}
          max={maxIdx}
          value={displayLow}
          onChange={e => handleLow(Number(e.target.value))}
          style={{ zIndex: displayLow >= maxIdx ? 5 : 3 }}
        />
        {/* High handle */}
        <input
          type="range"
          min={0}
          max={maxIdx}
          value={displayHigh}
          onChange={e => handleHigh(Number(e.target.value))}
          style={{ zIndex: displayLow >= maxIdx ? 3 : 5 }}
        />
      </div>

      {/* Mode toggle */}
      <div className={`flex justify-end mt-1.5 ${labelSz}`}>
        <button
          onClick={toggleMode}
          className="flex items-center gap-1 text-gray-400 dark:text-gray-500 hover:text-blue-500 dark:hover:text-blue-400 transition-colors"
        >
          <span className={`inline-flex rounded-full px-1.5 py-0.5 font-medium transition-colors ${mode === 'month' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400' : 'text-gray-400 dark:text-gray-500'}`}>M</span>
          <span className="text-gray-300 dark:text-gray-600">/</span>
          <span className={`inline-flex rounded-full px-1.5 py-0.5 font-medium transition-colors ${mode === 'quarter' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400' : 'text-gray-400 dark:text-gray-500'}`}>Q</span>
        </button>
      </div>
    </div>
  )
}
