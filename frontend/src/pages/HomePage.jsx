import { useAuth } from '../auth/context'

// Placeholder until the dashboard (task 16) lands.
export default function HomePage() {
  const { user } = useAuth()
  return (
    <section className="card">
      <h1>Welcome{user.first_name ? `, ${user.first_name}` : ''}</h1>
      <p className="muted">Your dashboard will appear here.</p>
    </section>
  )
}
