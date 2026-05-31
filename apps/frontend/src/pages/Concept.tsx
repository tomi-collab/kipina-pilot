import { useEffect, useState } from 'react'
import { useNavigate, useParams } from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { Layout } from '@/components/Layout'
import { Button } from '@/components/ui/button'
import { Card, CardTitle, CardBody } from '@/components/ui/card'
import { useTranslation } from '@/lib/i18n'
import { generateConcept, type GenerateConceptResponse } from '@/lib/api'

const REPORT_STORAGE_PREFIX = 'kipina_report_'
const VIBE_REPORT_STORAGE_PREFIX = 'kipina-report-'
const VIBE_CONCEPT_STORAGE_PREFIX = 'kipina-concept-'
const VIBE_TEMPLATES_STORAGE_PREFIX = 'kipina-templates-'
const conceptCache = new Map<string, string>()
const templateCache = new Map<string, string[]>()

export function ConceptPage() {
  const { lang, t } = useTranslation()
  const navigate = useNavigate()
  const { id } = useParams({ from: '/protected/konsepti/$id' })
  const [report, setReport] = useState<string | null>(null)
  const [concept, setConcept] = useState<string | null>(null)

  useEffect(() => {
    const stored = sessionStorage.getItem(REPORT_STORAGE_PREFIX + id)
    const reportText = stored && stored !== '[object Object]' ? stored : null
    setReport(reportText)
    setConcept(reportText ? conceptCache.get(cacheKey(reportText, lang)) ?? null : null)
  }, [id, lang])

  const mutation = useMutation({
    mutationFn: (reportText: string) =>
      generateConcept({ report: reportText, language: lang }),
    onSuccess: (data: GenerateConceptResponse, reportText) => {
      conceptCache.set(cacheKey(reportText, lang), data.concept)
      templateCache.set(cacheKey(reportText, lang), data.suggested_templates ?? [])
      setConcept(data.concept)
      sessionStorage.setItem(VIBE_CONCEPT_STORAGE_PREFIX + id, data.concept)
      sessionStorage.setItem(
        VIBE_TEMPLATES_STORAGE_PREFIX + id,
        JSON.stringify(data.suggested_templates ?? [])
      )
    },
  })

  const handleGenerate = () => {
    if (!report || mutation.isPending) return
    const cached = conceptCache.get(cacheKey(report, lang))
    if (cached) {
      setConcept(cached)
      sessionStorage.setItem(VIBE_CONCEPT_STORAGE_PREFIX + id, cached)
      sessionStorage.setItem(
        VIBE_TEMPLATES_STORAGE_PREFIX + id,
        JSON.stringify(templateCache.get(cacheKey(report, lang)) ?? [])
      )
      return
    }
    mutation.mutate(report)
  }

  const handleStartVibeCoding = () => {
    if (!report) return
    sessionStorage.setItem(VIBE_CONCEPT_STORAGE_PREFIX + id, concept ?? report)
    sessionStorage.setItem(VIBE_REPORT_STORAGE_PREFIX + id, report)
    if (!sessionStorage.getItem(VIBE_TEMPLATES_STORAGE_PREFIX + id)) {
      sessionStorage.setItem(VIBE_TEMPLATES_STORAGE_PREFIX + id, JSON.stringify([]))
    }
    navigate({ to: '/vibe/$sessionId', params: { sessionId: id } })
  }

  const showError = mutation.isError && !mutation.isPending

  return (
    <Layout showLogout>
      <h1 className="mb-6 text-3xl sm:text-4xl font-bold text-[var(--color-text)]">
        {t.concept.heading}
      </h1>

      <Card>
        <CardTitle>{t.concept.description}</CardTitle>
        <CardBody>
          <pre className="whitespace-pre-wrap font-sans text-lg leading-relaxed text-[var(--color-text)]">
            {report ?? t.common.loading}
          </pre>
        </CardBody>
      </Card>

      <div className="mt-6">
        <Button
          size="xl"
          onClick={handleGenerate}
          disabled={!report || mutation.isPending}
        >
          {mutation.isPending ? t.concept.loading : t.concept.generateButton}
        </Button>
      </div>

      {mutation.isPending && (
        <Card
          className="mt-6 bg-[var(--color-surface-elevated)]"
          aria-live="polite"
        >
          <ThinkingIndicator label={t.concept.loading} />
        </Card>
      )}

      {showError && (
        <Card className="mt-6 border-[var(--color-danger)]" role="alert">
          <p className="mb-4 text-lg font-semibold text-[var(--color-danger)]">
            {t.concept.errorTitle}
          </p>
          <Button
            variant="secondary"
            size="lg"
            onClick={handleGenerate}
            disabled={!report}
          >
            {t.concept.errorRetry}
          </Button>
        </Card>
      )}

      {concept && (
        <Card className="mt-6 bg-[var(--color-surface-elevated)]">
          <CardTitle>{t.concept.generatedHeading}</CardTitle>
          <CardBody>
            <ConceptText text={concept} />
          </CardBody>
        </Card>
      )}

      <div className="mt-6 flex flex-col sm:flex-row gap-3">
        <Button
          size="xl"
          onClick={handleStartVibeCoding}
          disabled={!report}
          className="bg-emerald-500 text-slate-950 shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:bg-emerald-400"
        >
          {t.vibe.startButton} →
        </Button>
        <Button
          variant="secondary"
          size="xl"
          onClick={() => navigate({ to: '/koti' })}
        >
          {t.concept.backToHome}
        </Button>
      </div>
    </Layout>
  )
}

function cacheKey(report: string, lang: string) {
  return `${lang}:${report}`
}

function ConceptText({ text }: { text: string }) {
  return (
    <div className="space-y-3 text-[var(--color-text-muted)]">
      {text.split('\n').map((line, index) => {
        const trimmed = line.trim()
        if (!trimmed) {
          return <div key={index} className="h-2" aria-hidden="true" />
        }

        if (trimmed.startsWith('## ')) {
          return (
            <h2
              key={index}
              className="pt-3 text-2xl font-bold text-[var(--color-text)] first:pt-0"
            >
              {trimmed.slice(3)}
            </h2>
          )
        }

        const bullet = trimmed.match(/^[-*]\s+(.*)$/)
        if (bullet) {
          return (
            <p key={index} className="flex gap-3 text-lg leading-relaxed">
              <span aria-hidden="true">-</span>
              <span>{bullet[1]}</span>
            </p>
          )
        }

        return (
          <p key={index} className="whitespace-pre-wrap text-lg leading-relaxed">
            {trimmed}
          </p>
        )
      })}
    </div>
  )
}

function ThinkingIndicator({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-3 text-[var(--color-text-muted)]">
      <span className="flex gap-1" aria-hidden="true">
        <Dot delay="0s" />
        <Dot delay="0.15s" />
        <Dot delay="0.3s" />
      </span>
      <span className="text-base">{label}</span>
    </div>
  )
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="inline-block h-2 w-2 rounded-full bg-[var(--color-text-muted)]"
      style={{
        animation: 'kipina-bounce 1s infinite',
        animationDelay: delay,
      }}
    />
  )
}
