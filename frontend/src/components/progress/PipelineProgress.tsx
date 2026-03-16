interface Step {
  key: string
  label: string
  icon: string
}

const STEPS: Step[] = [
  { key: 'analyze',            label: 'Analyzing',      icon: '🔍' },
  { key: 'curate',             label: 'Curating',       icon: '📚' },
  { key: 'rag_retriever',      label: 'Retrieving',     icon: '🗂️' },
  { key: 'live_verifier',      label: 'Verifying',      icon: '📡' },
  { key: 'draft_plan',         label: 'Drafting',       icon: '✍️' },
  { key: 'validate_citations', label: 'Validating',     icon: '🔒' },
  { key: 'human_review',       label: 'Ready',          icon: '✅' },
]

interface PipelineProgressProps {
  activeNode: string | null
  completedNodes: string[]
}

export default function PipelineProgress({ activeNode, completedNodes }: PipelineProgressProps) {
  return (
    <div className="w-full">
      {/* Desktop: horizontal steps */}
      <ul className="steps steps-horizontal w-full hidden md:flex">
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
                  {active ? '⟳' : step.icon}
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
              <span className={`w-6 text-center ${active ? 'animate-pulse text-primary' : done ? 'text-success' : 'opacity-30'}`}>
                {done ? '✓' : active ? '⟳' : '○'}
              </span>
              <span className={active ? 'text-primary font-semibold' : done ? '' : 'opacity-40'}>
                {step.icon} {step.label}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
