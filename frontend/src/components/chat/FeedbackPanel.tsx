import { useState } from 'react'

interface FeedbackPanelProps {
  onApprove: () => void
  onFeedback: (text: string) => void
  isResuming?: boolean
}

export default function FeedbackPanel({ onApprove, onFeedback, isResuming }: FeedbackPanelProps) {
  const [feedback, setFeedback] = useState('')

  const handleFeedback = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = feedback.trim()
    if (!trimmed) return
    onFeedback(trimmed)
    setFeedback('')
  }

  return (
    <div className="card bg-base-200 shadow-md">
      <div className="card-body gap-5">
        <h3 className="card-title text-base">What would you like to do?</h3>

        {/* Approve */}
        <button
          className="btn btn-success btn-lg gap-2 w-full"
          onClick={onApprove}
          disabled={isResuming}
        >
          {isResuming ? (
            <span className="loading loading-spinner loading-sm" />
          ) : (
            <span>✅</span>
          )}
          Approve & Download Itinerary
        </button>

        <div className="divider text-xs opacity-50">or request changes</div>

        {/* Feedback */}
        <form onSubmit={handleFeedback} className="flex flex-col gap-3">
          <textarea
            className="textarea textarea-bordered w-full h-24 resize-none text-sm focus:textarea-primary"
            placeholder="e.g. Add more restaurant recommendations, swap Day 3 for a beach day, include museums…"
            value={feedback}
            onChange={e => setFeedback(e.target.value)}
            disabled={isResuming}
          />
          <button
            type="submit"
            className="btn btn-outline btn-primary w-full gap-2"
            disabled={!feedback.trim() || isResuming}
          >
            {isResuming ? (
              <span className="loading loading-spinner loading-sm" />
            ) : null}
            Submit Feedback
          </button>
        </form>
      </div>
    </div>
  )
}
