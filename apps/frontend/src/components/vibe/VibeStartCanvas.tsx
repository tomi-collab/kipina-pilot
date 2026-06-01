import { Button } from '@/components/ui/button'
import { VibeWaitingIndicator } from '@/components/vibe/VibeWaitingIndicator'
import type { VibeStartPhase } from '@/hooks/useVibeSession'
import { useTranslation } from '@/lib/i18n'

interface VibeStartCanvasProps {
  hasError: boolean
  phase: VibeStartPhase
  onRetry: () => void
}

export function VibeStartCanvas({
  hasError,
  phase,
  onRetry,
}: VibeStartCanvasProps) {
  const { t } = useTranslation()

  return (
    <div className="fixed inset-0 z-50 flex min-h-dvh items-center justify-center bg-slate-950 px-5 text-slate-100">
      <div className="w-full max-w-md text-center">
        {/* SISÄLTÖALUE — Tomi täyttää: rahoittajat, ilmoitukset, vinkit.
            Tällä hetkellä placeholder. Vaihda tämän divin sisältö. */}
        <div
          className="vibe-start-canvas__content rounded-3xl border border-slate-700 bg-slate-900 px-6 py-8 shadow-2xl"
          role="status"
          aria-live="polite"
          data-phase={phase}
        >
          {hasError ? (
            <>
              <p className="text-xl font-bold text-slate-50">
                Sovelluksen luonti kesti tavallista kauemmin tai epäonnistui.
                Yritä uudelleen.
              </p>
              <Button className="mt-6 min-h-12 w-full" size="lg" onClick={onRetry}>
                Yritä uudelleen
              </Button>
            </>
          ) : (
            <>
              {/* VAIHE-SISÄLTÖ — Tomi voi myöhemmin näyttää eri sisältöä per phase.
                  Nyt: yksi placeholder kaikille vaiheille. */}
              <VibeWaitingIndicator
                label="Mestari rakentaa sovellustasi…"
                tips={t.vibe.tips}
              />
            </>
          )}
        </div>
      </div>
    </div>
  )
}
