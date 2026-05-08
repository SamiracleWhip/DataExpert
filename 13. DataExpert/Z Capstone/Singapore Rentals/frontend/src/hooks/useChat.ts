import { useState, useRef, useEffect } from 'react'
import type { ChatMessage, Filters } from '../types'
import { chatStream } from '../lib/api'

const STORAGE_KEY = 'casota_chat_history'
const MAX_HISTORY = 20

function saveToStorage(msgs: ChatMessage[]) {
  try {
    const completed = msgs.filter(m => !m.isStreaming)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(completed.slice(-MAX_HISTORY)))
  } catch {}
}

export function useChat(filters: Filters) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored ? JSON.parse(stored) : []
    } catch {
      return []
    }
  })
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const clearedRef = useRef(false)
  const filtersRef = useRef(filters)

  useEffect(() => { filtersRef.current = filters }, [filters])

  useEffect(() => {
    return () => { abortRef.current?.abort() }
  }, [])

  async function sendMessage(text: string) {
    if (isStreaming) return
    clearedRef.current = false

    const history = messages
      .filter(m => !m.isStreaming)
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }))

    setMessages(prev => [
      ...prev,
      { role: 'user', content: text },
      { role: 'assistant', content: '', isStreaming: true, toolsUsed: [] },
    ])
    setIsStreaming(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      for await (const event of chatStream(text, history, filtersRef.current, controller.signal)) {
        if (event.type === 'text' && event.text) {
          setMessages(prev => {
            const msgs = [...prev]
            const last = msgs[msgs.length - 1]
            if (last?.role === 'assistant') {
              msgs[msgs.length - 1] = { ...last, content: last.content + event.text }
            }
            return msgs
          })
        } else if (event.type === 'tool_start' && event.tool) {
          setMessages(prev => {
            const msgs = [...prev]
            const last = msgs[msgs.length - 1]
            if (last?.role === 'assistant') {
              msgs[msgs.length - 1] = {
                ...last,
                toolsUsed: [...(last.toolsUsed ?? []), event.tool!],
              }
            }
            return msgs
          })
        } else if (event.type === 'error') {
          setMessages(prev => {
            const msgs = [...prev]
            const last = msgs[msgs.length - 1]
            if (last?.role === 'assistant') {
              msgs[msgs.length - 1] = {
                ...last,
                content: last.content || `Error: ${event.message ?? 'something went wrong'}`,
              }
            }
            return msgs
          })
          break
        } else if (event.type === 'done') {
          break
        }
      }
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setMessages(prev => {
          const msgs = [...prev]
          const last = msgs[msgs.length - 1]
          if (last?.role === 'assistant' && last.isStreaming) {
            msgs[msgs.length - 1] = {
              ...last,
              content: last.content || 'Sorry, something went wrong. Please try again.',
            }
          }
          return msgs
        })
      }
    } finally {
      if (!clearedRef.current) {
        setMessages(prev => {
          const msgs = [...prev]
          const last = msgs[msgs.length - 1]
          if (last?.role === 'assistant' && last.isStreaming) {
            msgs[msgs.length - 1] = { ...last, isStreaming: false }
          }
          saveToStorage(msgs)
          return msgs
        })
      }
      setIsStreaming(false)
    }
  }

  function clearHistory() {
    clearedRef.current = true
    abortRef.current?.abort()
    abortRef.current = null
    setIsStreaming(false)
    setMessages([])
    try { localStorage.removeItem(STORAGE_KEY) } catch {}
  }

  return { messages, isStreaming, sendMessage, clearHistory }
}
