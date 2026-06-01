import { useEffect, useState } from 'react'
import { useNavigate, useParams } from '@tanstack/react-router'
import { VibeControls } from '@/components/vibe/VibeControls'
import { VibeDrawer } from '@/components/vibe/VibeDrawer'
import { VibePreview } from '@/components/vibe/VibePreview'
import { VibeStartCanvas } from '@/components/vibe/VibeStartCanvas'
import { Button } from '@/components/ui/button'
import { useVibeSession } from '@/hooks/useVibeSession'
import { useTranslation } from '@/lib/i18n'

const CONCEPT_STORAGE_PREFIX = 'kipina-concept-'
const REPORT_STORAGE_PREFIX = 'kipina-report-'
const LEGACY_REPORT_STORAGE_PREFIX = 'kipina_report_'
const VIBE_STORAGE_PREFIX = 'kipina-vibe-'

export function VibeStudioPage() {
  const { lang, t } = useTranslation()
  const navigate = useNavigate()
  const { sessionId } = useParams({ from: '/protected/vibe/$sessionId' })
  const {
    state,
    startAutomatedSession,
    iterate,
    setPromptText,
    setDrawerOpen,
    clearError,
  } = useVibeSession(sessionId, lang)
  const [conceptText, setConceptText] = useState<string | null>(null)
  const [conceptOpen, setConceptOpen] = useState(false)

  useEffect(() => {
    if (!sessionId || !/^[A-Za-z0-9._:-]+$/.test(sessionId)) {
      navigate({ to: '/koti' })
    }
  }, [navigate, sessionId])

  useEffect(() => {
    if (state.initialized || state.prototypeHtml) return
    if (sessionStorage.getItem(VIBE_STORAGE_PREFIX + sessionId)) return

    const report =
      sessionStorage.getItem(REPORT_STORAGE_PREFIX + sessionId) ??
      sessionStorage.getItem(LEGACY_REPORT_STORAGE_PREFIX + sessionId)

    if (!report) {
      navigate({ to: '/konsepti/$id', params: { id: sessionId } })
      return
    }

    startAutomatedSession(report, 'vibe')
  }, [
    navigate,
    sessionId,
    startAutomatedSession,
    state.initialized,
    state.prototypeHtml,
  ])

  useEffect(() => {
    const storedConcept = sessionStorage.getItem(CONCEPT_STORAGE_PREFIX + sessionId)
    setConceptText(storedConcept && storedConcept !== '[object Object]' ? storedConcept : null)
  }, [sessionId, state.isInitializing, state.prototypeHtml])

  const handleBack = () => {
    navigate({ to: '/konsepti/$id', params: { id: sessionId } })
  }

  const handleSubmit = () => {
    iterate(state.promptText)
  }

  const retryStart = () => {
    clearError()
    if (state.prototypeHtml) return
    const report =
      sessionStorage.getItem(REPORT_STORAGE_PREFIX + sessionId) ??
      sessionStorage.getItem(LEGACY_REPORT_STORAGE_PREFIX + sessionId)
    if (!report) {
      navigate({ to: '/konsepti/$id', params: { id: sessionId } })
      return
    }
    startAutomatedSession(report, 'vibe')
  }

  const errorText = state.expired
    ? t.vibe.errors.sessionExpired
    : state.error && state.prototypeHtml
      ? t.vibe.errors.startFailed
      : null
  const showStartCanvas =
    state.isInitializing || (!state.prototypeHtml && Boolean(state.error))

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-slate-950 text-slate-100">
      <header className="z-30 flex min-h-14 items-center justify-between border-b border-slate-800 bg-slate-950 px-4">
        <button
          type="button"
          aria-label={t.vibe.back}
          onClick={handleBack}
          className="min-h-12 rounded-xl px-3 text-base font-semibold text-slate-100 transition-colors hover:bg-slate-900"
        >
          ← {t.vibe.back}
        </button>
      </header>

      <main className="relative flex min-h-0 flex-1 flex-col md:flex-row">
        <div className="min-h-0 flex-1 pb-[100px] md:order-2 md:pb-0">
          <VibePreview
            prototypeHtml={state.prototypeHtml}
            sandboxId={state.sandboxId}
            isLoading={state.isLoading}
            loadingLabel={
              state.prototypeHtml ? t.vibe.preparing : t.vibe.startLoading
            }
            loadingTips={t.vibe.tips}
            title={t.prototype.heading}
          />
        </div>

        <VibeDrawer
          open={state.drawerOpen}
          label={t.vibe.drawerLabel}
          onOpenChange={setDrawerOpen}
        >
          <div className="hidden pb-6 md:block">
            <p className="text-sm font-semibold uppercase tracking-wide text-emerald-300">
              {t.vibe.drawerLabel}
            </p>
          </div>
          {conceptText && (
            <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-900/80 p-4">
              <Button
                type="button"
                variant="ghost"
                size="md"
                className="min-h-12 w-full justify-between px-0 text-left text-slate-100 hover:bg-transparent"
                onClick={() => setConceptOpen((open) => !open)}
                aria-expanded={conceptOpen}
              >
                <span>Näin ymmärsin ideasi</span>
                <span aria-hidden="true">{conceptOpen ? '−' : '+'}</span>
              </Button>
              {conceptOpen && (
                <div className="mt-3 max-h-72 overflow-y-auto border-t border-slate-700 pt-3 text-slate-300">
                  <ConceptSummary text={conceptText} />
                </div>
              )}
            </div>
          )}
          <VibeControls
            promptText={state.promptText}
            placeholder={t.vibe.promptPlaceholder}
            updateLabel={t.vibe.update}
            updatingLabel={t.vibe.updating}
            isLoading={state.isLoading}
            onPromptChange={setPromptText}
            onSubmit={handleSubmit}
          />
          {state.mestariMessage && (
            <p className="mt-5 text-sm leading-relaxed text-slate-400">
              {state.mestariMessage}
            </p>
          )}
        </VibeDrawer>
      </main>

      {errorText && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/80 px-4">
          <div
            role="alertdialog"
            aria-modal="true"
            className="w-full max-w-sm rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl"
          >
            <p className="mb-5 text-lg font-semibold text-slate-100">
              {errorText}
            </p>
            <div className="flex flex-col gap-3">
              {state.expired && (
                <Button
                  size="lg"
                  onClick={() =>
                    navigate({ to: '/konsepti/$id', params: { id: sessionId } })
                  }
                >
                  {t.vibe.errors.sessionExpiredAction}
                </Button>
              )}
              <Button
                variant="secondary"
                size="lg"
                onClick={state.prototypeHtml ? clearError : retryStart}
              >
                {t.common.retry}
              </Button>
            </div>
          </div>
        </div>
      )}

      {showStartCanvas && (
        <VibeStartCanvas
          hasError={Boolean(state.error)}
          phase={state.error ? 'error' : state.startPhase}
          onRetry={retryStart}
        />
      )}
    </div>
  )
}

function ConceptSummary({ text }: { text: string }) {
  return (
    <div className="space-y-2">
      {text.split('\n').map((line, index) => {
        const trimmed = line.trim()
        if (!trimmed) {
          return <div key={index} className="h-2" aria-hidden="true" />
        }
        if (trimmed.startsWith('## ')) {
          return (
            <h2 key={index} className="pt-2 text-lg font-bold text-slate-100 first:pt-0">
              {trimmed.slice(3)}
            </h2>
          )
        }
        const bullet = trimmed.match(/^[-*]\s+(.*)$/)
        if (bullet) {
          return (
            <p key={index} className="flex gap-2 text-sm leading-relaxed">
              <span aria-hidden="true">-</span>
              <span>{bullet[1]}</span>
            </p>
          )
        }
        return (
          <p key={index} className="whitespace-pre-wrap text-sm leading-relaxed">
            {trimmed}
          </p>
        )
      })}
    </div>
  )
}
