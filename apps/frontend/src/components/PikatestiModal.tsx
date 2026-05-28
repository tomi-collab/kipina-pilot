import { useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { startPrototype } from '@/api/vibeApi'
import { useTranslation } from '@/lib/i18n'

interface PikatestiModalProps {
  open: boolean
  onClose: () => void
}

export function PikatestiModal({ open, onClose }: PikatestiModalProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [vibe, setVibe] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  const handleSubmit = async () => {
    const trimmed = vibe.trim()
    if (!trimmed || isLoading) return

    setIsLoading(true)
    setError(null)
    const sessionId = `pikatesti-${Date.now()}`

    try {
      const response = await startPrototype({
        sessionId,
        vibe: trimmed,
      })

      sessionStorage.setItem(
        `kipina-vibe-${sessionId}`,
        JSON.stringify({
          sandboxId: response.sandbox_id,
          prototypeHtml: response.prototype_html,
          mestariMessage: response.mestari_message,
          iterationCount: 0,
        })
      )
      navigate({ to: '/vibe/$sessionId', params: { sessionId } })
    } catch {
      setError(t.pikatesti.errors.startFailed)
      setIsLoading(false)
    }
  }

  const closeIfIdle = () => {
    if (!isLoading) onClose()
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
      onMouseDown={closeIfIdle}
      role="presentation"
    >
      <div
        className="w-full max-w-md space-y-4 rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
        onMouseDown={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="pikatesti-title"
      >
        <div className="flex items-center justify-between gap-4">
          <h2 id="pikatesti-title" className="text-xl font-bold text-emerald-400">
            {t.pikatesti.title}
          </h2>
          <button
            type="button"
            onClick={closeIfIdle}
            className="min-h-11 min-w-11 rounded-xl text-xl font-semibold text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-100 disabled:opacity-50"
            aria-label={t.pikatesti.close}
            disabled={isLoading}
          >
            ×
          </button>
        </div>

        <p className="text-sm leading-relaxed text-slate-400">
          {t.pikatesti.description}
        </p>

        <textarea
          className="h-32 w-full resize-none rounded-2xl border border-slate-700 bg-slate-800 p-4 text-sm text-slate-100 outline-none transition-all focus:border-transparent focus:ring-2 focus:ring-emerald-500"
          placeholder={t.pikatesti.placeholder}
          value={vibe}
          onChange={(event) => setVibe(event.target.value)}
          disabled={isLoading}
          autoFocus
        />

        {error && <p className="text-sm text-rose-400">{error}</p>}

        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            onClick={closeIfIdle}
            disabled={isLoading}
            className="min-h-12 flex-1 rounded-2xl bg-slate-800 px-4 py-3 font-semibold text-slate-100 transition-colors hover:bg-slate-700 disabled:opacity-50"
          >
            {t.pikatesti.cancel}
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isLoading || !vibe.trim()}
            className="min-h-12 flex-1 rounded-2xl bg-emerald-500 px-4 py-3 font-bold text-slate-950 shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all hover:bg-emerald-400 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? t.pikatesti.loading : t.pikatesti.start}
          </button>
        </div>
      </div>
    </div>
  )
}
