import { useCallback, useRef, useState } from 'react'
import { createSession, downloadCalendar, downloadItinerary, streamFeedback, streamPlan } from '../api/client'
import type { SSEEvent, VenueCoordinate, WeatherDay } from '../api/types'

export type AppPhase = 'idle' | 'streaming' | 'interrupted' | 'resuming' | 'done' | 'error'

export interface PlanState {
  phase: AppPhase
  threadId: string | null
  destination: string
  activeNode: string | null
  completedNodes: string[]
  streamingText: string
  draftItinerary: string
  verificationScore: number
  venueCoordinates: VenueCoordinate[]
  weatherData: WeatherDay[]
  travelStartDate: string | null
  error: string | null
}

const INITIAL: PlanState = {
  phase: 'idle',
  threadId: null,
  destination: '',
  activeNode: null,
  completedNodes: [],
  streamingText: '',
  draftItinerary: '',
  verificationScore: 0,
  venueCoordinates: [],
  weatherData: [],
  travelStartDate: null,
  error: null,
}

export function usePlanSession() {
  const [state, setState] = useState<PlanState>(INITIAL)
  const abortRef = useRef<AbortController | null>(null)

  const handleEvent = useCallback((event: SSEEvent) => {
    switch (event.event) {
      case 'node_start':
        setState(prev => ({ ...prev, activeNode: event.node }))
        break

      case 'node_complete':
        setState(prev => ({
          ...prev,
          completedNodes: prev.completedNodes.includes(event.node)
            ? prev.completedNodes
            : [...prev.completedNodes, event.node],
          destination: event.destination ?? prev.destination,
          verificationScore: event.verification_score ?? prev.verificationScore,
        }))
        break

      case 'llm_token':
        setState(prev => ({ ...prev, streamingText: prev.streamingText + event.token }))
        break

      case 'interrupt':
        setState(prev => ({
          ...prev,
          phase: 'interrupted',
          activeNode: null,
          draftItinerary: event.draft_itinerary,
          verificationScore: event.verification_score,
          venueCoordinates: event.venue_coordinates ?? [],
          weatherData: event.weather_data ?? [],
          travelStartDate: event.travel_start_date ?? null,
          streamingText: '',
          completedNodes: prev.completedNodes.filter(n => n !== 'human_review'),
        }))
        break

      case 'done':
        setState(prev => ({ ...prev, phase: 'done', activeNode: null, streamingText: '' }))
        break

      case 'error':
        setState(prev => ({ ...prev, phase: 'error', error: event.detail, activeNode: null }))
        break
    }
  }, [])

  const submitTrip = useCallback(async (message: string, startDate?: string | null) => {
    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac

    setState({ ...INITIAL, phase: 'streaming' })

    try {
      const threadId = await createSession()
      setState(prev => ({ ...prev, threadId }))
      await streamPlan(threadId, message, handleEvent, ac.signal, startDate)
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setState(prev => ({
          ...prev,
          phase: 'error',
          error: (err as Error).message ?? 'Unknown error',
        }))
      }
    }
  }, [handleEvent])

  const submitFeedback = useCallback(async (feedback: string) => {
    const { threadId } = state
    if (!threadId) return

    abortRef.current?.abort()
    const ac = new AbortController()
    abortRef.current = ac

    setState(prev => ({
      ...prev,
      phase: 'resuming',
      activeNode: null,
      streamingText: '',
    }))

    try {
      await streamFeedback(threadId, feedback, handleEvent, ac.signal)
    } catch (err) {
      if ((err as Error).name !== 'AbortError') {
        setState(prev => ({
          ...prev,
          phase: 'error',
          error: (err as Error).message ?? 'Unknown error',
        }))
      }
    }
  }, [state, handleEvent])

  const triggerDownload = useCallback(async () => {
    if (!state.threadId) return
    try { await downloadItinerary(state.threadId) }
    catch (err) { setState(prev => ({ ...prev, error: (err as Error).message })) }
  }, [state.threadId])

  const triggerCalendarDownload = useCallback(async () => {
    if (!state.threadId) return
    try { await downloadCalendar(state.threadId) }
    catch (err) { setState(prev => ({ ...prev, error: (err as Error).message })) }
  }, [state.threadId])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState(INITIAL)
  }, [])

  return { state, submitTrip, submitFeedback, triggerDownload, triggerCalendarDownload, reset }
}
