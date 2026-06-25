export const CURRENT_WEEK = '2026-W25'

export const kpis = {
  reviewsAnalyzed: 1669,
  rawReviews: 9743,
  themes: 3,
  avgRating: 3.2,
  ratingDelta: -0.4,
  pipelineStatus: 'Completed' as const,
  lastRun: '14 mins ago',
}

export const themes = [
  {
    rank: 1,
    title: 'Security and Reliability Concerns',
    reviewCount: 412,
    pct: 24.7,
    quote:
      'Transaction failed three times during peak hours. Customer support was unreachable for 40 minutes. Highly unreliable for serious investing.',
    accent: 'error' as const,
    tags: ['Critical Fix', 'Latency', 'Support Delay'],
    action: 'Assign to SRE',
  },
  {
    rank: 2,
    title: 'Poor User Experience and Technical Issues',
    reviewCount: 389,
    pct: 23.3,
    quote:
      "The new dashboard is cluttered. Finding the 'withdraw' button took me 5 minutes. Why change something that worked perfectly?",
    accent: 'tertiary' as const,
    tags: ['UI Friction', 'Navigation', 'Visual Clutter'],
    action: 'Log UX Issue',
  },
  {
    rank: 3,
    title: 'User Experience and Feature Enhancements',
    reviewCount: 298,
    pct: 17.9,
    quote:
      'Good for beginners but lacks detailed analysis tools. Would love better portfolio insights.',
    accent: 'primary' as const,
    tags: ['Feature Request', 'Analytics'],
    action: 'Add to Roadmap',
  },
]

export const ratingDistribution = [
  { label: '5 & 4 Stars', pct: 25, color: 'bg-primary' },
  { label: '3 Stars', pct: 40, color: 'bg-tertiary' },
  { label: '1 & 2 Stars', pct: 35, color: 'bg-error' },
]

export const weeklyTrend = [40, 45, 38, 55, 60, 52, 48, 70, 85, 80, 92, 100]

export const historicalRuns = [
  {
    week: '2026-W25',
    date: 'Jun 22, 2026',
    period: '15 Jun - 21 Jun',
    reviews: 1669,
    themes: 5,
    status: 'Completed' as const,
  },
  {
    week: '2026-W24',
    date: 'Jun 15, 2026',
    period: '08 Jun - 14 Jun',
    reviews: 1422,
    themes: 4,
    status: 'Completed' as const,
  },
  {
    week: '2026-W23',
    date: 'Jun 08, 2026',
    period: '01 Jun - 07 Jun',
    reviews: 1890,
    themes: 6,
    status: 'Completed' as const,
  },
  {
    week: '2026-W22',
    date: 'Jun 01, 2026',
    period: '25 May - 31 May',
    reviews: 0,
    themes: 0,
    status: 'Failed' as const,
  },
  {
    week: '2026-W21',
    date: 'May 25, 2026',
    period: '18 May - 24 May',
    reviews: 2105,
    themes: 7,
    status: 'Completed' as const,
  },
]

export const sampleReviews = [
  {
    id: '1',
    rating: 1,
    text: 'All apps have low charges but Groww More Charges You also charge less Please',
    version: '18.11.1',
    date: '21 Jun 2026',
  },
  {
    id: '2',
    rating: 1,
    text: "worst update in 17.91.1 version as it's UI is not like previous one.. plz improve app speed..",
    version: '18.11.1',
    date: '21 Jun 2026',
  },
  {
    id: '3',
    rating: 5,
    text: 'easy to use for a new Bird so just do it',
    version: '18.7.1',
    date: '21 Jun 2026',
  },
  {
    id: '4',
    rating: 3,
    text: 'Avoid purchasing Bonds from Groww aap, no Update, No response, No Details',
    version: '18.11.1',
    date: '21 Jun 2026',
  },
  {
    id: '5',
    rating: 4,
    text: 'good experience app I think I am huge investment of mutual fund vry good app',
    version: '18.11.1',
    date: '21 Jun 2026',
  },
]

export const pipelineStages = [
  { id: 'ingest', label: 'Ingest', status: 'done' as const },
  { id: 'analyze', label: 'Analyze', status: 'done' as const },
  { id: 'render', label: 'Render', status: 'done' as const },
  { id: 'docs', label: 'Docs', status: 'done' as const },
  { id: 'email', label: 'Email', status: 'done' as const },
]

export const delivery = {
  docTitle: 'Weekly Review Pulse — Groww',
  docUrl:
    'https://docs.google.com/document/d/1dIsJ3Va8d0Aiq_czZ3M3tvxF408-TKwLB99yOuaj8dg/edit',
  contentHash: 'fe3455b2fad5700a6aba872c69dc1e22ff59274ef4f1f01045f2dac7ff6d89aa',
  emailSubject: 'Groww Weekly Review Pulse — Week 2026-W25',
  recipients: ['asolesayali@gmail.com'],
  mode: 'draft' as const,
  draftId: 'r345793903828727181',
  messageId: '19efbd298731b561',
  /** Opens Gmail drafts folder (stakeholder teaser draft). */
  gmailDraftUrl: 'https://mail.google.com/mail/u/0/#drafts',
  githubActionsUrl: 'https://github.com/SayaliAsole26/groww-review-pulse/actions',
  runId: 'groww:2026-W25',
}

export const settings = {
  packageId: 'com.nextbillion.groww',
  reviewWindow: '12-week rolling window',
  timezone: 'Asia/Kolkata (IST)',
  embeddingModel: 'BAAI/bge-small-en-v1.5',
  llmModel: 'llama-3.3-70b-versatile',
  mcpUrl: 'https://mcp-server-production-725c.up.railway.app',
  cron: 'Mon 09:00 IST',
  environment: 'Production',
}
