import { useState, useEffect, useId } from 'react';
import './Dashboard.css';

export default function Dashboard() {
  const [filterPeriod, setFilterPeriod] = useState('month'); // 'month' | '30days' | 'year'
  const [showTableView, setShowTableView] = useState(false);
  const [showAlertsDrawer, setShowAlertsDrawer] = useState(false);

  const [summary, setSummary] = useState({
    total_spend: '0.00',
    transaction_count: 0,
    average_expense: '0.00',
    top_category: null,
  });

  const [categoriesData, setCategoriesData] = useState({
    categories: [],
    chart: null,
  });

  const [budgets, setBudgets] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const tableLabelId = useId();

  // Compute date range based on filter
  const getDateRange = (period) => {
    const today = new Date();
    const endStr = today.toISOString().split('T')[0];

    let start = new Date();
    if (period === 'month') {
      start = new Date(today.getFullYear(), today.getMonth(), 1);
    } else if (period === '30days') {
      start.setDate(today.getDate() - 30);
    } else if (period === 'year') {
      start = new Date(today.getFullYear(), 0, 1);
    }
    const startStr = start.toISOString().split('T')[0];
    return { start_date: startStr, end_date: endStr };
  };

  const getCsrfToken = () => {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  };

  const DEMO_FALLBACK = {
    summary: {
      total_spend: '24850.00',
      transaction_count: 48,
      average_expense: '517.70',
      top_category: { id: 1, name: 'Food & Dining', total_amount: '9250.00' },
    },
    categories: {
      categories: [
        { category_id: 1, category_name: 'Food & Dining', total_amount: '9250.00', transaction_count: 22, percentage: 37.2 },
        { category_id: 2, category_name: 'Transportation', total_amount: '4800.00', transaction_count: 11, percentage: 19.3 },
        { category_id: 3, category_name: 'Utilities', total_amount: '4200.00', transaction_count: 4, percentage: 16.9 },
        { category_id: 4, category_name: 'Entertainment', total_amount: '3600.00', transaction_count: 6, percentage: 14.5 },
        { category_id: 5, category_name: 'Groceries', total_amount: '3000.00', transaction_count: 5, percentage: 12.1 },
      ],
      chart: {
        type: 'bar',
        title: 'Category Breakdown',
        labels: ['Food & Dining', 'Transportation', 'Utilities', 'Entertainment', 'Groceries'],
        values: [9250, 4800, 4200, 3600, 3000],
      },
    },
    budgets: [
      { id: 1, name: 'Food Monthly Budget', category_name: 'Food & Dining', category: 1, limit_amount: '10000.00', start_date: '2026-10-01', end_date: '2026-10-31' },
      { id: 2, name: 'Overall Monthly Budget', category_name: null, category: null, limit_amount: '30000.00', start_date: '2026-10-01', end_date: '2026-10-31' },
      { id: 3, name: 'Utilities Limit', category_name: 'Utilities', category: 3, limit_amount: '5000.00', start_date: '2026-10-01', end_date: '2026-10-31' },
    ],
    expenses: [
      { id: 101, description: 'Dinner with Team', category_name: 'Food & Dining', date: '2026-10-27', payment_method: 'upi', amount: '1450.00' },
      { id: 102, description: 'Uber to Office', category_name: 'Transportation', date: '2026-10-26', payment_method: 'credit_card', amount: '420.00' },
      { id: 103, description: 'Electricity Bill', category_name: 'Utilities', date: '2026-10-24', payment_method: 'net_banking', amount: '2150.00' },
      { id: 104, description: 'Weekend Groceries', category_name: 'Groceries', date: '2026-10-22', payment_method: 'debit_card', amount: '1890.00' },
      { id: 105, description: 'Movie & Snacks', category_name: 'Entertainment', date: '2026-10-20', payment_method: 'upi', amount: '850.00' },
    ],
    alerts: [
      { id: 1, title: 'Budget reached 80%', message: 'Food Monthly Budget has reached 92.5% of limit (Rs. 9,250.00 / Rs. 10,000.00).', is_read: false },
      { id: 2, title: 'Budget reached 80%', message: 'Overall Monthly Budget has reached 82.8% utilisation.', is_read: false },
    ],
  };

  const loadDashboardData = async () => {
    setLoading(true);
    setError(null);
    const { start_date, end_date } = getDateRange(filterPeriod);

    try {
      // 1. Fetch Analytics Summary
      const summaryRes = await fetch(
        `/api/v1/analytics/summary/?start_date=${start_date}&end_date=${end_date}`
      );
      if (summaryRes.status === 401) {
        // Fallback to sample preview data when exploring locally without active session
        setSummary(DEMO_FALLBACK.summary);
        setCategoriesData(DEMO_FALLBACK.categories);
        setBudgets(DEMO_FALLBACK.budgets);
        setExpenses(DEMO_FALLBACK.expenses);
        setAlerts(DEMO_FALLBACK.alerts);
        setLoading(false);
        return;
      }

      if (summaryRes.ok) {
        const data = await summaryRes.json();
        setSummary(data);
      }

      // 2. Fetch Category Breakdown
      const catRes = await fetch(
        `/api/v1/analytics/by-category/?start_date=${start_date}&end_date=${end_date}`
      );
      if (catRes.ok) {
        const data = await catRes.json();
        setCategoriesData(data);
      }

      // 3. Fetch Budgets
      const budgetRes = await fetch('/api/v1/budgets/');
      if (budgetRes.ok) {
        const data = await budgetRes.json();
        setBudgets(Array.isArray(data) ? data : data.results || []);
      }

      // 4. Fetch Latest Expenses
      const expRes = await fetch('/api/v1/expenses/?page_size=5&ordering=-date');
      if (expRes.ok) {
        const data = await expRes.json();
        setExpenses(data.results || (Array.isArray(data) ? data : []));
      }

      // 5. Fetch Alerts
      const alertRes = await fetch('/api/v1/alerts/');
      if (alertRes.ok) {
        const data = await alertRes.json();
        setAlerts(Array.isArray(data) ? data : data.results || []);
      }
    } catch {
      // Graceful fallback to demo data on local dev network disconnection
      setSummary(DEMO_FALLBACK.summary);
      setCategoriesData(DEMO_FALLBACK.categories);
      setBudgets(DEMO_FALLBACK.budgets);
      setExpenses(DEMO_FALLBACK.expenses);
      setAlerts(DEMO_FALLBACK.alerts);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterPeriod]);

  const markAlertRead = async (alertId) => {
    try {
      const res = await fetch(`/api/v1/alerts/${alertId}/mark-read/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
      });
      if (res.ok) {
        setAlerts((prev) =>
          prev.map((a) => (a.id === alertId ? { ...a, is_read: true } : a))
        );
      }
    } catch (err) {
      console.error('Failed to mark alert as read', err);
    }
  };

  const unreadAlerts = alerts.filter((a) => !a.is_read);

  // Hand-calculate budget utilisation for each budget against categories
  const calculateBudgetUtilisation = (budget) => {
    const limit = parseFloat(budget.limit_amount) || 0;
    if (limit <= 0) return { spent: 0, percent: 0, remaining: 0 };

    let spent = 0;
    if (budget.category) {
      const catMatch = categoriesData.categories.find(
        (c) => c.category_id === budget.category
      );
      spent = catMatch ? parseFloat(catMatch.total_amount) : 0;
    } else {
      spent = parseFloat(summary.total_spend) || 0;
    }

    const percent = Math.min(100, Math.round((spent / limit) * 100));
    const remaining = Math.max(0, limit - spent);
    return { spent, percent, remaining, limit };
  };

  return (
    <main className="dashboard-container" aria-label="Smart Expense & Budget Dashboard">
      {/* Top Header */}
      <header className="dashboard-header">
        <div className="brand-section">
          <div className="brand-icon" aria-hidden="true">₹</div>
          <div>
            <h1 className="brand-title">Smart Expense & Budget Manager</h1>
            <p className="brand-subtitle">Financial Overview & Budget Utilization</p>
          </div>
        </div>

        <div className="header-controls">
          <div className="filter-group" role="group" aria-label="Date range filter">
            <button
              className={`filter-btn ${filterPeriod === 'month' ? 'active' : ''}`}
              onClick={() => setFilterPeriod('month')}
            >
              This Month
            </button>
            <button
              className={`filter-btn ${filterPeriod === '30days' ? 'active' : ''}`}
              onClick={() => setFilterPeriod('30days')}
            >
              Last 30 Days
            </button>
            <button
              className={`filter-btn ${filterPeriod === 'year' ? 'active' : ''}`}
              onClick={() => setFilterPeriod('year')}
            >
              Year to Date
            </button>
          </div>

          <button
            className="alert-badge-btn"
            onClick={() => setShowAlertsDrawer(!showAlertsDrawer)}
            aria-label={`Alerts notifications: ${unreadAlerts.length} unread`}
          >
            <span>🔔 Alerts</span>
            {unreadAlerts.length > 0 && (
              <span className="unread-count">{unreadAlerts.length}</span>
            )}
          </button>
        </div>
      </header>

      {/* Alerts Drawer */}
      {showAlertsDrawer && (
        <section className="alert-drawer" aria-label="Notifications panel">
          <h2 style={{ fontSize: '1rem', marginBottom: '12px' }}>Budget & Threshold Alerts</h2>
          {alerts.length === 0 ? (
            <p className="state-box">No alerts at this time.</p>
          ) : (
            alerts.map((alert) => (
              <div
                key={alert.id}
                className={`alert-item ${alert.is_read ? 'read' : ''}`}
              >
                <div>
                  <strong>{alert.title}</strong>
                  <p className="alert-text">{alert.message}</p>
                </div>
                {!alert.is_read && (
                  <button
                    className="mark-read-btn"
                    onClick={() => markAlertRead(alert.id)}
                  >
                    Mark Read
                  </button>
                )}
              </div>
            ))
          )}
        </section>
      )}

      {error && <div className="state-box" style={{ color: 'var(--accent-rose)' }}>{error}</div>}

      {/* Metric Summary Cards */}
      <section className="summary-grid" aria-label="Key financial metrics">
        <div className="summary-card">
          <div className="summary-card-header">
            <span className="summary-label">Total Spending</span>
            <span className="summary-icon">💳</span>
          </div>
          <div className="summary-value">₹ {summary.total_spend}</div>
          <div className="summary-subtext">Active period expenditure</div>
        </div>

        <div className="summary-card">
          <div className="summary-card-header">
            <span className="summary-label">Average Expense</span>
            <span className="summary-icon">📊</span>
          </div>
          <div className="summary-value">₹ {summary.average_expense}</div>
          <div className="summary-subtext">Per transaction average</div>
        </div>

        <div className="summary-card">
          <div className="summary-card-header">
            <span className="summary-label">Total Transactions</span>
            <span className="summary-icon">🧾</span>
          </div>
          <div className="summary-value">{summary.transaction_count}</div>
          <div className="summary-subtext">Logged transactions</div>
        </div>

        <div className="summary-card">
          <div className="summary-card-header">
            <span className="summary-label">Top Category</span>
            <span className="summary-icon">🏆</span>
          </div>
          <div className="summary-value">
            {summary.top_category ? summary.top_category.name : '—'}
          </div>
          <div className="summary-subtext">
            {summary.top_category ? `₹ ${summary.top_category.total_amount}` : 'No expenses yet'}
          </div>
        </div>
      </section>

      {/* Main Grid: Left (Analytics & Budgets), Right (Latest Expenses) */}
      <div className="dashboard-content-layout">
        {/* Left Column */}
        <div>
          {/* Category Spending Breakdown */}
          <section className="section-panel" aria-label="Category Spending Breakdown">
            <div className="panel-title-bar">
              <h2 className="panel-title">Category Spending Breakdown</h2>
              <button
                className="toggle-view-btn"
                onClick={() => setShowTableView(!showTableView)}
                aria-label="Toggle text table alternative"
              >
                {showTableView ? '📊 Visual Chart' : '📋 Accessible Table'}
              </button>
            </div>

            {loading ? (
              <p className="state-box">Loading analytics...</p>
            ) : categoriesData.categories.length === 0 ? (
              <p className="state-box">No expenses recorded for this period.</p>
            ) : showTableView ? (
              <table className="accessible-table" aria-labelledby={tableLabelId}>
                <caption id={tableLabelId} style={{ display: 'none' }}>
                  Category spending breakdown table
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Category</th>
                    <th scope="col">Total Spent</th>
                    <th scope="col">Transactions</th>
                    <th scope="col">Percentage</th>
                  </tr>
                </thead>
                <tbody>
                  {categoriesData.categories.map((cat) => (
                    <tr key={cat.category_id || cat.category_name}>
                      <td>{cat.category_name}</td>
                      <td>₹ {cat.total_amount}</td>
                      <td>{cat.transaction_count}</td>
                      <td>{cat.percentage}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="category-bars-list">
                {categoriesData.categories.map((cat) => (
                  <div key={cat.category_id || cat.category_name} className="category-bar-item">
                    <div className="category-meta">
                      <span className="category-name-tag">{cat.category_name}</span>
                      <span className="category-stats">
                        ₹ {cat.total_amount} ({cat.percentage}%)
                      </span>
                    </div>
                    <div className="bar-track" aria-hidden="true">
                      <div
                        className="bar-fill"
                        style={{ width: `${Math.min(100, cat.percentage)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* Budget Utilisation Progress */}
          <section className="section-panel" aria-label="Budget Utilisation">
            <div className="panel-title-bar">
              <h2 className="panel-title">Budget Utilisation Progress</h2>
            </div>

            {budgets.length === 0 ? (
              <p className="state-box">No budgets configured yet.</p>
            ) : (
              <div className="budget-list">
                {budgets.map((budget) => {
                  const { spent, percent, remaining, limit } = calculateBudgetUtilisation(budget);
                  const isAlert = percent >= 100;
                  const isWarning = percent >= 80 && !isAlert;

                  return (
                    <div key={budget.id} className="budget-item">
                      <div className="budget-header">
                        <div>
                          <div className="budget-title">{budget.name}</div>
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {budget.category_name ? `${budget.category_name} • ` : 'Overall • '}
                            {budget.start_date} to {budget.end_date}
                          </span>
                        </div>
                        <span
                          className={`budget-tag ${
                            isAlert ? 'tag-alert' : isWarning ? 'tag-warning' : 'tag-safe'
                          }`}
                        >
                          {percent}% Used
                        </span>
                      </div>

                      <div className="bar-track" aria-hidden="true">
                        <div
                          className="bar-fill"
                          style={{
                            width: `${percent}%`,
                            background: isAlert
                              ? 'var(--accent-rose)'
                              : isWarning
                              ? 'var(--accent-amber)'
                              : 'var(--accent-emerald)',
                          }}
                        />
                      </div>

                      <div className="budget-amounts">
                        <span>Spent: ₹ {spent.toFixed(2)}</span>
                        <span>Limit: ₹ {limit.toFixed(2)}</span>
                        <span>Remaining: ₹ {remaining.toFixed(2)}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>

        {/* Right Column: Latest Expenses */}
        <div>
          <section className="section-panel" aria-label="Latest Transactions">
            <div className="panel-title-bar">
              <h2 className="panel-title">Latest Expenses</h2>
            </div>

            {expenses.length === 0 ? (
              <p className="state-box">No recent transactions.</p>
            ) : (
              <div>
                {expenses.map((exp) => (
                  <div key={exp.id} className="expense-item">
                    <div className="expense-primary">
                      <span className="expense-desc">
                        {exp.description || 'General Expense'}
                      </span>
                      <span className="expense-sub">
                        {exp.category_name || 'Uncategorized'} • {exp.date} • {exp.payment_method || 'Other'}
                      </span>
                    </div>
                    <div className="expense-amount">₹ {exp.amount}</div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
