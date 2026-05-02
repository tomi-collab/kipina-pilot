import type { ReactNode } from 'react'
import { useTranslation, type Lang } from '@/lib/i18n'
import { useAuth } from '@/lib/auth'
import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'

interface LayoutProps {
  children: ReactNode
  showLogout?: boolean
}

export function Layout({ children, showLogout = false }: LayoutProps) {
  const { lang, setLang, t } = useTranslation()
  const { signOut } = useAuth()
  const navigate = useNavigate()

  const handleSignOut = () => {
    signOut()
    navigate({ to: '/' })
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-[var(--color-border)] bg-[var(--color-bg)]">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-baseline gap-3">
            <span className="text-xl font-bold text-[var(--color-accent)]">
              {t.app.title}
            </span>
            <span className="hidden sm:inline text-sm text-[var(--color-text-faint)]">
              {t.app.tagline}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <LanguageSwitch current={lang} onChange={setLang} />
            {showLogout && (
              <Button
                variant="ghost"
                size="md"
                onClick={handleSignOut}
                aria-label={t.nav.logout}
              >
                {t.nav.logout}
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-6 sm:py-12">
          {children}
        </div>
      </main>
    </div>
  )
}

interface LanguageSwitchProps {
  current: Lang
  onChange: (lang: Lang) => void
}

function LanguageSwitch({ current, onChange }: LanguageSwitchProps) {
  return (
    <div
      role="group"
      aria-label="Language"
      className="flex rounded-[var(--radius)] border border-[var(--color-border)] overflow-hidden"
    >
      <LangButton active={current === 'fi'} onClick={() => onChange('fi')}>
        FI
      </LangButton>
      <LangButton active={current === 'en'} onClick={() => onChange('en')}>
        EN
      </LangButton>
    </div>
  )
}

function LangButton({
  active,
  children,
  onClick,
}: {
  active: boolean
  children: ReactNode
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={
        'min-h-12 px-4 text-base font-semibold transition-colors ' +
        (active
          ? 'bg-[var(--color-accent)] text-[var(--color-accent-fg)]'
          : 'bg-transparent text-[var(--color-text-muted)] hover:bg-[var(--color-surface)]')
      }
    >
      {children}
    </button>
  )
}
