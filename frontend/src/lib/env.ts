import { CURRENT_WEEK as DEFAULT_WEEK, delivery as defaultDelivery, settings as defaultSettings } from '../data/mock'

const DEFAULT_MCP_URL = defaultSettings.mcpUrl

function env(key: string): string | undefined {
  const value = import.meta.env[key]
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

/** Railway hosted Google MCP server (public health check only). */
export const mcpUrl = env('VITE_MCP_URL') ?? DEFAULT_MCP_URL

export const currentWeek = env('VITE_CURRENT_WEEK') ?? DEFAULT_WEEK

export const googleDocUrl = env('VITE_GOOGLE_DOC_URL') ?? defaultDelivery.docUrl

export const githubActionsUrl = env('VITE_GITHUB_ACTIONS_URL') ?? defaultDelivery.githubActionsUrl

export const gmailDraftUrl = env('VITE_GMAIL_DRAFT_URL') ?? defaultDelivery.gmailDraftUrl
