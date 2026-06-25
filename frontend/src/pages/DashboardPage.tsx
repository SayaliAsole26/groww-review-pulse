import { useState } from 'react'
import { GlassCard } from '../components/GlassCard'
import { Icon } from '../components/Icon'
import {
  delivery,
  kpis,
  ratingDistribution,
  themes,
  weeklyTrend,
} from '../data/mock'
import { openExternal, useToast } from '../lib/ui'

const accentBar: Record<string, string> = {
  error: 'bg-error',
  tertiary: 'bg-tertiary',
  primary: 'bg-primary',
}

export function DashboardPage() {
  const { showToast } = useToast()
  const [actionsDone, setActionsDone] = useState<Record<number, boolean>>({ 0: true })

  const toggleAction = (index: number) => {
    setActionsDone((prev) => ({ ...prev, [index]: !prev[index] }))
    if (index === 0) {
      openExternal(delivery.gmailDraftUrl)
      showToast('Opening Gmail draft')
    } else {
      showToast(actionsDone[index] ? 'Action marked pending' : 'Action marked complete')
    }
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <GlassCard className="flex flex-col justify-between p-4">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium tracking-wide text-on-surface-variant">Reviews Analyzed</span>
            <Icon name="data_exploration" className="text-primary" />
          </div>
          <div className="mt-4">
            <div className="text-3xl font-semibold tabular-nums">{kpis.reviewsAnalyzed.toLocaleString()}</div>
            <div className="mt-1 text-xs text-on-surface-variant">
              Filtered from {kpis.rawReviews.toLocaleString()} raw entries
            </div>
          </div>
        </GlassCard>

        <GlassCard className="flex flex-col justify-between p-4">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium tracking-wide text-on-surface-variant">Key Themes</span>
            <Icon name="category" className="text-tertiary" />
          </div>
          <div className="mt-4">
            <div className="text-3xl font-semibold">{kpis.themes}</div>
            <div className="mt-1 text-xs text-on-surface-variant">Top themes in email teaser</div>
          </div>
        </GlassCard>

        <GlassCard className="flex flex-col justify-between p-4">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium tracking-wide text-on-surface-variant">Avg Rating</span>
            <Icon name="star" className="text-secondary" />
          </div>
          <div className="mt-4 flex items-end gap-1">
            <div className="text-3xl font-semibold tabular-nums">{kpis.avgRating}</div>
            <div className="mb-1 flex items-center text-xs text-error">
              <Icon name="trending_down" className="text-sm" /> {Math.abs(kpis.ratingDelta)}
            </div>
          </div>
          <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-surface-container">
            <div className="h-full w-[64%] bg-secondary" />
          </div>
        </GlassCard>

        <GlassCard className="flex flex-col justify-between border-primary/20 p-4">
          <div className="flex items-start justify-between">
            <span className="text-xs font-medium tracking-wide text-on-surface-variant">Analysis Pipeline</span>
            <div className="flex items-center gap-1">
              <span className="text-xs font-bold text-primary">Live</span>
              <div className="h-2 w-2 rounded-full bg-primary pulse-indicator" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-xl font-semibold text-primary">{kpis.pipelineStatus}</div>
            <div className="mt-1 text-xs text-on-surface-variant">Last run: {kpis.lastRun}</div>
          </div>
        </GlassCard>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="space-y-4 lg:col-span-7">
          <div className="flex flex-wrap items-end justify-between gap-2 px-1">
            <h3 className="text-xl font-semibold">Top Themes This Week</h3>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  openExternal(delivery.docUrl)
                  showToast('Opening Google Doc report')
                }}
                className="flex items-center gap-1 rounded-lg border border-outline-variant/20 px-3 py-1.5 text-xs font-bold text-on-surface hover:border-primary hover:text-primary"
              >
                <Icon name="description" className="text-sm" /> Full Report
              </button>
              <button
                type="button"
                onClick={() => {
                  openExternal(delivery.gmailDraftUrl)
                  showToast('Opening Gmail draft')
                }}
                className="flex items-center gap-1 rounded-lg bg-primary px-3 py-1.5 text-xs font-bold text-on-primary hover:brightness-110"
              >
                <Icon name="mail" className="text-sm" /> Email Draft
              </button>
            </div>
          </div>

          {themes.map((theme) => (
            <GlassCard key={theme.rank} className="relative overflow-hidden p-6">
              <div className="absolute right-0 top-0 p-4">
                <div className="rounded bg-surface-container-highest px-2 py-1 text-xs font-bold">#{theme.rank}</div>
              </div>
              <div className="flex gap-6">
                <div className={`w-1 rounded-full ${accentBar[theme.accent]}`} />
                <div className="flex-1">
                  <h4 className="text-lg font-bold">{theme.title}</h4>
                  <p className="mt-1 text-xs text-on-surface-variant">
                    Volume: <span className="font-bold text-on-surface">{theme.reviewCount} reviews</span> ({theme.pct}% of total)
                  </p>
                  <blockquote className="mt-4 rounded border-l-2 border-outline-variant/30 bg-surface-container-lowest/50 p-4 text-sm italic text-on-surface-variant">
                    &ldquo;{theme.quote}&rdquo;
                  </blockquote>
                  <div className="mt-4 flex flex-wrap gap-2">
                    {theme.tags.map((tag, i) => (
                      <span
                        key={tag}
                        className={`rounded-full px-2 py-1 text-[11px] font-bold ${
                          i === 0
                            ? theme.accent === 'error'
                              ? 'bg-error/10 text-error'
                              : theme.accent === 'tertiary'
                                ? 'bg-tertiary/10 text-tertiary'
                                : 'bg-primary/10 text-primary'
                            : 'bg-surface-container-high text-on-surface'
                        }`}
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                  <div className="mt-4 flex justify-end">
                    <button
                      type="button"
                      onClick={() => showToast(`${theme.action} — logged for theme #${theme.rank}`)}
                      className={`rounded-lg px-4 py-2 text-xs font-bold transition-opacity hover:opacity-90 ${
                        theme.rank === 1
                          ? 'bg-primary text-on-primary'
                          : 'border border-outline-variant/20 bg-surface-container-high text-on-surface'
                      }`}
                    >
                      {theme.action}
                    </button>
                  </div>
                </div>
              </div>
            </GlassCard>
          ))}
        </div>

        <div className="space-y-6 lg:col-span-5">
          <GlassCard className="p-6">
            <h3 className="mb-6 text-xs font-bold uppercase tracking-wider text-on-surface-variant">
              Rating Distribution
            </h3>
            <div className="flex items-center gap-8">
              <div className="relative h-32 w-32 shrink-0">
                <svg className="h-full w-full -rotate-90" viewBox="0 0 36 36">
                  <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" className="text-surface-container-highest" />
                  <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" strokeDasharray="35 100" className="text-error" />
                  <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" strokeDasharray="40 100" strokeDashoffset="-35" className="text-tertiary" />
                  <circle cx="18" cy="18" r="16" fill="none" stroke="currentColor" strokeWidth="3" strokeDasharray="25 100" strokeDashoffset="-75" className="text-primary" />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-bold tabular-nums">{kpis.avgRating}</span>
                  <span className="text-xs text-on-surface-variant">Global</span>
                </div>
              </div>
              <div className="flex-1 space-y-2">
                {ratingDistribution.map((row) => (
                  <div key={row.label} className="flex items-center gap-2 text-sm">
                    <span className={`h-2 w-2 rounded-full ${row.color}`} />
                    <span className="flex-1 text-on-surface-variant">{row.label}</span>
                    <span className="font-bold tabular-nums">{row.pct}%</span>
                  </div>
                ))}
              </div>
            </div>
          </GlassCard>

          <GlassCard className="flex h-64 flex-col p-6">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-on-surface-variant">12-Week Volume Trend</h3>
              <span className="text-xs font-bold text-primary">+12% vs LY</span>
            </div>
            <div className="relative flex flex-1 items-end justify-between gap-1 px-1">
              {weeklyTrend.map((h, i) => (
                <button
                  key={i}
                  type="button"
                  title={`Week ${13 + i}`}
                  onClick={() => showToast(`Week ${13 + i}: ${Math.round((h / 100) * kpis.reviewsAnalyzed)} reviews`)}
                  className={`w-full max-w-[24px] rounded-t transition-all hover:opacity-80 ${
                    i === weeklyTrend.length - 1 ? 'bg-primary shadow-[0_0_12px_rgba(68,237,183,0.3)]' : 'bg-primary-container/20'
                  }`}
                  style={{ height: `${h}%` }}
                />
              ))}
            </div>
            <div className="mt-2 flex justify-between px-1 text-xs text-on-surface-variant">
              <span>W13</span>
              <span>W19</span>
              <span className="font-bold text-primary">W25</span>
            </div>
          </GlassCard>

          <div className="rounded-xl border border-outline-variant/10 bg-surface-container-high/40 p-4">
            <h4 className="mb-3 text-xs font-bold">Immediate Actions</h4>
            <ul className="space-y-2">
              {[
                'Draft response to Reliability issues',
                'Sync with UX Team on Navigation revamp',
              ].map((label, index) => (
                <li key={label}>
                  <button
                    type="button"
                    onClick={() => toggleAction(index)}
                    className="flex w-full cursor-pointer items-center gap-2 text-left text-sm hover:text-primary"
                  >
                    <Icon
                      name={actionsDone[index] ? 'task_alt' : 'radio_button_unchecked'}
                      className={`text-sm ${actionsDone[index] ? 'text-primary' : 'text-on-surface-variant'}`}
                      filled={actionsDone[index]}
                    />
                    <span className={actionsDone[index] ? 'line-through opacity-70' : ''}>{label}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
