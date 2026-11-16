import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import { GuestOnly, RequireAuth } from './components/RouteGuards'
import AlertsPage from './pages/AlertsPage'
import BudgetsPage from './pages/BudgetsPage'
import CategoriesPage from './pages/CategoriesPage'
import DashboardPage from './pages/DashboardPage'
import ExpensesPage from './pages/ExpensesPage'
import ExpenseImportPage from './pages/ExpenseImportPage'
import LoginPage from './pages/LoginPage'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'
import ReportsPage from './pages/ReportsPage'
import RecurringRulesPage from './pages/RecurringRulesPage'

export default function App() {
  return (
    <Routes>
      <Route element={<GuestOnly />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>
      <Route element={<RequireAuth />}>
        <Route element={<AppShell />}>
          <Route index element={<DashboardPage />} />
          <Route path="/expenses" element={<ExpensesPage />} />
          <Route path="/expenses/import" element={<ExpenseImportPage />} />
          <Route path="/recurring" element={<RecurringRulesPage />} />
          <Route path="/budgets" element={<BudgetsPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
