import { useEffect, useRef, useState } from 'react'
import './App.css'
import { usePlanSession } from './hooks/usePlanSession'
import Navbar from './components/layout/Navbar'
import TripInput from './components/chat/TripInput'
import FeedbackPanel from './components/chat/FeedbackPanel'
import PipelineProgress from './components/progress/PipelineProgress'
import ItineraryView from './components/itinerary/ItineraryView'
import { CheckCircle, Download, FileDown, CalendarDays, AlertTriangle } from 'lucide-react'

type Theme = 'dark' | 'light'

const NODE_STATUS: Record<string, string> = {
  analyze:            'Analyzing your trip request…',
  curate:             'Curating knowledge from travel sources…',
  rag_retriever:      'Retrieving relevant context…',
  live_verifier:      'Verifying live travel data…',
  draft_plan:         'Drafting your personalised itinerary…',
  validate_citations: 'Validating source citations…',
  human_review:       'Itinerary ready for your review!',
}

export default function App() {
  const [theme, setTheme] = useState<Theme>('dark')
  const { state, submitTrip, submitFeedback, triggerDownload, triggerCalendarDownload, reset } = usePlanSession()
  const itineraryRef = useRef<HTMLDivElement>(null)

  const downloadAsPdf = () => {
    if (!itineraryRef.current) return
    const destination = (state.destination || 'Trip').replace(/[\s,]+/g, ' ').trim()
    const html = itineraryRef.current.innerHTML
    const printWindow = window.open('', '_blank')
    if (!printWindow) return
    printWindow.document.write(`<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Itinerary — ${destination}</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: Georgia, 'Times New Roman', serif;
      font-size: 13px;
      line-height: 1.7;
      color: #111;
      background: #fff;
      padding: 40px 52px;
      max-width: 780px;
      margin: 0 auto;
    }
    h1, h2, h3, h4 { font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a1a2e; margin: 1.4em 0 0.4em; }
    h1 { font-size: 22px; border-bottom: 2px solid #1a1a2e; padding-bottom: 6px; }
    h2 { font-size: 17px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }
    h3 { font-size: 14px; }
    p  { margin: 0.5em 0; }
    ul, ol { padding-left: 1.4em; margin: 0.5em 0; }
    li { margin: 0.2em 0; }
    strong { font-weight: 700; }
    em { font-style: italic; color: #444; }
    a  { color: #1a1a2e; text-decoration: underline; }
    hr { border: none; border-top: 1px solid #ddd; margin: 1em 0; }
    table { width: 100%; border-collapse: collapse; margin: 0.8em 0; }
    th, td { border: 1px solid #ccc; padding: 6px 10px; text-align: left; font-size: 12px; }
    th { background: #f0f0f0; font-weight: 700; }
    blockquote { border-left: 3px solid #aaa; padding-left: 12px; color: #555; margin: 0.8em 0; }
    code { font-family: monospace; background: #f4f4f4; padding: 1px 4px; border-radius: 3px; font-size: 12px; }
    @media print {
      body { padding: 0; }
      a { color: inherit; text-decoration: none; }
    }
  </style>
</head>
<body>
  <h1>${destination} — Travel Itinerary</h1>
  ${html}
</body>
</html>`)
    printWindow.document.close()
    printWindow.focus()
    // Small delay so the browser finishes rendering before the print dialog opens
    setTimeout(() => {
      printWindow.print()
      printWindow.close()
    }, 400)
  }

  // Apply theme to <html>
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => (t === 'dark' ? 'light' : 'dark'))

  const isActive = state.phase !== 'idle'
  const isStreaming = state.phase === 'streaming' || state.phase === 'resuming'
  const isInterrupted = state.phase === 'interrupted'
  const isDone = state.phase === 'done'
  const isError = state.phase === 'error'

  return (
    <div className="min-h-screen bg-base-100 flex flex-col">
      <Navbar
        theme={theme}
        onToggleTheme={toggleTheme}
        showNewTrip={isActive}
        onNewTrip={reset}
      />

      <main className="flex-1">

        {/* ── IDLE ─────────────────────────────────────────────── */}
        {state.phase === 'idle' && (
          <TripInput onSubmit={submitTrip} />
        )}

        {/* ── STREAMING / RESUMING ──────────────────────────────── */}
        {(isStreaming) && (
          <div className="phase-enter max-w-3xl mx-auto px-4 py-10 flex flex-col gap-8">

            {/* Destination heading */}
            {state.destination && (
              <div className="text-center">
                <h2 className="text-2xl font-bold">
                  Planning your trip to{' '}
                  <span className="text-primary">{state.destination}</span>
                </h2>
              </div>
            )}
            {!state.destination && (
              <div className="text-center">
                <h2 className="text-2xl font-bold text-base-content/60">
                  Starting your trip plan…
                </h2>
              </div>
            )}

            {/* Pipeline steps */}
            <div className="card bg-base-200 shadow-md">
              <div className="card-body">
                <PipelineProgress
                  activeNode={state.activeNode}
                  completedNodes={state.completedNodes}
                />
              </div>
            </div>

            {/* Active step status */}
            {state.activeNode && (
              <div className="alert bg-base-200 border border-primary/30">
                <span className="loading loading-dots loading-sm text-primary" />
                <span className="text-sm">
                  {NODE_STATUS[state.activeNode] ?? `Running ${state.activeNode}…`}
                </span>
              </div>
            )}

            {/* Live token stream (draft_plan phase) */}
            {state.streamingText && (
              <div className="card bg-base-300 shadow-inner">
                <div className="card-body p-4">
                  <p className="text-xs font-mono text-base-content/40 mb-2 uppercase tracking-widest">
                    Live preview
                  </p>
                  <div
                    className={`font-mono text-xs text-base-content/70 whitespace-pre-wrap max-h-52 overflow-y-auto leading-relaxed ${!state.activeNode ? '' : 'stream-cursor'}`}
                  >
                    {state.streamingText}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── INTERRUPTED ──────────────────────────────────────── */}
        {isInterrupted && (
          <div className="phase-enter max-w-3xl mx-auto px-4 py-8 flex flex-col gap-6">

            {/* Pipeline (all done) */}
            <div className="card bg-base-200 shadow-md">
              <div className="card-body py-4">
                <PipelineProgress
                  activeNode={null}
                  completedNodes={state.completedNodes}
                />
              </div>
            </div>

            {/* Itinerary */}
            <ItineraryView
              ref={itineraryRef}
              draft={state.draftItinerary}
              verificationScore={state.verificationScore}

              weatherData={state.weatherData}
            />

            {/* Feedback / Approve */}
            <FeedbackPanel
              onApprove={() => submitFeedback('approve')}
              onFeedback={submitFeedback}
              isResuming={isStreaming}
            />
          </div>
        )}

        {/* ── DONE ─────────────────────────────────────────────── */}
        {isDone && (
          <div className="phase-enter max-w-3xl mx-auto px-4 py-8 flex flex-col gap-6">
            {/* Success banner */}
            <div className="alert alert-success shadow-lg">
              <CheckCircle size={22} />
              <div>
                <h3 className="font-bold">Itinerary approved!</h3>
                <p className="text-sm opacity-80">
                  Your trip to{' '}
                  <strong>{state.destination || 'your destination'}</strong> is ready.
                </p>
              </div>
            </div>

            {/* Itinerary view */}
            <ItineraryView
              ref={itineraryRef}
              draft={state.draftItinerary}
              verificationScore={state.verificationScore}

              weatherData={state.weatherData}
            />

            {/* Action buttons */}
            <div className="flex flex-col gap-3">
              <div className="flex flex-col sm:flex-row gap-3">
                <button
                  className="btn btn-primary flex-1 gap-2"
                  onClick={triggerDownload}
                >
                  <Download size={16} /> Download as Markdown
                </button>
                <button
                  className="btn btn-outline btn-primary flex-1 gap-2"
                  onClick={downloadAsPdf}
                >
                  <FileDown size={16} />
                  Download as PDF
                </button>
                {state.travelStartDate && (
                  <button
                    className="btn btn-outline btn-primary flex-1 gap-2"
                    onClick={triggerCalendarDownload}
                  >
                    <CalendarDays size={16} />
                    Export Calendar
                  </button>
                )}
              </div>
              <button className="btn btn-ghost w-full gap-2" onClick={reset}>
                Plan Another Trip
              </button>
            </div>
          </div>
        )}

        {/* ── ERROR ─────────────────────────────────────────────── */}
        {isError && (
          <div className="phase-enter max-w-xl mx-auto px-4 py-16 flex flex-col gap-6 items-center text-center">
            <AlertTriangle size={48} className="text-error" />
            <div>
              <h2 className="text-2xl font-bold mb-2">Something went wrong</h2>
              <p className="text-base-content/60 text-sm mb-6">
                {state.error ?? 'An unexpected error occurred.'}
              </p>
              <button className="btn btn-primary" onClick={reset}>
                Try Again
              </button>
            </div>
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="footer footer-center py-4 text-base-content/30 text-xs border-t border-base-300">
        <p>WanderBot · AI-powered travel planning · Verify all details before booking</p>
      </footer>
    </div>
  )
}
