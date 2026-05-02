import { createContext, useContext, useState, useCallback } from 'react'
import type { ReactNode } from 'react'

const STORAGE_KEY = 'kipina_auth_ok'

interface AuthContextValue {
  isAuthed: boolean
  setAuthed: (value: boolean) => void
  signOut: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readInitial(): boolean {
  if (typeof window === 'undefined') return false
  return window.sessionStorage.getItem(STORAGE_KEY) === '1'
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthed, setIsAuthed] = useState<boolean>(readInitial)

  const setAuthed = useCallback((value: boolean) => {
    if (value) {
      window.sessionStorage.setItem(STORAGE_KEY, '1')
    } else {
      window.sessionStorage.removeItem(STORAGE_KEY)
    }
    setIsAuthed(value)
  }, [])

  const signOut = useCallback(() => setAuthed(false), [setAuthed])

  return (
    <AuthContext.Provider value={{ isAuthed, setAuthed, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
