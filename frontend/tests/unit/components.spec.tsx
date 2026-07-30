import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, test, vi } from 'vitest'

import { IconButton } from '../../src/components/IconButton'
import { MetricCard } from '../../src/components/MetricCard'
import { StatePanel } from '../../src/components/StatePanel'

describe('shared UI components', () => {
  test('renders empty states with accessible copy', () => {
    render(<StatePanel title="No predictions yet" description="Run a prediction to populate this panel." />)

    expect(screen.getByText('No predictions yet')).toBeVisible()
    expect(screen.getByText('Run a prediction to populate this panel.')).toBeVisible()
  })

  test('renders metric labels, values, and supporting details', () => {
    render(<MetricCard metric={{ label: 'Portfolio Value', value: 'Rs 6,000', detail: '1 active positions' }} />)

    expect(screen.getByText('Portfolio Value')).toBeVisible()
    expect(screen.getByText('Rs 6,000')).toBeVisible()
    expect(screen.getByText('1 active positions')).toBeVisible()
  })

  test('exposes icon buttons by label and handles user clicks', async () => {
    const user = userEvent.setup()
    const onClick = vi.fn()

    render(
      <IconButton label="Refresh dashboard" onClick={onClick}>
        R
      </IconButton>,
    )

    await user.click(screen.getByRole('button', { name: 'Refresh dashboard' }))

    expect(onClick).toHaveBeenCalledOnce()
  })
})
