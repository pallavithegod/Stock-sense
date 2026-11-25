import { beforeEach, describe, expect, test, vi } from 'vitest'

vi.mock('../../src/auth/supabase', () => ({
  getAccessToken: vi.fn(),
}))

import { getAccessToken } from '../../src/auth/supabase'
import { apiClient } from '../../src/api/client'

describe('API authentication', () => {
  beforeEach(() => {
    vi.mocked(getAccessToken).mockResolvedValue('user-access-token')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ success: true, data: [] }),
      }),
    )
  })

  test('forwards the active Supabase access token to the API', async () => {
    await apiClient.get('/portfolio')

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/portfolio'),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: 'Bearer user-access-token',
        }),
      }),
    )
  })

  test('does not send an authorization header without a signed-in session', async () => {
    vi.mocked(getAccessToken).mockResolvedValueOnce(null)

    await apiClient.get('/stocks')

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/stocks'),
      expect.objectContaining({
        headers: expect.not.objectContaining({ Authorization: expect.anything() }),
      }),
    )
  })
})
