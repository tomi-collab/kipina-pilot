import { useMemo } from 'react'

interface VibePreviewProps {
  prototypeHtml: string
  sandboxId: string | null
  isLoading: boolean
  loadingLabel: string
  title: string
}

export function VibePreview({
  prototypeHtml,
  sandboxId,
  isLoading,
  loadingLabel,
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
          sandbox="allow-scripts allow-forms"
          title={title}
        />
      ) : (
        <div className="flex h-full items-center justify-center px-6 text-center text-slate-400">
          {loadingLabel}
        </div>
      )}

      {isLoading && (
        <div
          className="absolute inset-0 flex items-center justify-center bg-slate-900/60"
          aria-live="polite"
        >
          <div className="flex items-center gap-3 rounded-2xl bg-slate-950/90 px-5 py-4 text-slate-100 shadow-2xl">
            <span
              className="h-5 w-5 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent"
              aria-hidden="true"
            />
            <span className="text-base font-semibold">{loadingLabel}</span>
          </div>
        </div>
      )}
    </div>
  )
}
