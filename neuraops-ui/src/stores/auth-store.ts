/**
 * NeuraOps Authentication Store (Next.js 14)
 * Zustand store for user authentication state
 * Modern implementation with proper typing
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, LoginRequest } from '@/types'
import { apiService } from '@/services/api'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
}

interface AuthActions {
  login: (credentials: LoginRequest) => Promise<void>
  logout: () => Promise<void>
  getCurrentUser: () => Promise<void>
  clearError: () => void
  setLoading: (loading: boolean) => void
}

type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      // State
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: async (credentials: LoginRequest) => {
        try {
          set({ isLoading: true, error: null })
          
          // Always use the real API, even in development mode
          // This ensures we get a proper JWT token for CLI authentication
          const response = await apiService.login(credentials)
          
          // Handle the real API response structure
          if (response.data?.user && response.data?.token) {
            // Make sure apiService uses the new token
            apiService.refreshAuth()
            
            // Convert API user to our User type
            const user: User = {
              id: response.data.user.id,
              username: response.data.user.username,
              email: response.data.user.email,
              role: response.data.user.role as 'admin' | 'user' | 'viewer',
              permissions: response.data.user.role === 'admin' ? ['*'] : [],
              lastLogin: new Date(),
              isActive: true,
              createdAt: new Date(),
              updatedAt: new Date()
            }
            
            set({ 
              user,
              isAuthenticated: true,
              isLoading: false
            })
          } else {
            throw new Error('Invalid login response')
          }
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Login failed',
            isLoading: false,
            isAuthenticated: false,
            user: null
          })
          throw error
        }
      },

      logout: async () => {
        try {
          set({ isLoading: true })
          await apiService.logout()
        } catch (error) {
          console.error('Logout error:', error)
        } finally {
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null
          })
        }
      },

      getCurrentUser: async () => {
        try {
          set({ isLoading: true, error: null })
          const user = await apiService.getCurrentUser()
          set({ 
            user,
            isAuthenticated: true,
            isLoading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to get user',
            isLoading: false,
            isAuthenticated: false,
            user: null
          })
        }
      },

      clearError: () => {
        set({ error: null })
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      }
    }),
    {
      name: 'neuraops-auth',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated
      })
    }
  )
)