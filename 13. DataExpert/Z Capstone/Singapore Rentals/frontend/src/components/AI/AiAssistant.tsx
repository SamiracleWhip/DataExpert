import { useEffect, useRef, useState } from 'react'
import { Sparkles, Send, Trash2 } from 'lucide-react'
import type { Filters } from '../../types'
import { useChat } from '../../hooks/useChat'
import { ChatBubble } from './ChatBubble'
import { SuggestedChips } from './SuggestedChips'

export function AiAssistant({ filters }: { filters: Filters }) {
  const { messages, isStreaming, sendMessage, clearHistory } = useChat(filters)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const hasFilters =
    filters.districts.length > 0 ||
    filters.stations.length > 0 ||
    filters.bedrooms.length > 0 ||
    filters.selectedBuildings.length > 0

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleSend() {
    const text = input.trim()
    if (!text || isStreaming) return
    setInput('')
    sendMessage(text)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 flex-shrink-0">
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <Sparkles size={14} className="text-amber-400" />
          <span className="font-medium text-gray-700 dark:text-gray-200">Casota AI</span>
          <span className="text-gray-300 dark:text-gray-600">·</span>
          <span>Powered by Claude</span>
        </div>
        {messages.length > 0 && (
          <button
            type="button"
            onClick={() => clearHistory()}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          >
            <Trash2 size={13} />
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 bg-gray-50 dark:bg-gray-900">
        {messages.length === 0
          ? <SuggestedChips onSelect={sendMessage} />
          : messages.map((msg, i) => <ChatBubble key={i} message={msg} />)
        }
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3 flex-shrink-0">
        {hasFilters && (
          <div className="mb-2">
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800">
              Using active filters
            </span>
          </div>
        )}
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            placeholder="Ask about Singapore rentals…"
            className="flex-1 px-4 py-2.5 rounded-xl text-sm bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 border border-transparent focus:border-blue-300 dark:focus:border-blue-700 focus:outline-none disabled:opacity-50 transition-colors"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
