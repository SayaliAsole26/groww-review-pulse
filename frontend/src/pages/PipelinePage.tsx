import { useCallback, useState } from 'react'
import { GlassCard } from '../components/GlassCard'
import { Icon } from '../components/Icon'
import { delivery, kpis, settings } from '../data/mock'
import { openExternal, useToast } from '../lib/ui'

const STAGE_LABELS = ['Ingest', 'Analyze', 'Render', 'Docs', 'Email'] as const

function sleep(ms: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(resolve, ms)
  })
}

export function PipelinePage() {
  const { showToast } = useToast()
  const [completedCount, setCompletedCount] = useState<number>(STAGE_LABELS.length)
  const [running, setRunning] = useState(false)
  const [statusLabel, setStatusLabel] = useState('COMPLETED')
  const [logLines, setLogLines] = useState<string[]>([
    '[09:00:02] pulse run starting (run_id=groww:2026-W25)',
    '[09:01:15] Ingestion complete: raw=9743 processed=1669',
    '[09:04:32] Analyze complete: themes=3',
    '[09:05:01] Docs delivery complete (inserted=true)',
    '[09:05:18] Email delivery complete (created=true)',
  ])

  const progress = (completedCount / STAGE_LABELS.length) * 100

  const runPipeline = useCallback(async () => {
    if (running) return
    setRunning(true)
    setStatusLabel('RUNNING')
    setCompletedCount(0)
    setLogLines([`[${new Date().toLocaleTimeString()}] Re-run pipeline started...`])

    const steps = [
      'Ingestion complete: raw=9743 processed=1669',
      `Analyze complete: themes=${kpis.themes}`,
      'Render complete: doc + email payloads saved',
      'Docs delivery complete (inserted=true)',
      'Email delivery complete (created=true)',
    ]

    for (let i = 0; i < steps.length; i += 1) {
      await sleep(900)
      setCompletedCount(i + 1)
      setLogLines((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${steps[i]}`])
    }

    setStatusLabel('COMPLETED')
    setRunning(false)
    showToast('Pipeline re-run finished successfully')
  }, [running, showToast])

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h3 className="text-3xl font-bold md:text-4xl">Pipeline Monitor</h3>
          <p className="mt-1 text-on-surface-variant">Real-time status of ingestion and report generation.</p>
        </div>
        <button
          type="button"
          disabled={running}
          onClick={runPipeline}
          className="flex items-center gap-2 rounded-xl bg-primary px-4 py-3 text-xs font-bold text-on-primary shadow-[0_0_20px_rgba(68,237,183,0.3)] disabled:opacity-50 hover:brightness-110"
        >
          <Icon name="restart_alt" /> Re-run Pipeline
        </button>
      </section>

      <GlassCard className="p-6">
        <div className="mb-8 flex items-center justify-between">
          <h4 className="flex items-center gap-2 text-lg font-semibold">
            <Icon name="analytics" className="text-primary" /> Processing Workflow
          </h4>
          <span
            className={`rounded-full border px-3 py-1 text-[11px] font-semibold ${
              running
                ? 'border-tertiary/30 bg-tertiary-container/20 text-tertiary'
                : 'border-primary/20 bg-primary-container/20 text-primary'
            }`}
          >
            {statusLabel}
          </span>
        </div>
        <div className="relative flex items-center justify-between">
          <div className="absolute left-0 top-1/2 z-0 h-0.5 w-full -translate-y-1/2 bg-outline-variant/30" />
          <div
            className="absolute left-0 top-1/2 z-0 h-0.5 -translate-y-1/2 bg-primary shadow-[0_0_8px_#44edb7] transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
          {STAGE_LABELS.map((label, index) => {
            const done = index < completedCount
            const active = running && index === completedCount
            return (
              <div key={label} className="relative z-10 flex flex-col items-center gap-2">
                <div
                  className={`flex h-12 w-12 items-center justify-center rounded-full border-4 border-background ${
                    done
                      ? 'bg-primary text-on-primary'
                      : active
                        ? 'border-primary pulse-indicator bg-background'
                        : 'border-outline-variant/30 bg-background'
                  }`}
                >
                  {done ? (
                    <Icon name="check" />
                  ) : (
                    <div className={`h-4 w-4 rounded-full ${active ? 'bg-primary' : 'bg-outline-variant/30'}`} />
                  )}
                </div>
                <span className={`text-xs font-medium ${done || active ? 'text-on-surface' : 'text-on-surface-variant'}`}>
                  {label}
                </span>
              </div>
            )
          })}
        </div>
      </GlassCard>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <GlassCard className="space-y-6 p-6 lg:col-span-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-lg font-semibold">Last Run Instance</span>
              <code className="rounded bg-surface-container px-2 py-1 text-[11px] text-tertiary">{delivery.runId}</code>
            </div>
            <span className="text-xs text-on-surface-variant">{running ? 'Running…' : 'Duration: ~6 min'}</span>
          </div>
          <div>
            <div className="mb-1 flex justify-between text-[11px] uppercase tracking-tight text-on-surface-variant">
              <span>Pipeline Progress</span>
              <span className="text-primary">{Math.round(progress)}%</span>
            </div>
            <div className="h-3 overflow-hidden rounded-full border border-outline-variant/10 bg-surface-container-lowest">
              <div className="h-full bg-primary transition-all duration-500" style={{ width: `${progress}%` }} />
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-outline-variant/10 bg-surface-container-low p-4">
              <p className="mb-1 text-[11px] text-on-surface-variant">Token Consumption</p>
              <div className="flex items-end gap-1">
                <span className="text-2xl font-semibold text-primary tabular-nums">6,621</span>
                <span className="mb-1 text-xs text-on-surface-variant">/ 10,000</span>
              </div>
              <p className="mt-2 text-sm text-on-surface-variant">Groq llama-3.3-70b</p>
            </div>
            <div className="rounded-lg border border-outline-variant/10 bg-surface-container-low p-4">
              <p className="mb-1 text-[11px] text-on-surface-variant">Themes Generated</p>
              <div className="flex items-end gap-1">
                <span className="text-2xl font-semibold text-secondary tabular-nums">{kpis.themes}</span>
              </div>
              <p className="mt-2 text-sm text-on-surface-variant">UMAP + HDBSCAN clusters</p>
            </div>
          </div>
          <div className="rounded-lg border border-outline-variant/10 bg-surface-container-lowest p-4 font-mono text-sm">
            <div className="mb-2 flex items-center gap-2 text-xs text-on-surface-variant">
              <Icon name="terminal" className="text-sm" /> Run Log
            </div>
            <div className="custom-scrollbar max-h-40 space-y-1 overflow-y-auto opacity-80">
              {logLines.map((line, i) => (
                <p key={`${line}-${i}`}>
                  <span className="text-primary/70">{line.split(']')[0]}]</span>
                  {line.includes(']') ? line.slice(line.indexOf(']') + 1) : line}
                </p>
              ))}
            </div>
          </div>
        </GlassCard>

        <GlassCard className="border-l-4 border-l-primary p-6 lg:col-span-4">
          <div className="mb-6 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Icon name="deployed_code" className="text-primary" />
            </div>
            <div>
              <h5 className="font-semibold">GitHub Actions</h5>
              <p className="text-[11px] text-on-surface-variant">Automation Workflow</p>
            </div>
          </div>
          <div className="space-y-3 text-sm">
            <div className="flex justify-between border-b border-outline-variant/10 py-2">
              <span className="text-on-surface-variant">Next run</span>
              <span className="font-bold">{settings.cron}</span>
            </div>
            <div className="flex justify-between border-b border-outline-variant/10 py-2">
              <span className="text-on-surface-variant">Last result</span>
              <span className="flex items-center gap-1 font-bold text-primary">
                <Icon name="check_circle" className="text-sm" filled /> Success
              </span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-on-surface-variant">Workflow</span>
              <span className="font-mono text-xs">weekly-pulse.yml</span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => openExternal(delivery.githubActionsUrl)}
            className="mt-4 w-full rounded-lg border border-outline-variant/20 py-2 text-xs font-bold hover:border-primary hover:text-primary"
          >
            Open GitHub Actions
          </button>
        </GlassCard>
      </div>
    </div>
  )
}
