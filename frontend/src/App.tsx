import { ErrorBoundary } from './components/ErrorBoundary'
import { AppShell } from './layouts/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { NewsPage } from './pages/NewsPage'
import { PredictionsPage } from './pages/PredictionsPage'
import { PortfolioPage } from './pages/PortfolioPage'
import { ResearchPage } from './pages/ResearchPage'
import { StocksPage } from './pages/StocksPage'
import { useAppRouter } from './router/useAppRouter'

function App() {
  const { activePage, navigate } = useAppRouter()

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
    <AppShell activePage={activePage} onPageChange={navigate}>
      <ErrorBoundary key={activePage}>{page}</ErrorBoundary>
    </AppShell>
  )
}

export default App
