import { useQuery } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { Layout } from '@/components/Layout'
import { Button } from '@/components/ui/button'
import { Card, CardTitle, CardBody } from '@/components/ui/card'
import { useTranslation } from '@/lib/i18n'
import { getTenants, type Tenant } from '@/lib/api'

export function HomePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

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
    </Layout>
  )
}
