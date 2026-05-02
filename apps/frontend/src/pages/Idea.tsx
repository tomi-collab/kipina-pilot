import { useState, useRef, useEffect } from 'react'
import { useNavigate, useParams } from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { Layout } from '@/components/Layout'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card } from '@/components/ui/card'
import { useTranslation } from '@/lib/i18n'
import { sendChatMessage, type ChatResponse } from '@/lib/api'
import { cn } from '@/lib/utils'

interface Turn {
  role: 'user' | 'assistant'
  text: string
}

const REPORT_STORAGE_PREFIX = 'kipina_report_'

export function IdeaPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { tenantId } = useParams({ strict: false }) as { tenantId: string }

  const [sessionId, setSessionId] = useState<string | null>(null)
  const [reportId, setReportId] = useState<string | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [finished, setFinished] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Jos ei tenanttia URLissa, ohjataan takaisin
  useEffect(() => {
    if (!tenantId) {
      navigate({ to: '/koti' })
    }
  }, [tenantId, navigate])

  const mutation = useMutation({
    mutationFn: (message: string) =>
      sendChatMessage({
        message,
        tenant_id: tenantId,
        session_id: sessionId,
      }),
    onSuccess: (data: ChatResponse) => {
      const nextSessionId = data.session_id || sessionId
      if (data.session_id && !sessionId) {
        setSessionId(data.session_id)
      }
      setTurns((prev) => [...prev, { role: 'assistant', text: data.reply }])
      const reportText = normalizeReport(data.report)
      if (data.finished && reportText && nextSessionId) {
        setReportId(nextSessionId)
        setFinished(true)
        sessionStorage.setItem(
          REPORT_STORAGE_PREFIX + nextSessionId,
          reportText
        )
      }
    },
  })

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [turns, mutation.isPending])

  const handleSend = () => {
    const text = draft.trim()
    if (!text || mutation.isPending || finished) return
    setTurns((prev) => [...prev, { role: 'user', text }])
    setDraft('')
    mutation.mutate(text)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault()
      handleSend()
    }
  }

  const showRetry = mutation.isError && !mutation.isPending

  return (
    <Layout showLogout>
      <h1 className="mb-6 text-3xl sm:text-4xl font-bold text-[var(--color-text)]">
        {t.idea.heading}
      </h1>

      <div
        ref={scrollRef}
        className="stack mb-6 max-h-[55vh] overflow-y-auto pr-1"
        aria-live="polite"
        aria-label="conversation"
      >
        {turns.map((turn, i) => (
          <TurnBubble key={i} role={turn.role} text={turn.text} t={t} />
        ))}

        {mutation.isPending && (
          <Card
            className="bg-[var(--color-surface-elevated)]"
            aria-label={t.idea.sending}
          >
            <p className="text-sm font-semibold text-[var(--color-text-faint)] mb-2">
              {t.idea.assistantTurn}
            </p>
            <ThinkingIndicator label={t.idea.sending} />
          </Card>
        )}
      </div>

      {finished ? (
        <Card>
          <p className="mb-4 text-lg font-semibold text-[var(--color-success)]">
            {t.idea.finishedNotice}
          </p>
          <Button
            size="xl"
            onClick={() =>
              navigate({
                to: '/konsepti/$id',
                params: { id: reportId ?? sessionId ?? tenantId },
              })
            }
          >
            {t.idea.showConcept} →
          </Button>
        </Card>
      ) : (
        <Card>
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t.idea.placeholder}
            disabled={mutation.isPending}
            aria-label={t.idea.heading}
          />
          {showRetry && (
            <p
              role="alert"
              className="mt-3 text-base text-[var(--color-danger)]"
            >
              {t.idea.networkError}
            </p>
          )}
          <div className="mt-4 flex flex-col sm:flex-row gap-3">
            <Button
              size="xl"
              onClick={handleSend}
              disabled={!draft.trim() || mutation.isPending}
              className="flex-1"
            >
              {mutation.isPending ? t.idea.sending : t.idea.send}
            </Button>
            {showRetry && (
              <Button
                variant="secondary"
                size="xl"
                onClick={() => mutation.reset()}
              >
                {t.common.retry}
              </Button>
            )}
          </div>
        </Card>
      )}
    </Layout>
  )
}

function normalizeReport(value: unknown): string | null {
  const text = reportValueToText(value).trim()
  if (!text || text === '[object Object]') return null
  return text
}

function reportValueToText(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  if (Array.isArray(value)) {
    return value.map(reportValueToText).filter(Boolean).join('\n\n')
  }
  if (typeof value === 'object') {
    const record = value as Record<string, unknown>
    for (const key of ['text', 'content', 'markdown', 'report', 'final_report']) {
      const text = reportValueToText(record[key]).trim()
      if (text) return text
    }

    return Object.entries(record)
      .map(([key, nested]) => {
        const text = reportValueToText(nested).trim()
        return text ? `${labelFromKey(key)}\n${text}` : ''
      })
      .filter(Boolean)
      .join('\n\n')
  }
  return ''
}

function labelFromKey(key: string): string {
  const label = key.replace(/[_-]/g, ' ').trim()
  return label ? label.charAt(0).toUpperCase() + label.slice(1) : key
}

function TurnBubble({
  role,
  text,
  t,
}: {
  role: 'user' | 'assistant'
  text: string
  t: ReturnType<typeof useTranslation>['t']
}) {
  return (
    <Card
      className={cn(
        role === 'user'
          ? 'bg-[var(--color-surface-elevated)]'
          : 'bg-[var(--color-surface)]'
      )}
    >
      <p className="text-sm font-semibold text-[var(--color-text-faint)] mb-2">
        {role === 'user' ? t.idea.yourTurn : t.idea.assistantTurn}
      </p>
      <p className="whitespace-pre-wrap text-lg text-[var(--color-text)]">
        {text}
      </p>
    </Card>
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
