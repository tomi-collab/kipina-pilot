import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { Layout } from '@/components/Layout'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardTitle, CardBody } from '@/components/ui/card'
import { useTranslation } from '@/lib/i18n'
import { useAuth } from '@/lib/auth'
import { checkAccessCode, ApiError } from '@/lib/api'

export function LoginPage() {
  const { t } = useTranslation()
  const { setAuthed } = useAuth()
  const navigate = useNavigate()
  const [code, setCode] = useState('')

  const mutation = useMutation({
    mutationFn: (value: string) => checkAccessCode(value),
    onSuccess: (data) => {
      if (data.ok) {
        setAuthed(true)
        navigate({ to: '/koti' })
      }
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!code.trim() || mutation.isPending) return
    mutation.mutate(code.trim())
  }

  const errorMessage = (() => {
    if (!mutation.isError) return null
    const err = mutation.error
    if (err instanceof ApiError && err.status === 401) {
      return t.login.error
    }
    return t.login.networkError
  })()

  return (
    <Layout>
      <Card>
        <CardTitle>{t.login.heading}</CardTitle>
        <CardBody>
          <p className="mb-6">{t.login.description}</p>
          <form onSubmit={handleSubmit} className="stack" noValidate>
            <label className="block">
              <span className="block mb-2 text-base font-medium text-[var(--color-text)]">
                {t.login.codeLabel}
              </span>
              <Input
                type="text"
                inputMode="text"
                autoComplete="off"
                autoCapitalize="characters"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder={t.login.codePlaceholder}
                aria-invalid={mutation.isError}
                aria-describedby={errorMessage ? 'login-error' : undefined}
                disabled={mutation.isPending}
              />
            </label>

            {errorMessage && (
              <p
                id="login-error"
                role="alert"
                className="text-[var(--color-danger)] text-base"
              >
                {errorMessage}
              </p>
            )}

            <Button
              type="submit"
              size="xl"
              disabled={!code.trim() || mutation.isPending}
            >
              {mutation.isPending ? t.common.loading : t.login.submit}
            </Button>
          </form>
        </CardBody>
      </Card>
    </Layout>
  )
}
