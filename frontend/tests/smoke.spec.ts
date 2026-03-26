import { expect, test } from '@playwright/test'

test('renders login screen for anonymous users', async ({ page }) => {
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Connexion DealTracker' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Se connecter avec Microsoft' })).toBeVisible()
})

test('navigates to pipeline with authenticated session', async ({ page }) => {
  await page.addInitScript(() => {
    const session = {
      access_token: 'fake-access-token',
      refresh_token: 'fake-refresh-token',
      token_type: 'bearer',
      expires_in: 3600,
      expires_at: 4102444800,
      user: {
        id: '11111111-1111-1111-1111-111111111111',
        aud: 'authenticated',
        role: 'authenticated',
        email: 'alice.martin@edge-consulting.biz',
        email_confirmed_at: '2026-01-01T00:00:00.000Z',
        phone: '',
        confirmed_at: '2026-01-01T00:00:00.000Z',
        app_metadata: { provider: 'azure', providers: ['azure'] },
        user_metadata: { full_name: 'Alice Martin' },
        identities: [],
        created_at: '2026-01-01T00:00:00.000Z',
        updated_at: '2026-01-01T00:00:00.000Z',
      },
    }

    window.localStorage.setItem('sb-e2e-project-auth-token', JSON.stringify(session))
  })

  await page.route('**/api/dashboard/kpis', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        activeCount: 1,
        winRate: 0.33,
        overdueCount: 0,
        byOwner: [{ owner: 'alice.martin@edge-consulting.biz', count: 1 }],
      }),
    })
  })

  await page.route('**/api/summary/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [] }),
    })
  })

  await page.route('**/api/settings/users', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: '11111111-1111-1111-1111-111111111111',
          email: 'alice.martin@edge-consulting.biz',
          full_name: 'Alice Martin',
          whatsapp_number: null,
        },
      ]),
    })
  })

  await page.route('**/api/deals', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'deal-1',
          company: 'Belfius',
          description: 'Relance proposition',
          action: 'Rappeler vendredi',
          deadline: '2026-03-31',
          owner: 'alice.martin@edge-consulting.biz',
          owner_id: '11111111-1111-1111-1111-111111111111',
          status: 'active',
        },
      ]),
    })
  })

  await page.goto('/')
  await page.getByRole('link', { name: 'Pipeline' }).click()

  await expect(page.getByRole('heading', { name: 'Pipeline' })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'Belfius' })).toBeVisible()
  await expect(page.getByText('Responsable')).toBeVisible()
})
