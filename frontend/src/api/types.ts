export type NodeName =
  | 'analyze'
  | 'curate'
  | 'rag_retriever'
  | 'live_verifier'
  | 'draft_plan'
  | 'validate_citations'
  | 'human_review'

export interface NodeStartEvent {
  event: 'node_start'
  node: NodeName
}

export interface NodeCompleteEvent {
  event: 'node_complete'
  node: NodeName
  destination?: string
  verification_score?: number
  draft_snippet?: string
}

export interface LLMTokenEvent {
  event: 'llm_token'
  token: string
}

export interface InterruptEvent {
  event: 'interrupt'
  draft_itinerary: string
  verification_score: number
  message: string
}

export interface DoneEvent {
  event: 'done'
  thread_id: string
}

export interface ErrorEvent {
  event: 'error'
  detail: string
}

export type SSEEvent =
  | NodeStartEvent
  | NodeCompleteEvent
  | LLMTokenEvent
  | InterruptEvent
  | DoneEvent
  | ErrorEvent

export interface StateResponse {
  thread_id: string
  destination: string
  verification_score: number
  draft_itinerary: string
  is_interrupted: boolean
  interrupt_message?: string
}
