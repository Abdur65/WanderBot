import {
  Search,
  BookOpen,
  Database,
  Wifi,
  PenLine,
  MapPin,
  ShieldCheck,
  CheckCircle,
  Check,
  Loader2,
  Circle,
} from 'lucide-react'

interface Step {
  key: string
  label: string
  icon: React.ReactNode
}

const STEPS: Step[] = [
  { key: 'analyze',            label: 'Analyzing',  icon: <Search size={14} /> },
  { key: 'curate',             label: 'Curating',   icon: <BookOpen size={14} /> },
  { key: 'rag_retriever',      label: 'Retrieving', icon: <Database size={14} /> },
  { key: 'live_verifier',      label: 'Verifying',  icon: <Wifi size={14} /> },
  { key: 'draft_plan',         label: 'Drafting',   icon: <PenLine size={14} /> },
  { key: 'logistics_enricher', label: 'Routing',    icon: <MapPin size={14} /> },
  { key: 'validate_citations', label: 'Validating', icon: <ShieldCheck size={14} /> },
  { key: 'human_review',       label: 'Ready',      icon: <CheckCircle size={14} /> },
]

interface PipelineProgressProps {
  activeNode: string | null
  completedNodes: string[]
}

export default function PipelineProgress({ activeNode, completedNodes }: PipelineProgressProps) {
  return (
    <div className="w-full">
      {/* Desktop: horizontal steps */}
      <ul className="steps steps-horizontal w-full hidden md:grid">
        {STEPS.map(step => {
          const done = completedNodes.includes(step.key)
          const active = activeNode === step.key
          return (
            <li
              key={step.key}
              className={`step text-xs ${done || active ? 'step-primary' : ''}`}
            >
              <span className="flex flex-col items-center gap-0.5">
                <span className={active ? 'animate-pulse' : ''}>
                  {active ? <Loader2 size={14} className="animate-spin" /> : step.icon}
                </span>
                <span className={`${active ? 'text-primary font-semibold' : 'opacity-60'}`}>
                  {step.label}
                </span>
              </span>
            </li>
          )
        })}
      </ul>

      {/* Mobile: vertical list */}
      <ul className="flex flex-col gap-1 md:hidden">
        {STEPS.map(step => {
          const done = completedNodes.includes(step.key)
          const active = activeNode === step.key
          return (
            <li key={step.key} className="flex items-center gap-3 text-sm">
              <span className={`w-6 flex justify-center ${active ? 'animate-pulse text-primary' : done ? 'text-success' : 'opacity-30'}`}>
                {done ? <Check size={14} /> : active ? <Loader2 size={14} className="animate-spin" /> : <Circle size={14} />}
              </span>
              <span className={`flex items-center gap-1.5 ${active ? 'text-primary font-semibold' : done ? '' : 'opacity-40'}`}>
                {step.icon} {step.label}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
