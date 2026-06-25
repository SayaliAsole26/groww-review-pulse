/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MCP_URL?: string
  readonly VITE_CURRENT_WEEK?: string
  readonly VITE_GOOGLE_DOC_URL?: string
  readonly VITE_GITHUB_ACTIONS_URL?: string
  readonly VITE_GMAIL_DRAFT_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
