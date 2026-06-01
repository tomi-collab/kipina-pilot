import { useEffect, useState } from 'react'

const TIP_INTERVAL_MS = 6000
const TIP_FADE_MS = 300

interface VibeWaitingIndicatorProps {
  label: string
  tips: string[]
}

function shuffleTips(tips: string[]) {
  const shuffled = [...tips]
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    ;[shuffled[index], shuffled[swapIndex]] = [
      shuffled[swapIndex],
      shuffled[index],
    ]
  }
  return shuffled
}

function useReducedMotion() {
  const [reduced, setReduced] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const query = window.matchMedia('(prefers-reduced-motion: reduce)')
    setReduced(query.matches)
    const update = () => setReduced(query.matches)
    query.addEventListener('change', update)
    return () => query.removeEventListener('change', update)
  }, [])

  return reduced
}

export function VibeWaitingIndicator({
  label,
  tips,
}: VibeWaitingIndicatorProps) {
  const reducedMotion = useReducedMotion()
  const [tipOrder, setTipOrder] = useState(() => shuffleTips(tips))
  const [tipIndex, setTipIndex] = useState(0)
  const [tipVisible, setTipVisible] = useState(true)

  useEffect(() => {
    setTipOrder(shuffleTips(tips))
    setTipIndex(0)
    setTipVisible(true)
  }, [tips])

  useEffect(() => {
    if (tipOrder.length < 2) return

    const advanceTip = () => {
      setTipOrder((currentOrder) => {
        if (tipIndex < currentOrder.length - 1) return currentOrder
        return shuffleTips(tips)
      })
      setTipIndex((currentIndex) =>
        currentIndex < tipOrder.length - 1 ? currentIndex + 1 : 0
      )
    }

    let fadeTimeoutId: number | undefined
    const intervalId = window.setInterval(() => {
      if (reducedMotion) {
        advanceTip()
        return
      }
      setTipVisible(false)
      fadeTimeoutId = window.setTimeout(() => {
        advanceTip()
        setTipVisible(true)
      }, TIP_FADE_MS)
    }, TIP_INTERVAL_MS)

    return () => {
      window.clearInterval(intervalId)
      if (fadeTimeoutId !== undefined) window.clearTimeout(fadeTimeoutId)
    }
  }, [reducedMotion, tipIndex, tipOrder.length, tips])

  const activeTip = tipOrder[tipIndex] ?? tips[0] ?? ''

  return (
    <div className="flex max-w-sm flex-col items-center text-center">
      <p className="text-base font-semibold text-slate-50 md:text-lg">
        {label}
      </p>
      <div className="mt-4 flex h-8 items-center gap-2" aria-hidden="true">
        {[0, 1, 2].map((dot) => (
          <span
            key={dot}
            className="h-3 w-3 rounded-full bg-[var(--color-accent)]"
            style={{
              animation: reducedMotion
                ? 'none'
                : `kipina-bounce 1.6s ${dot * 0.18}s ease-in-out infinite`,
            }}
          />
        ))}
      </div>
      {activeTip && (
        <p
          className={[
            'mt-4 min-h-20 text-sm leading-relaxed text-slate-300 transition-opacity duration-300 md:min-h-16 md:text-base',
            tipVisible ? 'opacity-100' : 'opacity-0',
          ].join(' ')}
        >
          {activeTip}
        </p>
      )}
    </div>
  )
}
