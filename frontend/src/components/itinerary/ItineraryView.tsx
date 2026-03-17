import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ItineraryViewProps {
  draft: string
  verificationScore: number
}

function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const colour = pct >= 80 ? 'badge-success' : pct >= 50 ? 'badge-warning' : 'badge-error'
  const dot = pct >= 80 ? 'bg-success' : pct >= 50 ? 'bg-warning' : 'bg-error'
  return (
    <span className={`badge ${colour} badge-outline gap-1.5 text-sm py-3 px-4`}>
      <span className={`inline-block w-2 h-2 rounded-full ${dot}`} />
      {pct}% verified
    </span>
  )
}

export default function ItineraryView({ draft, verificationScore }: ItineraryViewProps) {
  // Strip the prepended badge blockquote that the backend adds — we render it ourselves
  // Also strip [src:N] and [Unverified...] tags — scoring is already done, tags clutter the output
  const cleanDraft = draft
    .replace(/^>\s+\*\*Verification:\*\*[^\n]*\n\n/, '')
    .replace(/\[src:\d+\]/g, '')
    .replace(/\[Unverified[^\]]*\]/gi, '')

  return (
    <div className="flex flex-col gap-4">
      {/* Verification header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold">Your Itinerary</h2>
        <ScoreBadge score={verificationScore} />
      </div>

      {/* Markdown body */}
      <div className="card bg-base-200 shadow-md">
        <div className="card-body p-5 sm:p-7 itinerary-scroll max-h-[60vh] overflow-y-auto">
          <div className="prose prose-sm sm:prose max-w-none prose-headings:text-primary prose-strong:text-base-content prose-a:text-secondary">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {cleanDraft}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  )
}
