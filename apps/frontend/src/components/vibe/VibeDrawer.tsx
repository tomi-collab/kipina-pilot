import { useEffect, useRef, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface VibeDrawerProps {
  open: boolean
  label: string
  onOpenChange: (open: boolean) => void
  children: ReactNode
}

export function VibeDrawer({
  open,
  label,
  onOpenChange,
  children,
}: VibeDrawerProps) {
  const drawerHeaderRef = useRef<HTMLDivElement>(null)
  const [startY, setStartY] = useState(0)

  useEffect(() => {
    const el = drawerHeaderRef.current
    if (!el) return

    const onTouchStart = (event: TouchEvent) =>
      setStartY(event.touches[0].clientY)
    const onTouchEnd = (event: TouchEvent) => {
      const endY = event.changedTouches[0].clientY
      const diff = endY - startY
      if (diff > 30) onOpenChange(false)
      else if (diff < -30) onOpenChange(true)
      else if (Math.abs(diff) < 10) onOpenChange(!open)
    }

    el.addEventListener('touchstart', onTouchStart, { passive: true })
    el.addEventListener('touchend', onTouchEnd, { passive: true })
    return () => {
      el.removeEventListener('touchstart', onTouchStart)
      el.removeEventListener('touchend', onTouchEnd)
    }
  }, [onOpenChange, open, startY])

  return (
    <aside
      className={cn(
        'fixed inset-x-0 bottom-0 z-20 flex h-[72vh] flex-col rounded-t-3xl border border-slate-700 bg-slate-900 shadow-2xl transition-transform duration-300 ease-out md:static md:h-auto md:min-h-0 md:w-96 md:translate-y-0 md:rounded-none md:border-y-0 md:border-l-0 md:shadow-none',
        open ? 'translate-y-0' : 'translate-y-[calc(100%-100px)]'
      )}
    >
      <div
        ref={drawerHeaderRef}
        role="button"
        tabIndex={0}
        aria-expanded={open}
        aria-label={label}
        onClick={() => onOpenChange(!open)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault()
            onOpenChange(!open)
          }
        }}
        className="flex min-h-[100px] cursor-pointer flex-col items-center justify-center gap-3 px-5 text-slate-300 md:hidden"
      >
        <span className="h-1.5 w-14 rounded-full bg-slate-600" aria-hidden="true" />
        <span className="text-sm font-semibold">{label}</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-6 md:flex md:flex-col md:px-6 md:py-6">
        {children}
      </div>
    </aside>
  )
}
