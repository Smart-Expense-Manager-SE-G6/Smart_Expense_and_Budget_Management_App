import Icon from './Icon'

export default function BrandMark({ size = 20 }) {
  return (
    <span className="brand-mark">
      <Icon name="coins" size={size} strokeWidth={2.1} />
    </span>
  )
}

