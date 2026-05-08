import React from 'react'
import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'

export interface ChartSpec {
  type: 'bar' | 'line'
  title?: string
  data: { label: string; value: number }[]
  y_label?: string
}

const fmt = (v: unknown) => {
  const n = Number(v)
  return n >= 1000 ? `$${(n / 1000).toFixed(1)}k` : `$${n}`
}

export const ChatChart = React.memo(function ChatChart({ spec }: { spec: ChartSpec }) {
  const { type, title, data, y_label } = spec
  const chartData = data.map(d => ({ name: d.label, value: d.value }))

  return (
    <div className="my-3 w-full">
      {title && (
        <p className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">{title}</p>
      )}
      <ResponsiveContainer width="100%" height={180}>
        {type === 'line' ? (
          <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: '#9ca3af' }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tickFormatter={fmt}
              tick={{ fontSize: 10, fill: '#9ca3af' }}
              tickLine={false}
              axisLine={false}
              width={44}
            />
            <Tooltip
              formatter={(v: number) => [fmt(v), y_label ?? 'Value']}
              contentStyle={{ fontSize: 11, borderRadius: 6 }}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#3b82f6"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        ) : (
          <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 4, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" strokeOpacity={0.5} vertical={false} />
            <XAxis
              dataKey="name"
              tick={{ fontSize: 10, fill: '#9ca3af' }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tickFormatter={fmt}
              tick={{ fontSize: 10, fill: '#9ca3af' }}
              tickLine={false}
              axisLine={false}
              width={44}
            />
            <Tooltip
              formatter={(v: number) => [fmt(v), y_label ?? 'Value']}
              contentStyle={{ fontSize: 11, borderRadius: 6 }}
            />
            <Bar dataKey="value" fill="#3b82f6" radius={[3, 3, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
})
