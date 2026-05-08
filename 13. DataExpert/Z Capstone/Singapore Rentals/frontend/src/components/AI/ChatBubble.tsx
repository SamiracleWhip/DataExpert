import React, { useRef, useMemo } from 'react'
import { User, Bot } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage } from '../../types'
import { ChatChart } from './ChatChart'
import type { ChartSpec } from './ChatChart'

export const ChatBubble = React.memo(function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'
  const chartSpecCache = useRef<Map<string, ChartSpec>>(new Map())

  const mdComponents = useMemo(() => ({
    p: ({ children }: { children?: React.ReactNode }) => <p className="mb-2 last:mb-0">{children}</p>,
    strong: ({ children }: { children?: React.ReactNode }) => <strong className="font-semibold">{children}</strong>,
    ul: ({ children }: { children?: React.ReactNode }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
    ol: ({ children }: { children?: React.ReactNode }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
    li: ({ children }: { children?: React.ReactNode }) => <li>{children}</li>,
    table: ({ children }: { children?: React.ReactNode }) => (
      <div className="overflow-x-auto my-2">
        <table className="min-w-full text-xs border-collapse">{children}</table>
      </div>
    ),
    thead: ({ children }: { children?: React.ReactNode }) => <thead className="bg-gray-100 dark:bg-gray-700">{children}</thead>,
    tbody: ({ children }: { children?: React.ReactNode }) => <tbody>{children}</tbody>,
    tr: ({ children }: { children?: React.ReactNode }) => <tr className="border-b border-gray-200 dark:border-gray-600">{children}</tr>,
    th: ({ children }: { children?: React.ReactNode }) => <th className="px-3 py-1.5 text-left font-semibold text-gray-700 dark:text-gray-200 whitespace-nowrap">{children}</th>,
    td: ({ children }: { children?: React.ReactNode }) => <td className="px-3 py-1.5 text-gray-700 dark:text-gray-300">{children}</td>,
    pre: ({ children }: { children?: React.ReactNode }) => {
      const arr = React.Children.toArray(children)
      if (arr.length === 1) {
        const child = arr[0] as React.ReactElement<{ className?: string; children?: unknown }>
        if (child?.props?.className === 'language-chart') {
          try {
            const raw = String(
              Array.isArray(child.props.children)
                ? child.props.children.join('')
                : child.props.children ?? ''
            )
            if (!chartSpecCache.current.has(raw)) {
              chartSpecCache.current.set(raw, JSON.parse(raw) as ChartSpec)
            }
            return <ChatChart spec={chartSpecCache.current.get(raw)!} />
          } catch {}
        }
      }
      return <pre className="overflow-x-auto p-3 my-2 rounded-lg bg-gray-100 dark:bg-gray-900 text-xs font-mono">{children}</pre>
    },
    code: ({ children }: { children?: React.ReactNode }) => <code className="px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-700 font-mono text-xs">{children}</code>,
    h3: ({ children }: { children?: React.ReactNode }) => <h3 className="font-semibold text-base mb-1 mt-2">{children}</h3>,
  }), []) // stable — chartSpecCache is a ref, never changes identity

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
        isUser
          ? 'bg-blue-600 text-white'
          : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
      }`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      <div className={`flex flex-col gap-1 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-sm whitespace-pre-wrap'
            : 'bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-100 rounded-tl-sm border border-gray-100 dark:border-gray-700'
        }`}>
          {isUser ? (
            message.content || (message.isStreaming ? '' : '…')
          ) : (
            <>
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={mdComponents}
              >
                {message.content || (message.isStreaming ? '' : '…')}
              </ReactMarkdown>
              {message.isStreaming && (
                <span className="inline-block w-0.5 h-4 bg-current ml-0.5 animate-pulse align-middle" />
              )}
            </>
          )}
        </div>

        {(message.toolsUsed?.length ?? 0) > 0 && (
          <div className="flex flex-wrap gap-1 mt-0.5">
            {message.toolsUsed!.map(tool => (
              <span
                key={tool}
                className="text-xs px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400"
              >
                ↳ {tool.replace(/_/g, ' ')}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
})
