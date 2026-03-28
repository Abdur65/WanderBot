import { useState } from 'react'
import { Plane, MapPin } from 'lucide-react'

const EXAMPLES = [
  '7 days in Tokyo, Japan — budget traveller, love street food and photography',
  '3 days in Jeddah, Saudi Arabia. Solo, nature, high-range budget, and local culture',
  '4 days in Chittagong, Bangladesh, solo, love nature, high-range budget, and local culture',
  '3 days in Kyoto, solo, moderate pace, interested in street food and nature walks',
  '10 days in Bali, Indonesia — luxury, beach, yoga retreats, no crowded spots',
]

interface TripInputProps {
  onSubmit: (message: string) => void
}

export default function TripInput({ onSubmit }: TripInputProps) {
  const [message, setMessage] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = message.trim()
    if (!trimmed) return
    onSubmit(trimmed)
  }

  return (
    <div className="phase-enter flex flex-col items-center justify-center min-h-[calc(100vh-64px)] px-4 py-12">
      {/* Hero */}
      <div className="text-center mb-10 max-w-2xl">
        <div className="flex justify-center mb-4">
          <Plane size={56} className="text-primary" />
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight mb-3">
          Plan Your{' '}
          <span className="text-primary">Dream Trip</span>
        </h1>
        <p className="text-base-content/60 text-lg">
          Describe your trip and let AI craft a personalised, source-verified itinerary in minutes.
        </p>
      </div>

      {/* Input card */}
      <div className="card bg-base-200 shadow-xl w-full max-w-2xl">
        <div className="card-body gap-4">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <textarea
              className="textarea textarea-bordered textarea-lg w-full h-36 resize-none text-base leading-relaxed focus:textarea-primary"
              placeholder="e.g. 7 days in Tokyo, Japan — budget traveller, love street food and photography, want scenic spots for photos…"
              value={message}
              onChange={e => setMessage(e.target.value)}
              onKeyDown={e => {
                if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit(e)
              }}
            />
            <button
              type="submit"
              disabled={!message.trim()}
              className="btn btn-primary btn-lg w-full gap-2"
            >
              <span>Plan My Trip</span>
              <span>→</span>
            </button>
          </form>

          <div className="divider text-xs opacity-50">or try an example</div>

          {/* Example chips */}
          <div className="flex flex-col gap-2">
            {EXAMPLES.map(ex => (
              <button
                key={ex}
                className="btn btn-ghost btn-sm justify-start text-left h-auto py-2 px-3 font-normal text-base-content/70 hover:text-base-content border border-base-300 hover:border-primary transition-colors"
                onClick={() => setMessage(ex)}
              >
                <MapPin size={14} className="mr-1 shrink-0" />
                <span className="text-sm leading-snug">{ex}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <p className="text-xs text-base-content/30 mt-6">
        Powered by LangGraph · Groq · Tavily · Qdrant
      </p>
    </div>
  )
}
