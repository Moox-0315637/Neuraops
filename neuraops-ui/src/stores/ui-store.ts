/**
 * NeuraOps UI Store (Next.js 14)
 * Global UI state management - sidebar, theme, notifications, etc.
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Theme = 'light' | 'dark' | 'auto'
export type NotificationType = 'success' | 'error' | 'warning' | 'info'

export interface Notification {
  id: string
  type: NotificationType
  title: string
  message?: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
  createdAt: Date
}

interface UiState {
  // Sidebar
  sidebarCollapsed: boolean
  sidebarMobileOpen: boolean
  
  // Theme
  theme: Theme
  
  // Navigation
  currentPage: string
  breadcrumbs: Array<{ label: string; href?: string }>
  
  // Notifications
  notifications: Notification[]
  
  // Loading states
  globalLoading: boolean
  
  // Modals and dialogs
  modals: Record<string, boolean>
  
  // Search
  globalSearchOpen: boolean
  globalSearchQuery: string
}

interface UiActions {
  // Sidebar actions
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebarMobile: () => void
  setSidebarMobileOpen: (open: boolean) => void
  
  // Theme actions
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  
  // Navigation actions
  setCurrentPage: (page: string) => void
  setBreadcrumbs: (breadcrumbs: Array<{ label: string; href?: string }>) => void
  
  // Notification actions
  addNotification: (notification: Omit<Notification, 'id' | 'createdAt'>) => string
  removeNotification: (id: string) => void
  clearNotifications: () => void
  
  // Loading actions
  setGlobalLoading: (loading: boolean) => void
  
  // Modal actions
  openModal: (modalId: string) => void
  closeModal: (modalId: string) => void
  toggleModal: (modalId: string) => void
  
  // Search actions
  setGlobalSearchOpen: (open: boolean) => void
  setGlobalSearchQuery: (query: string) => void
  
  // Utility actions
  showSuccessNotification: (message: string, title?: string) => void
  showErrorNotification: (message: string, title?: string) => void
  showWarningNotification: (message: string, title?: string) => void
  showInfoNotification: (message: string, title?: string) => void
}

type UiStore = UiState & UiActions

export const useUiStore = create<UiStore>()(
  persist(
    (set, get) => ({
      // State
      sidebarCollapsed: false,
      sidebarMobileOpen: false,
      theme: 'dark',
      currentPage: 'dashboard',
      breadcrumbs: [{ label: 'Dashboard' }],
      notifications: [],
      globalLoading: false,
      modals: {},
      globalSearchOpen: false,
      globalSearchQuery: '',

      // Sidebar actions
      toggleSidebar: () => {
        set(state => ({ sidebarCollapsed: !state.sidebarCollapsed }))
      },

      setSidebarCollapsed: (collapsed: boolean) => {
        set({ sidebarCollapsed: collapsed })
      },

      toggleSidebarMobile: () => {
        set(state => ({ sidebarMobileOpen: !state.sidebarMobileOpen }))
      },

      setSidebarMobileOpen: (open: boolean) => {
        set({ sidebarMobileOpen: open })
      },

      // Theme actions
      setTheme: (theme: Theme) => {
        set({ theme })
        
        // Update document class for theme
        if (typeof document !== 'undefined') {
          const root = document.documentElement
          root.classList.remove('light', 'dark')
          
          if (theme === 'auto') {
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
            root.classList.add(prefersDark ? 'dark' : 'light')
          } else {
            root.classList.add(theme)
          }
        }
      },

      toggleTheme: () => {
        const currentTheme = get().theme
        const newTheme = currentTheme === 'light' ? 'dark' : 'light'
        get().setTheme(newTheme)
      },

      // Navigation actions
      setCurrentPage: (page: string) => {
        set({ currentPage: page })
      },

      setBreadcrumbs: (breadcrumbs: Array<{ label: string; href?: string }>) => {
        set({ breadcrumbs })
      },

      // Notification actions
      addNotification: (notificationData: Omit<Notification, 'id' | 'createdAt'>) => {
        const id = Math.random().toString(36).substring(2, 15)
        const notification: Notification = {
          ...notificationData,
          id,
          createdAt: new Date()
        }

        set(state => ({
          notifications: [...state.notifications, notification]
        }))

        // Auto-remove notification after duration
        if (notification.duration !== 0) {
          const duration = notification.duration ?? 5000
          setTimeout(() => {
            get().removeNotification(id)
          }, duration)
        }

        return id
      },

      removeNotification: (id: string) => {
        set(state => ({
          notifications: state.notifications.filter(n => n.id !== id)
        }))
      },

      clearNotifications: () => {
        set({ notifications: [] })
      },

      // Loading actions
      setGlobalLoading: (loading: boolean) => {
        set({ globalLoading: loading })
      },

      // Modal actions
      openModal: (modalId: string) => {
        set(state => ({
          modals: { ...state.modals, [modalId]: true }
        }))
      },

      closeModal: (modalId: string) => {
        set(state => ({
          modals: { ...state.modals, [modalId]: false }
        }))
      },

      toggleModal: (modalId: string) => {
        set(state => ({
          modals: { ...state.modals, [modalId]: !state.modals[modalId] }
        }))
      },

      // Search actions
      setGlobalSearchOpen: (open: boolean) => {
        set({ globalSearchOpen: open })
      },

      setGlobalSearchQuery: (query: string) => {
        set({ globalSearchQuery: query })
      },

      // Utility notification methods
      showSuccessNotification: (message: string, title = 'Success') => {
        get().addNotification({
          type: 'success',
          title,
          message,
          duration: 4000
        })
      },

      showErrorNotification: (message: string, title = 'Error') => {
        get().addNotification({
          type: 'error',
          title,
          message,
          duration: 6000
        })
      },

      showWarningNotification: (message: string, title = 'Warning') => {
        get().addNotification({
          type: 'warning',
          title,
          message,
          duration: 5000
        })
      },

      showInfoNotification: (message: string, title = 'Info') => {
        get().addNotification({
          type: 'info',
          title,
          message,
          duration: 4000
        })
      }
    }),
    {
      name: 'neuraops-ui',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
        currentPage: state.currentPage
      })
    }
  )
)