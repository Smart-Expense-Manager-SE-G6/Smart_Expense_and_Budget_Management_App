import assert from 'node:assert/strict'
import test from 'node:test'

import { statusLabel, statusTone } from '../src/features/monitoring/status.js'

test('monitoring statuses map to readable labels and severity tones', () => {
  assert.equal(statusLabel('healthy'), 'Healthy')
  assert.equal(statusTone('healthy'), 'success')
  assert.equal(statusLabel('failed'), 'Failed')
  assert.equal(statusTone('failed'), 'danger')
  assert.equal(statusLabel('stale'), 'Stale')
  assert.equal(statusTone('stale'), 'warning')
})

test('missing or unrecognized statuses remain explicitly unknown', () => {
  assert.equal(statusLabel(undefined), 'Unknown')
  assert.equal(statusLabel('invented'), 'Unknown')
  assert.equal(statusTone('unknown'), 'info')
})
