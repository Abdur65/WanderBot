import { forwardRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { WeatherDay } from '../../api/types'

interface ItineraryViewProps {
  draft: string
  verificationScore: number
  weatherData?: WeatherDay[]
}

interface Venue {
  time: string
  name: string
  content: string
  travelTo?: string
}

interface Day {
  label: string
  shortLabel: string
  intro: string
  venues: Venue[]
}

// ── parser ────────────────────────────────────────────────────────────────────

function parseItinerary(md: string): { title: string; days: Day[]; budget: string } {
  // Separate the budget section (everything after the '---' divider)
  const dividerIdx = md.search(/^---\s*$/m)
  const body   = dividerIdx >= 0 ? md.slice(0, dividerIdx).trim() : md
  const budget = dividerIdx >= 0 ? md.slice(dividerIdx).replace(/^---\s*/m, '').trim() : ''

  const titleMatch = body.match(/^#\s+(.+)$/m)
  const title = titleMatch?.[1]?.trim() ?? ''
  const rest  = body.replace(/^#[^#].*\n?/m, '')

  const chunks = rest.split(/(?=^## )/m).filter(s => s.trim())
  const days: Day[] = []

  for (const chunk of chunks) {
    const lines = chunk.split('\n')
    const heading = lines[0].replace(/^##\s*/, '').trim()
    if (!/day\s*\d/i.test(heading)) continue

    const shortLabel = heading.match(/Day\s*\d+/i)?.[0] ?? heading
    const content = lines.slice(1).join('\n')
    const venueParts = content.split(/(?=^### )/m)
    let intro = ''
    const venues: Venue[] = []

    for (const vp of venueParts) {
      if (!vp.startsWith('### ')) { intro = vp.trim(); continue }
      const vlines = vp.split('\n')
      const vheading = vlines[0].replace(/^###\s*/, '').trim()
      const vcontent = vlines.slice(1).join('\n').trim()

      const timeMatch   = vheading.match(/^(\d{1,2}:\d{2}\s*[–\-–]\s*\d{1,2}:\d{2})\s+(.+)/)
      const travelMatch = vcontent.match(/^↳\s+.+$/m)
      const travelTo    = travelMatch?.[0]?.trim()
      const cleanContent = vcontent.replace(/^↳\s+.+\n?/m, '').trim()

      venues.push({
        time: timeMatch?.[1]?.replace(/\s/g, '') ?? '',
        name: timeMatch?.[2]?.trim() ?? vheading,
        content: cleanContent,
        travelTo,
      })
    }

    days.push({ label: heading, shortLabel, intro, venues })
  }

  return { title, days, budget }
}

function timeColor(time: string) {
  const h = parseInt(time.split(':')[0], 10)
  if (isNaN(h))  return 'badge-neutral'
  if (h < 12)    return 'badge-info'
  if (h < 17)    return 'badge-warning'
  return 'badge-error'
}

// ── venue card ────────────────────────────────────────────────────────────────

function VenueCard({ venue, isLast }: { venue: Venue; isLast: boolean }) {

  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center pt-1">
        <div className="w-3 h-3 rounded-full border-2 border-primary bg-primary mt-1 flex-shrink-0" />
        {!isLast && <div className="w-px flex-1 bg-primary/20 mt-1" />}
      </div>

      <div className="flex-1 pb-1">
        <div className="flex items-start gap-2 flex-wrap">
          {venue.time && (
            <span className={`badge badge-sm font-mono flex-shrink-0 mt-0.5 ${timeColor(venue.time)}`}>
              {venue.time}
            </span>
          )}
          <span className="font-semibold text-base-content leading-snug">{venue.name}</span>
        </div>

        {venue.content && (
          <div className="mt-2 pl-1 prose prose-sm max-w-none
            prose-p:text-base-content/80 prose-p:my-1 prose-strong:text-base-content
            prose-ul:my-1 prose-li:my-0 prose-headings:text-primary
            prose-table:text-sm">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{venue.content}</ReactMarkdown>
          </div>
        )}

        {!isLast && venue.travelTo && (
          <div className="flex items-center gap-1.5 mt-2 mb-1 text-xs text-base-content/40 font-mono">
            <span className="text-primary/40">↳</span>
            <span>{venue.travelTo.replace(/^↳\s*/, '')}</span>
          </div>
        )}
        {!isLast && !venue.travelTo && <div className="pb-3" />}
      </div>
    </div>
  )
}

function WeatherBadge({ w }: { w: WeatherDay }) {
  const temp = w.high_c !== null ? `${Math.round(w.high_c)}°` : null
  const rain = w.rain_prob !== null && w.rain_prob > 20 ? `${w.rain_prob}%` : null
  if (!temp && !rain) return null
  return (
    <span className="flex items-center gap-1 text-xs text-base-content/40 font-normal ml-1">
      {temp && <span>{temp}</span>}
      {rain && <span className="text-info">☂ {rain}</span>}
    </span>
  )
}

function DayPanel({ day }: { day: Day }) {
  return (
    <div>
      {day.venues.map((v, i) => (
        <VenueCard key={i} venue={v} isLast={i === day.venues.length - 1} />
      ))}
    </div>
  )
}

// ── main component ────────────────────────────────────────────────────────────

const ItineraryView = forwardRef<HTMLDivElement, ItineraryViewProps>(
  function ItineraryView({ draft, verificationScore: _score, weatherData = [] }, ref) {
    const cleanDraft = draft
      .replace(/^>\s+\*\*Verification:\*\*[^\n]*\n\n/, '')
      .replace(/\[src:[^\]]+\]/gi, '')
      .replace(/\[Unverified[^\]]*\]/gi, '')

    const { title, days, budget } = parseItinerary(cleanDraft)

    // Fallback for unstructured output
    if (days.length === 0) {
      return (
        <div className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold">Your Itinerary</h2>
          <div className="card bg-base-200 shadow-md">
            <div ref={ref} className="card-body p-5 sm:p-7">
              <div className="prose prose-sm sm:prose max-w-none prose-headings:text-primary">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{cleanDraft}</ReactMarkdown>
              </div>
            </div>
          </div>
        </div>
      )
    }

    return (
      <div className="flex flex-col gap-3">
        <h2 className="text-lg font-semibold">{title || 'Your Itinerary'}</h2>

        <div ref={ref} className="card bg-base-200 shadow-md">
          <div className="card-body p-5 sm:p-6 flex flex-col gap-6">

            {/* ── Days ──────────────────────────────────────────────── */}
            {days.map((day, i) => {
              const wx = weatherData[i]
              return (
                <div key={i}>
                  <div className="flex items-center gap-2 mb-3">
                    <p className="text-sm font-bold text-primary">{day.label}</p>
                    {wx && <WeatherBadge w={wx} />}
                  </div>
                  {day.intro && (
                    <p className="text-sm text-base-content/60 italic mb-3 pl-6 border-l-2 border-primary/20">
                      {day.intro}
                    </p>
                  )}
                  <DayPanel day={day} />
                  {(i < days.length - 1 || budget) && <div className="divider my-2 opacity-30" />}
                </div>
              )
            })}

            {/* ── Budget ────────────────────────────────────────────── */}
            {budget && (
              <div>
                <p className="text-sm font-bold text-primary mb-3">Budget Estimate</p>
                <div className="prose prose-sm max-w-none
                  prose-headings:text-primary prose-strong:text-base-content
                  prose-table:w-full prose-th:bg-base-300 prose-th:px-3 prose-th:py-2
                  prose-td:px-3 prose-td:py-1.5 prose-td:border prose-td:border-base-300">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{budget}</ReactMarkdown>
                </div>
              </div>
            )}

          </div>
        </div>
      </div>
    )
  }
)

export default ItineraryView
