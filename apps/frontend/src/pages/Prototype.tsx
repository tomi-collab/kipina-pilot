import { useNavigate } from '@tanstack/react-router'
import { Layout } from '@/components/Layout'
import { Button } from '@/components/ui/button'
import { Card, CardTitle, CardBody } from '@/components/ui/card'
import { useTranslation } from '@/lib/i18n'

export function PrototypePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  return (
    <Layout showLogout>
      <h1 className="mb-6 text-3xl sm:text-4xl font-bold text-[var(--color-text)]">
        {t.prototype.heading}
      </h1>

      <Card>
        <CardTitle>{t.prototype.description}</CardTitle>
        <CardBody>
          <p>{t.prototype.placeholder}</p>
        </CardBody>
      </Card>

      <div className="mt-6">
        <Button
          variant="secondary"
          size="xl"
          onClick={() => navigate({ to: '/koti' })}
        >
          ← {t.prototype.backToHome}
        </Button>
      </div>
    </Layout>
  )
}
