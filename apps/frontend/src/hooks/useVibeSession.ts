import { useCallback, useEffect, useReducer } from 'react'
import {
  iteratePrototype,
  startPrototype,
  type IterateResponse,
  type StartResponse,
  type VibeApiError,
} from '@/api/vibeApi'
import type { Lang } from '@/lib/i18n'

export interface VibeSessionState {
  sandboxId: string | null
  sessionId: string
  prototypeHtml: string
  mestariMessage: string
  iterationCount: number
  drawerOpen: boolean
  isLoading: boolean
  promptText: string
  error: string | null
  expired: boolean
  initialized: boolean
}

interface StoredVibeSession {
  sandboxId: string | null
  prototypeHtml: string
  mestariMessage: string
  iterationCount: number
}

type Action =
  | { type: 'RESTORE'; payload: StoredVibeSession }
  | { type: 'START_BEGIN' }
  | { type: 'START_SUCCESS'; payload: StartResponse }
  | { type: 'START_ERROR'; payload: string }
  | { type: 'ITERATE_BEGIN' }
  | { type: 'ITERATE_SUCCESS'; payload: IterateResponse }
  | { type: 'ITERATE_ERROR'; payload: string; expired: boolean }
  | { type: 'SET_PROMPT'; payload: string }
  | { type: 'SET_DRAWER'; payload: boolean }
  | { type: 'TOGGLE_DRAWER' }
  | { type: 'CLEAR_ERROR' }

function initialState(sessionId: string): VibeSessionState {
  return {
    sandboxId: null,
    sessionId,
    prototypeHtml: '',
    mestariMessage: '',
    iterationCount: 0,
    drawerOpen: false,
    isLoading: false,
    promptText: '',
    error: null,
    expired: false,
    initialized: false,
  }
}

function reducer(
  state: VibeSessionState,
  action: Action
): VibeSessionState {
  switch (action.type) {
    case 'RESTORE':
      return {
        ...state,
        sandboxId: action.payload.sandboxId,
        prototypeHtml: action.payload.prototypeHtml,
        mestariMessage: action.payload.mestariMessage,
        iterationCount: action.payload.iterationCount,
        initialized: true,
        error: null,
      }
    case 'START_BEGIN':
      return { ...state, isLoading: true, initialized: true, error: null }
    case 'START_SUCCESS':
      return {
        ...state,
        sandboxId: action.payload.sandbox_id,
        prototypeHtml: action.payload.prototype_html,
        mestariMessage: action.payload.mestari_message,
        iterationCount: 0,
        isLoading: false,
        initialized: true,
        error: null,
        expired: false,
      }
    case 'START_ERROR':
      return {
        ...state,
        isLoading: false,
        initialized: true,
        error: action.payload,
      }
    case 'ITERATE_BEGIN':
      return { ...state, isLoading: true, error: null }
    case 'ITERATE_SUCCESS':
      return {
        ...state,
        prototypeHtml: action.payload.prototype_html ?? state.prototypeHtml,
        mestariMessage: action.payload.mestari_message,
        iterationCount: action.payload.iteration_count,
        promptText: '',
        isLoading: false,
        error: null,
        expired: false,
      }
    case 'ITERATE_ERROR':
      return {
        ...state,
        isLoading: false,
        error: action.payload,
        expired: action.expired,
      }
    case 'SET_PROMPT':
      return { ...state, promptText: action.payload }
    case 'SET_DRAWER':
      return { ...state, drawerOpen: action.payload }
    case 'TOGGLE_DRAWER':
      return { ...state, drawerOpen: !state.drawerOpen }
    case 'CLEAR_ERROR':
      return { ...state, error: null }
    default:
      return state
  }
}

const VIBE_STORAGE_PREFIX = 'kipina-vibe-'

function storageKey(sessionId: string) {
  return VIBE_STORAGE_PREFIX + sessionId
}

function loadStoredSession(sessionId: string): StoredVibeSession | null {
  try {
    const raw = sessionStorage.getItem(storageKey(sessionId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<StoredVibeSession>
    if (!parsed.sandboxId || !parsed.prototypeHtml) return null
    return {
      sandboxId: parsed.sandboxId,
      prototypeHtml: parsed.prototypeHtml,
      mestariMessage: parsed.mestariMessage ?? '',
      iterationCount: parsed.iterationCount ?? 0,
    }
  } catch {
    return null
  }
}

function saveStoredSession(sessionId: string, session: StoredVibeSession) {
  sessionStorage.setItem(storageKey(sessionId), JSON.stringify(session))
}

function errorMessage(error: unknown) {
  if (error instanceof Error) return error.message
  return 'network_error'
}

export function useVibeSession(sessionId: string, language: Lang) {
  const [state, dispatch] = useReducer(reducer, sessionId, initialState)

  useEffect(() => {
    const stored = loadStoredSession(sessionId)
    if (stored) {
      dispatch({ type: 'RESTORE', payload: stored })
    }
  }, [sessionId])

  const startSession = useCallback(
    async (concept: string, report: string, tenantId: string) => {
      dispatch({ type: 'START_BEGIN' })
      try {
        const response = await startPrototype({
          concept,
          report,
          tenantId,
          sessionId,
        })
        dispatch({ type: 'START_SUCCESS', payload: response })
        saveStoredSession(sessionId, {
          sandboxId: response.sandbox_id,
          prototypeHtml: response.prototype_html,
          mestariMessage: response.mestari_message,
          iterationCount: 0,
        })
      } catch (error) {
        dispatch({ type: 'START_ERROR', payload: errorMessage(error) })
      }
    },
    [sessionId]
  )

  const iterate = useCallback(
    async (input: string) => {
      const trimmed = input.trim()
      if (!state.sandboxId || !trimmed || state.isLoading) return
      dispatch({ type: 'ITERATE_BEGIN' })
      try {
        const response = await iteratePrototype({
          sandboxId: state.sandboxId,
          mode: 'koodaus',
          userInput: trimmed,
          language,
        })
        dispatch({ type: 'ITERATE_SUCCESS', payload: response })
        saveStoredSession(sessionId, {
          sandboxId: state.sandboxId,
          prototypeHtml: response.prototype_html ?? state.prototypeHtml,
          mestariMessage: response.mestari_message,
          iterationCount: response.iteration_count,
        })
      } catch (error) {
        const expired =
          (error as VibeApiError).status === 404 ||
          errorMessage(error) === 'sandbox_not_found'
        dispatch({
          type: 'ITERATE_ERROR',
          payload: errorMessage(error),
          expired,
        })
      }
    },
    [language, sessionId, state.isLoading, state.prototypeHtml, state.sandboxId]
  )

  const setPromptText = useCallback((text: string) => {
    dispatch({ type: 'SET_PROMPT', payload: text })
  }, [])

  const setDrawerOpen = useCallback((open: boolean) => {
    dispatch({ type: 'SET_DRAWER', payload: open })
  }, [])

  const toggleDrawer = useCallback(() => {
    dispatch({ type: 'TOGGLE_DRAWER' })
  }, [])

  const clearError = useCallback(() => {
    dispatch({ type: 'CLEAR_ERROR' })
  }, [])

  return {
    state,
    startSession,
    iterate,
    setPromptText,
    setDrawerOpen,
    toggleDrawer,
    clearError,
  }
}
