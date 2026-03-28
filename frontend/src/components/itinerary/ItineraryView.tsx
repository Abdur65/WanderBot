import { forwardRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ItineraryViewProps {
  draft: string
  verificationScore: number
}

interface Venue {
  time: string
  name: string
  content: string
  travelTo?: string  // "↳ walking · ~15 min" connector to the next venue
}

interface Day {
  label: string       // full: "Day 1 — Historic Paris"
  shortLabel: string  // tab:  "Day 1"
  intro: string       // optional thematic sentence before the venues
  venues: Venue[]
}

// ── parser ────────────────────────────────────────────────────────────────────

function parseItinerary(md: string): { title: string; days: Day[] } {
  const titleMatch = md.match(/^#\s+(.+)$/m)
  const title = titleMatch?.[1]?.trim() ?? ''
  const body = md.replace(/^#[^#].*\n?/m, '')

  // Split on '## ' headings while keeping the delimiter
  const chunks = body.split(/(?=^## )/m).filter(s => s.trim())
  const days: Day[] = []

  for (const chunk of chunks) {
    const lines = chunk.split('\n')
    const heading = lines[0].replace(/^##\s*/, '').trim()
    if (!/day\s*\d/i.test(heading)) continue

    const shortLabel = heading.match(/Day\s*\d+/i)?.[0] ?? heading
    const rest = lines.slice(1).join('\n')

    // Split on '### ' headings
    const venueParts = rest.split(/(?=^### )/m)
    let intro = ''
    const venues: Venue[] = []

    for (const vp of venueParts) {
      if (!vp.startsWith('### ')) {
        intro = vp.trim()
        continue
      }
      const vlines = vp.split('\n')
      const vheading = vlines[0].replace(/^###\s*/, '').trim()
      const vcontent = vlines.slice(1).join('\n').trim()

      // Match "09:00–11:00  Venue Name" (en-dash, hyphen, or space-hyphen-space)
      const timeMatch = vheading.match(/^(\d{1,2}:\d{2}\s*[–\-–]\s*\d{1,2}:\d{2})\s+(.+)/)
      // Extract the ↳ travel connector line if present (inserted by logistics_enricher)
      const travelMatch = vcontent.match(/^↳\s+.+$/m)
      const travelTo = travelMatch?.[0]?.trim()
      const contentWithoutTravel = vcontent.replace(/^↳\s+.+\n?/m, '').trim()

      venues.push({
        time: timeMatch?.[1]?.replace(/\s/g, '') ?? '',
        name: timeMatch?.[2]?.trim() ?? vheading,
        content: contentWithoutTravel,
        travelTo,
      })
    }

    days.push({ label: heading, shortLabel, intro, venues })
  }

  return { title, days }
}

// Returns a colour class based on the hour of day
function timeColor(time: string): string {
  const h = parseInt(time.split(':')[0], 10)
  if (isNaN(h)) return 'badge-neutral'
  if (h < 12) return 'badge-info'      // morning — blue
  if (h < 17) return 'badge-warning'   // afternoon — amber
  return 'badge-error'                 // evening — red/pink
}

// ── sub-components ────────────────────────────────────────────────────────────

function VenueCard({ venue, isLast }: { venue: Venue; isLast: boolean }) {
  const [open, setOpen] = useState(true)
  const colorClass = timeColor(venue.time)

  return (
    <div className="flex gap-3">
      {/* Timeline spine */}
      <div className="flex flex-col items-center pt-1">
        <div className={`w-3 h-3 rounded-full border-2 border-primary mt-1 flex-shrink-0 ${open ? 'bg-primary' : 'bg-base-100'}`} />
        {!isLast && <div className="w-px flex-1 bg-primary/20 mt-1" />}
      </div>

      {/* Card + travel connector */}
      <div className="flex-1 pb-1">
        <button
          className="w-full text-left"
          onClick={() => setOpen(o => !o)}
        >
          <div className="flex items-start gap-2 flex-wrap">
            {venue.time && (
              <span className={`badge badge-sm font-mono flex-shrink-0 mt-0.5 ${colorClass}`}>
                {venue.time}
              </span>
            )}
            <span className="font-semibold text-base-content leading-snug">
              {venue.name}
            </span>
            <span className="ml-auto text-base-content/30 text-xs mt-0.5 flex-shrink-0">
              {open ? '▲' : '▼'}
            </span>
          </div>
        </button>

        {open && venue.content && (
          <div className="mt-2 pl-1 prose prose-sm max-w-none
            prose-p:text-base-content/80 prose-p:my-1
            prose-strong:text-base-content
            prose-ul:my-1 prose-li:my-0
            prose-headings:text-primary">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {venue.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Travel connector to next venue */}
        {!isLast && venue.travelTo && (
          <div className="flex items-center gap-2 mt-2 mb-1 text-xs text-base-content/45 font-mono">
            <span className="text-primary/40">↳</span>
            {/* strip the leading "↳ " from the stored string */}
            <span>{venue.travelTo.replace(/^↳\s*/, '')}</span>
          </div>
        )}
        {/* Spacer when no connector */}
        {!isLast && !venue.travelTo && <div className="pb-3" />}
      </div>
    </div>
  )
}

function DayPanel({ day }: { day: Day }) {
  return (
    <div className="pt-4">
      {day.intro && (
        <p className="text-sm text-base-content/60 italic mb-4 pl-6 border-l-2 border-primary/20">
          {day.intro}
        </p>
      )}
      {day.venues.length === 0 && (
        <div className="prose prose-sm max-w-none text-base-content/70">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{day.intro}</ReactMarkdown>
        </div>
      )}
      {day.venues.map((v, i) => (
        <VenueCard key={i} venue={v} isLast={i === day.venues.length - 1} />
      ))}
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

const ItineraryView = forwardRef<HTMLDivElement, ItineraryViewProps>(
  function ItineraryView({ draft, verificationScore: _score }, ref) {
    const [activeDay, setActiveDay] = useState(0)

    const cleanDraft = draft
      .replace(/^>\s+\*\*Verification:\*\*[^\n]*\n\n/, '')
      .replace(/\[src:[^\]]+\]/gi, '')
      .replace(/\[Unverified[^\]]*\]/gi, '')

    const { title, days } = parseItinerary(cleanDraft)

    // Fallback: if parsing yields nothing, render plain markdown
    if (days.length === 0) {
      return (
        <div className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold">Your Itinerary</h2>
          <div className="card bg-base-200 shadow-md">
            <div className="card-body p-5 sm:p-7 max-h-[70vh] overflow-y-auto">
              <div
                ref={ref}
                className="prose prose-sm sm:prose max-w-none prose-headings:text-primary prose-strong:text-base-content"
              >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{cleanDraft}</ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )
    }

    return (
      <div className="flex flex-col gap-3">
        {/* Title */}
        <h2 className="text-lg font-semibold">{title || 'Your Itinerary'}</h2>

        <div className="card bg-base-200 shadow-md" ref={ref}>
          {/* Day tabs */}
          <div className="border-b border-base-300 overflow-x-auto">
            <div className="flex min-w-max px-4 pt-3 gap-1">
              {days.map((day, i) => (
                <button
                  key={i}
                  onClick={() => setActiveDay(i)}
                  className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors whitespace-nowrap
                    ${activeDay === i
                      ? 'bg-base-100 text-primary border-b-2 border-primary -mb-px'
                      : 'text-base-content/50 hover:text-base-content/80'
                    }`}
                >
                  {day.shortLabel}
                </button>
              ))}
            </div>
          </div>

          {/* Active day content */}
          <div className="card-body p-5 sm:p-6 max-h-[65vh] overflow-y-auto">
            {/* Day theme header */}
            <div className="mb-2">
              <span className="text-base font-semibold text-primary">
                {days[activeDay]?.label}
              </span>
            </div>
            <DayPanel day={days[activeDay]} />
          </div>
        </div>

        {/* Day quick-jump dots for mobile */}
        {days.length > 1 && (
          <div className="flex justify-center gap-2 pt-1">
            {days.map((_, i) => (
              <button
                key={i}
                onClick={() => setActiveDay(i)}
                className={`w-2 h-2 rounded-full transition-colors ${
                  activeDay === i ? 'bg-primary' : 'bg-base-content/20'
                }`}
              />
            ))}
          </div>
        )}
      </div>
    )
  }
)

export default ItineraryView
