import Badge from '../../components/ui/Badge'
import Button from '../../components/ui/Button'
import Icon from '../../components/ui/Icon'
import ProgressBar from '../../components/ui/ProgressBar'
import { formatCurrency, formatDate, toneForPercent } from '../../lib/format'

const TONE_LABEL = { success: 'On track', warning: 'Nearing limit', danger: 'Limit exceeded' }

export default function BudgetCard({ budget, onEdit, onDelete, muted = false }) {
  const { util } = budget
  const tone = toneForPercent(util.percent)
  const over = util.remaining < 0

  return (
    <article className="card budget-card" data-muted={muted}>
      <header className="budget-card-head">
        <div>
          <h3>{budget.name}</h3>
          <p className="cell-sub">
            <Icon name="calendar" size={13} style={{ display: 'inline', verticalAlign: '-2px', marginRight: 4 }} />
            {formatDate(budget.start_date, { day: 'numeric', month: 'short' })} – {formatDate(budget.end_date)}
          </p>
        </div>
        <span className="row-actions">
          <Button variant="ghost" size="sm" iconOnly icon="pencil" aria-label={`Edit ${budget.name}`} onClick={() => onEdit(budget)} />
          <Button variant="ghost" size="sm" iconOnly icon="trash" aria-label={`Delete ${budget.name}`} onClick={() => onDelete(budget)} />
        </span>
      </header>

      <div className="budget-card-tags">
        <Badge tone="primary">{budget.category_name ?? 'All categories'}</Badge>
        <Badge>{budget.period === 'weekly' ? 'Weekly' : 'Monthly'}</Badge>
        {budget.rollover_mode === 'rollover' && <Badge tone="info">Rollover</Badge>}
      </div>

      <div className="budget-card-figure">
        <strong className="budget-percent" data-tone={tone}>
          {Math.round(util.percent)}%
        </strong>
        <Badge tone={tone}>{TONE_LABEL[tone]}</Badge>
      </div>

      <ProgressBar percent={util.percent} label={`${budget.name} utilisation`} />

      <dl className="mini-stats">
        <div>
          <dt>Spent</dt>
          <dd>{formatCurrency(util.spent, { whole: true })}</dd>
        </div>
        <div>
          <dt>Limit</dt>
          <dd>{formatCurrency(util.limit, { whole: true })}</dd>
        </div>
        <div>
          <dt>{over ? 'Over by' : 'Remaining'}</dt>
          <dd className={over ? 'amount-negative' : undefined}>{formatCurrency(Math.abs(util.remaining), { whole: true })}</dd>
        </div>
      </dl>
    </article>
  )
}

