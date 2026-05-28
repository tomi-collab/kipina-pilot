import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Layout } from '@/components/Layout'
import { PikatestiModal } from '@/components/PikatestiModal'
import { Button } from '@/components/ui/button'
import { Card, CardTitle, CardBody } from '@/components/ui/card'
import { useTranslation } from '@/lib/i18n'
import { getTenants, type Tenant } from '@/lib/api'

export function HomePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [pikatestiOpen, setPikatestiOpen] = useState(false)
  const showPikatesti =
    import.meta.env.DEV ||
    new URLSearchParams(window.location.search).get('pikatesti') === '1'

  const { data: tenants, isLoading, isError } = useQuery({
    queryKey: ['tenants'],
    queryFn: getTenants,
    staleTime: Infinity,
  })

  const handleSelect = (tenant: Tenant) => {
    navigate({ to: '/idea/$tenantId', params: { tenantId: tenant.id } })
  }

  return (
    <Layout showLogout>
      <h1 className="mb-8 text-3xl sm:text-4xl font-bold text-[var(--color-text)]">
        {t.home.heading}
      </h1>

      {isLoading && (
        <p className="text-[var(--color-text-muted)]">{t.home.loadingTenants}</p>
      )}

      {isError && (
        <p className="text-[var(--color-danger)]">{t.common.retry}</p>
      )}

      {tenants && (
        <div className="stack">
          {tenants.map((tenant) => (
            <Card key={tenant.id}>
              <CardTitle>{tenant.name}</CardTitle>
              <CardBody>
                <p className="mb-6 text-[var(--color-text-muted)]">{tenant.description}</p>
                <Button size="xl" onClick={() => handleSelect(tenant)}>
                  {t.home.startButton} →
                </Button>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {showPikatesti && (
        <button
          type="button"
          onClick={() => setPikatestiOpen(true)}
          className="fixed bottom-4 right-4 z-40 min-h-11 rounded-full border border-emerald-500/40 bg-emerald-500/20 px-4 py-2 text-sm font-semibold text-emerald-300 backdrop-blur transition-all hover:bg-emerald-500/40"
        >
          {t.pikatesti.button}
        </button>
      )}

      <PikatestiModal
        open={pikatestiOpen}
        onClose={() => setPikatestiOpen(false)}
      />
    </Layout>
  )
}
