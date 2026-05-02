import {
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
  redirect,
} from '@tanstack/react-router'
import { LoginPage } from '@/pages/Login'
import { HomePage } from '@/pages/Home'
import { IdeaPage } from '@/pages/Idea'
import { ConceptPage } from '@/pages/Concept'
import { PrototypePage } from '@/pages/Prototype'

const STORAGE_KEY = 'kipina_auth_ok'

function isAuthed(): boolean {
  if (typeof window === 'undefined') return false
  return window.sessionStorage.getItem(STORAGE_KEY) === '1'
}

const rootRoute = createRootRoute({
  component: () => <Outlet />,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: LoginPage,
  beforeLoad: () => {
    if (isAuthed()) {
      throw redirect({ to: '/koti' })
    }
  },
})

const protectedRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'protected',
  beforeLoad: () => {
    if (!isAuthed()) {
      throw redirect({ to: '/' })
    }
  },
  component: () => <Outlet />,
})

const homeRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: '/koti',
  component: HomePage,
})

const ideaRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: '/idea/$tenantId',
  component: IdeaPage,
})

const conceptRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: '/konsepti/$id',
  component: ConceptPage,
})

const prototypeRoute = createRoute({
  getParentRoute: () => protectedRoute,
  path: '/proto/$id',
  component: PrototypePage,
})

const routeTree = rootRoute.addChildren([
  loginRoute,
  protectedRoute.addChildren([homeRoute, ideaRoute, conceptRoute, prototypeRoute]),
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
