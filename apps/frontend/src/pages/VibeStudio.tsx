import { useEffect } from 'react'
import { useNavigate, useParams } from '@tanstack/react-router'
import { VibeControls } from '@/components/vibe/VibeControls'
import { VibeDrawer } from '@/components/vibe/VibeDrawer'
import { VibePreview } from '@/components/vibe/VibePreview'
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
    startSession,
    iterate,
    setPromptText,
    setDrawerOpen,
    clearError,
  } = useVibeSession(sessionId, lang)

  useEffect(() => {
    if (!sessionId || !/^[A-Za-z0-9._:-]+$/.test(sessionId)) {
      navigate({ to: '/koti' })
    }
  }, [navigate, sessionId])

  useEffect(() => {
    if (state.initialized || state.prototypeHtml) return
    if (sessionStorage.getItem(VIBE_STORAGE_PREFIX + sessionId)) return

    const concept = sessionStorage.getItem(CONCEPT_STORAGE_PREFIX + sessionId)
    const report =
      sessionStorage.getItem(REPORT_STORAGE_PREFIX + sessionId) ??
      sessionStorage.getItem(LEGACY_REPORT_STORAGE_PREFIX + sessionId)

    if (!concept || !report) {
      navigate({ to: '/konsepti/$id', params: { id: sessionId } })
      return
    }

    startSession(concept, report, 'vibe')
  }, [
    navigate,
    sessionId,
    startSession,
    state.initialized,
    state.prototypeHtml,
  ])

  const handleBack = () => {
    navigate({ to: '/konsepti/$id', params: { id: sessionId } })
  }

  const handleSubmit = () => {
    iterate(state.promptText)
  }

  const retryStart = () => {
    clearError()
    if (state.prototypeHtml) return
    const concept = sessionStorage.getItem(CONCEPT_STORAGE_PREFIX + sessionId)
    const report =
      sessionStorage.getItem(REPORT_STORAGE_PREFIX + sessionId) ??
      sessionStorage.getItem(LEGACY_REPORT_STORAGE_PREFIX + sessionId)
    if (!concept || !report) {
      navigate({ to: '/konsepti/$id', params: { id: sessionId } })
      return
    }
    startSession(concept, report, 'vibe')
  }

  const errorText = state.expired
    ? t.vibe.errors.sessionExpired
    : state.error
      ? t.vibe.errors.startFailed
      : null

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
    </div>
  )
}
