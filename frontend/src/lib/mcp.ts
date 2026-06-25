export type McpHealthState =
  | { status: 'loading' }
  | { status: 'ok'; message: string; checkedAt: string }
  | { status: 'error'; message: string; checkedAt: string }

type McpHealthResponse = {
  status?: string
  message?: string
}

/** Same-origin proxy avoids CORS (see vite.config + vercel.json). */
const HEALTH_PATH = '/api/mcp-health'

export async function fetchMcpHealth(): Promise<McpHealthState> {
  const checkedAt = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  try {
    const response = await fetch(HEALTH_PATH, {
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(10_000),
    })

    if (!response.ok) {
      return {
        status: 'error',
        message: `HTTP ${response.status}`,
        checkedAt,
      }
    }

    const data = (await response.json()) as McpHealthResponse
    if (data.status === 'ok') {
      return {
        status: 'ok',
        message: data.message ?? 'Google MCP Server is running',
        checkedAt,
      }
    }

    return {
      status: 'error',
      message: data.message ?? `Unexpected status: ${data.status ?? 'unknown'}`,
      checkedAt,
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Could not reach MCP server'
    return { status: 'error', message, checkedAt }
  }
}
