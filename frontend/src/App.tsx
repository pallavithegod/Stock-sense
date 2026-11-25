import { ErrorBoundary } from './components/ErrorBoundary'
import { AppShell } from './layouts/AppShell'
import { DashboardPage } from './pages/DashboardPage'
import { NewsPage } from './pages/NewsPage'
import { PredictionsPage } from './pages/PredictionsPage'
import { PortfolioPage } from './pages/PortfolioPage'
import { ResearchPage } from './pages/ResearchPage'
import { StocksPage } from './pages/StocksPage'
import { useAppRouter } from './router/useAppRouter'
import { AuthPage } from './auth/AuthPage'
import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/useAuth'

function AppContent() {
  const { activePage, navigate } = useAppRouter()
  const { loading, recovery, user } = useAuth()

  const page = (() => {
    switch (activePage) {
      case 'dashboard':
        return <DashboardPage />
      case 'stocks':
        return <StocksPage />
      case 'predictions':
        return <PredictionsPage />
      case 'portfolio':
        return loading ? (
          <p className="text-sm text-slate-400">Checking your sign-in session...</p>
        ) : recovery ? (
          <AuthPage />
        ) : user ? (
          <PortfolioPage key={user.id} />
        ) : (
          <AuthPage />
        )
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

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}

export default App
