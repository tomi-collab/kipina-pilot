import { useMemo } from 'react'
import { VibeWaitingIndicator } from '@/components/vibe/VibeWaitingIndicator'

interface VibePreviewProps {
  prototypeHtml: string
  sandboxId: string | null
  isLoading: boolean
  loadingLabel: string
  loadingTips: string[]
  title: string
}

export function VibePreview({
  prototypeHtml,
  sandboxId,
  isLoading,
  loadingLabel,
  loadingTips,
  title,
}: VibePreviewProps) {
  const injectedHtml = useMemo(() => {
    if (!prototypeHtml || !sandboxId) return prototypeHtml

    const injection = `<script>window.__KIPINA_SANDBOX_ID__ = ${JSON.stringify(sandboxId)};</script>`
    if (prototypeHtml.includes('</head>')) {
      return prototypeHtml.replace('</head>', `${injection}</head>`)
    }
    return injection + prototypeHtml
  }, [prototypeHtml, sandboxId])

  return (
    <div className="relative h-full min-h-0 w-full overflow-hidden bg-slate-950">
      {prototypeHtml ? (
        <iframe
          className="h-full w-full border-none bg-white"
          srcDoc={injectedHtml}
          sandbox="allow-scripts allow-forms allow-modals"
          allow="clipboard-write; fullscreen"
          title={title}
        />
      ) : (
        <div className="flex h-full items-center justify-center px-6 text-center text-slate-400">
          {loadingLabel}
        </div>
      )}

      {isLoading && (
        <div
          className="absolute inset-0 flex items-center justify-center bg-slate-900/70 px-5"
          aria-live="polite"
        >
          <div className="rounded-2xl border border-slate-700 bg-slate-950/90 px-5 py-5 text-slate-100 shadow-2xl md:px-6 md:py-6">
            <VibeWaitingIndicator label={loadingLabel} tips={loadingTips} />
          </div>
        </div>
      )}
    </div>
  )
}
