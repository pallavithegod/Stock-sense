import { useState } from 'react'
import { AppShell } from './layouts/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { NewsPage } from './pages/NewsPage'
import { PredictionsPage } from './pages/PredictionsPage'
import { PortfolioPage } from './pages/PortfolioPage'
import { ResearchPage } from './pages/ResearchPage'
import { StocksPage } from './pages/StocksPage'
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
        return <NewsPage />
      case 'research':
        return <ResearchPage />
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
