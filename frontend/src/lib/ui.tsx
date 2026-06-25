import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'

type Toast = { id: number; message: string }

type ToastContextValue = {
  showToast: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const showToast = useCallback((message: string) => {
    const id = Date.now()
    setToasts((prev) => [...prev, { id, message }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 3200)
  }, [])

  const value = useMemo(() => ({ showToast }), [showToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-20 left-1/2 z-[100] flex w-full max-w-md -translate-x-1/2 flex-col gap-2 px-4 md:bottom-6">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="rounded-lg border border-primary/30 bg-surface-container-high px-4 py-3 text-center text-sm font-medium text-on-surface shadow-lg"
          >
            {toast.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used within ToastProvider')
  return ctx
}

export function openExternal(url: string) {
  window.open(url, '_blank', 'noopener,noreferrer')
}
