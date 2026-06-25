import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { ToastProvider } from './lib/ui'
import { AppShell } from './layout/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { PipelinePage } from './pages/PipelinePage'
import { ReviewExplorerPage } from './pages/ReviewExplorerPage'

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="explorer" element={<ReviewExplorerPage />} />
            <Route path="pipeline" element={<PipelinePage />} />
            <Route path="reports" element={<Navigate to="/" replace />} />
            <Route path="delivery" element={<Navigate to="/" replace />} />
            <Route path="settings" element={<Navigate to="/" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
