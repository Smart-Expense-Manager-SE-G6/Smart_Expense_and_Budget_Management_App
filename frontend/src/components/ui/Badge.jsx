export default function Badge({ tone, icon, children }) {
  return (
    <span className="badge" data-tone={tone}>
      {icon}
      {children}
    </span>
  )
}

