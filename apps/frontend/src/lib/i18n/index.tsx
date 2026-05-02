import { createContext, useContext, useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { fi, type Translations } from './fi'
import { en } from './en'

export type Lang = 'fi' | 'en'

const dictionaries: Record<Lang, Translations> = { fi, en }

const STORAGE_KEY = 'kipina_lang'

interface I18nContextValue {
  lang: Lang
  t: Translations
  setLang: (lang: Lang) => void
}

const I18nContext = createContext<I18nContextValue | null>(null)

function detectInitialLang(): Lang {
  if (typeof window === 'undefined') return 'fi'
  const stored = window.localStorage.getItem(STORAGE_KEY) as Lang | null
  if (stored === 'fi' || stored === 'en') return stored
  const navLang = window.navigator.language.toLowerCase()
  if (navLang.startsWith('en')) return 'en'
  return 'fi'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(detectInitialLang)

  useEffect(() => {
    document.documentElement.lang = lang
    window.localStorage.setItem(STORAGE_KEY, lang)
  }, [lang])

  const setLang = (next: Lang) => setLangState(next)

  const value: I18nContextValue = {
    lang,
    t: dictionaries[lang],
    setLang,
  }

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useTranslation() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useTranslation must be used within I18nProvider')
  return ctx
}
