import { NavLink, Outlet } from 'react-router-dom'
import { Icon } from '../components/Icon'
import { currentWeek, githubActionsUrl, gmailDraftUrl, googleDocUrl } from '../lib/env'
import { openExternal, useToast } from '../lib/ui'

const navItems = [
  { to: '/', icon: 'dashboard', label: 'Dashboard' },
  { to: '/explorer', icon: 'explore', label: 'Review Explorer' },
  { to: '/pipeline', icon: 'account_tree', label: 'Pipeline' },
]

function DeliveryLinks({ className = '' }: { className?: string }) {
  return (
    <div className={`flex flex-wrap gap-3 ${className}`}>
      <button
        type="button"
        onClick={() => openExternal(googleDocUrl)}
        className="flex items-center gap-1 text-xs text-on-surface-variant transition-colors hover:text-primary"
      >
        <Icon name="description" className="text-sm" /> Google Docs
      </button>
      <button
        type="button"
        onClick={() => openExternal(gmailDraftUrl)}
        className="flex items-center gap-1 text-xs text-on-surface-variant transition-colors hover:text-primary"
      >
        <Icon name="mail" className="text-sm" /> Gmail Draft
      </button>
      <button
        type="button"
        onClick={() => openExternal(githubActionsUrl)}
        className="flex items-center gap-1 text-xs text-on-surface-variant transition-colors hover:text-primary"
      >
        <Icon name="settings_input_component" className="text-sm" /> GitHub Actions
      </button>
    </div>
  )
}

export function AppShell() {
  const { showToast } = useToast()

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <aside className="fixed left-0 top-0 z-50 hidden h-full w-64 flex-col border-r border-outline-variant/10 bg-surface/60 p-4 backdrop-blur-xl md:flex">
        <div className="mb-8 flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded bg-primary">
            <Icon name="insights" className="text-on-primary text-xl" filled />
          </div>
          <div>
            <h1 className="text-xl font-bold text-primary">Pulse</h1>
            <p className="text-[11px] font-semibold text-on-surface-variant">Premium Fintech</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg p-2 transition-all duration-150 active:scale-95 ${
                  isActive
                    ? 'border-r-2 border-primary bg-surface-container-highest/30 font-bold text-primary'
                    : 'text-on-surface-variant hover:bg-surface-container-highest/50 hover:text-on-surface'
                }`
              }
            >
              <Icon name={item.icon} />
              <span className="text-xs font-medium tracking-wide">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="mt-auto rounded-lg bg-surface-container-low p-2">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-full border border-outline-variant/20 bg-surface-container-high">
              <Icon name="person" className="text-on-surface-variant" />
            </div>
            <div className="overflow-hidden">
              <p className="truncate text-xs font-bold">Analyst Pulse</p>
              <p className="truncate text-[11px] text-on-surface-variant">Lead Researcher</p>
            </div>
          </div>
        </div>
      </aside>

      <main className="relative flex min-h-screen flex-1 flex-col md:ml-64">
        <header className="sticky top-0 z-40 flex items-center justify-between border-b border-outline-variant/10 bg-surface/60 px-4 py-4 backdrop-blur-xl md:px-6">
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold text-primary md:hidden">Pulse</span>
            <h2 className="hidden text-lg font-semibold md:block">Weekly Review Pulse</h2>
            <span className="rounded-lg border border-primary/20 bg-surface-container-high px-2 py-0.5 text-xs font-bold text-primary">
              {currentWeek}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-1 rounded-full border border-outline-variant/10 bg-surface-container-low px-3 py-1 sm:flex">
              <button
                type="button"
                onClick={() => showToast('Previous week backfill coming soon')}
                className="hover:text-primary"
              >
                <Icon name="chevron_left" className="text-sm" />
              </button>
              <span className="text-xs font-bold text-on-surface-variant">Prev Week</span>
              <button
                type="button"
                onClick={() => showToast('Next week not available yet')}
                className="hover:text-primary"
              >
                <Icon name="chevron_right" className="text-sm" />
              </button>
            </div>
            <button
              type="button"
              onClick={() => showToast('No new notifications')}
              className="relative flex h-10 w-10 items-center justify-center hover:text-primary"
            >
              <Icon name="notifications" />
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-error" />
            </button>
          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 pb-28 md:p-6 md:pb-6">
          <Outlet />
        </div>

        <footer className="fixed bottom-16 left-0 right-0 z-40 border-t border-outline-variant/10 bg-surface-container-low/95 px-4 py-2 backdrop-blur-xl md:bottom-0 md:left-64">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1">
                <Icon name="check_circle" className="text-sm text-primary" />
                <span className="text-xs font-bold">Weekly Report Delivered</span>
              </div>
              <div className="hidden h-4 w-px bg-outline-variant/30 md:block" />
              <DeliveryLinks />
            </div>
            <span className="hidden text-xs text-on-surface-variant md:inline">
              © 2026 Groww Weekly Review Pulse
            </span>
          </div>
        </footer>
      </main>

      <nav className="fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-outline-variant/10 glass-card md:hidden">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `flex flex-col items-center gap-0.5 ${isActive ? 'text-primary' : 'text-on-surface-variant'}`
            }
          >
            {({ isActive }) => (
              <>
                <Icon name={item.icon} className="text-xl" filled={isActive} />
                <span className="text-[11px] font-semibold">{item.label.split(' ')[0]}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
