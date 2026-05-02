import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from '@tanstack/react-router'
import { I18nProvider } from '@/lib/i18n'
import { AuthProvider } from '@/lib/auth'
import { router } from '@/router'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: 0,
    },
  },
})

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <AuthProvider>
          <RouterProvider router={router} />
        </AuthProvider>
      </I18nProvider>
    </QueryClientProvider>
  )
}
