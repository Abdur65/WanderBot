import { fetchEventSource } from '@microsoft/fetch-event-source'
import type { SSEEvent } from './types'

// In dev: VITE_API_URL is unset → BASE = '/api/v1' (Vite proxy handles /api → localhost:8000)
// In prod: VITE_API_URL = 'https://wanderbot-backend.onrender.com' → BASE = full URL + /api/v1
const BASE = `${import.meta.env.VITE_API_URL ?? ''}/api/v1`;

export async function createSession(): Promise<string> {
  const res = await fetch(`${BASE}/session`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to create session')
  const data = await res.json()
  return data.thread_id as string
}

export function streamPlan(
  threadId: string,
  message: string,
  onEvent: (e: SSEEvent) => void,
  signal: AbortSignal,
  startDate?: string | null,
): Promise<void> {
  return fetchEventSource(`${BASE}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, message, start_date: startDate ?? null }),
    signal,
    openWhenHidden: true,  // keep stream alive when tab is hidden/switched
    onmessage(msg) {
      if (!msg.data) return
      try { onEvent(JSON.parse(msg.data)) } catch { /* ignore */ }
    },
    onerror(err) {
      throw err // prevent auto-reconnect on network errors
    },
  })
}

export function streamFeedback(
  threadId: string,
  feedback: string,
  onEvent: (e: SSEEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  return fetchEventSource(`${BASE}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, feedback }),
    signal,
    openWhenHidden: true,  // keep stream alive when tab is hidden/switched
    onmessage(msg) {
      if (!msg.data) return
      try { onEvent(JSON.parse(msg.data)) } catch { /* ignore */ }
    },
    onerror(err) {
      throw err
    },
  })
}

export async function downloadCalendar(threadId: string): Promise<void> {
  const res = await fetch(`${BASE}/export/calendar/${threadId}`)
  if (!res.ok) throw new Error('Calendar export failed')
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') ?? ''
  const match = cd.match(/filename="(.+?)"/)
  const filename = match?.[1] ?? 'itinerary.ics'
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

export async function downloadItinerary(threadId: string): Promise<void> {
  const res = await fetch(`${BASE}/export/${threadId}`)
  if (!res.ok) throw new Error('Export failed')
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') ?? ''
  const match = cd.match(/filename="(.+?)"/)
  const filename = match?.[1] ?? 'itinerary.md'
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
