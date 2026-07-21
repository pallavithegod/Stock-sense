import { useState } from 'react'
import { AppShell } from './layouts/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { PredictionsPage } from './pages/PredictionsPage'
import { PortfolioPage } from './pages/PortfolioPage'
import { StocksPage } from './pages/StocksPage'
import { StatePanel } from './components/StatePanel'
import type { AppPage } from './types/navigation'

function App() {
  const [activePage, setActivePage] = useState<AppPage>('dashboard')

  const page = (() => {
    switch (activePage) {
      case 'dashboard':
        return <DashboardPage />
      case 'stocks':
        return <StocksPage />
      case 'predictions':
        return <PredictionsPage />
      case 'portfolio':
        return <PortfolioPage />
      case 'news':
        return (
          <div className="mx-auto max-w-4xl">
            <StatePanel
              description="News and research migration starts in Phase 5."
              title="News page pending"
            />
          </div>
        )
      case 'research':
        return (
          <div className="mx-auto max-w-4xl">
            <StatePanel
              description="Research cockpit migration starts in Phase 5."
              title="Research page pending"
            />
          </div>
        )
      default:
        return <DashboardPage />
    }
  })()

  return (
    <AppShell activePage={activePage} onPageChange={setActivePage}>
      {page}
    </AppShell>
  )
}

export default App
