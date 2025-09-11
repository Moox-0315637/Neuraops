/**
 * NeuraOps Documentation Store (Next.js 14)
 * Zustand store for documentation and templates management
 */
import { create } from 'zustand'
import { apiService } from '@/services/api'
import type { DocSection, DocTemplate, DocQuickLink } from '@/types'

interface DocumentationState {
  sections: DocSection[]
  activeSection: string
  activeTemplate: string | null
  quickLinks: DocQuickLink[]
  isLoading: boolean
  error: string | null
}

interface DocumentationActions {
  // Data fetching
  fetchDocumentation: () => Promise<void>
  fetchQuickLinks: () => Promise<void>
  
  // Navigation
  setActiveSection: (sectionId: string) => void
  setActiveTemplate: (templateId: string) => void
  
  // Template operations
  getTemplateById: (templateId: string) => DocTemplate | null
  getTemplatesBySection: (sectionId: string) => DocTemplate[]
  
  // UI state
  clearError: () => void
}

type DocumentationStore = DocumentationState & DocumentationActions

export const useDocumentationStore = create<DocumentationStore>((set, get) => ({
  // Initial state
  sections: [],
  activeSection: '',
  activeTemplate: null,
  quickLinks: [],
  isLoading: false,
  error: null,

  // Fetch documentation data
  fetchDocumentation: async () => {
    try {
      set({ isLoading: true, error: null })
      
      // Try to fetch from API first
      try {
        const [sections, quickLinks] = await Promise.all([
          apiService.getDocumentationSections(),
          apiService.getQuickLinks()
        ])
        
        // Set default active section and template
        const firstSection = sections[0]
        const firstTemplate = firstSection?.templates[0]
        
        set({
          sections,
          quickLinks,
          activeSection: firstSection?.id ?? '',
          activeTemplate: firstTemplate?.id ?? null,
          isLoading: false
        })
      } catch (apiError) {
        // Fallback to static data if API fails
        console.log('API failed, using static data:', apiError)
        const staticSections = await fetch('/api/documentation/sections')
          .then(res => res.json())
          .then(data => data.data ?? [])
          .catch(() => [])
        
        const staticQuickLinks = await fetch('/api/documentation/quick-links')
          .then(res => res.json())
          .then(data => data.data ?? [])
          .catch(() => [])
        
        const firstSection = staticSections[0]
        const firstTemplate = firstSection?.templates[0]
        
        set({
          sections: staticSections,
          quickLinks: staticQuickLinks,
          activeSection: firstSection?.id ?? '',
          activeTemplate: firstTemplate?.id ?? null,
          isLoading: false,
          error: null
        })
      }
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch documentation',
        isLoading: false
      })
    }
  },

  // Fetch quick links separately
  fetchQuickLinks: async () => {
    try {
      const quickLinks = await apiService.getQuickLinks()
      set({ quickLinks })
    } catch (error) {
      console.warn('Failed to fetch quick links:', error)
      // Don't set error state for quick links failure
    }
  },

  // Set active section and update active template
  setActiveSection: (sectionId: string) => {
    const { sections } = get()
    const section = sections.find(s => s.id === sectionId)
    const firstTemplate = section?.templates[0]
    
    set({
      activeSection: sectionId,
      activeTemplate: firstTemplate?.id ?? null
    })
  },

  // Set active template
  setActiveTemplate: (templateId: string) => {
    set({ activeTemplate: templateId })
  },

  // Get template by ID
  getTemplateById: (templateId: string) => {
    const { sections } = get()
    for (const section of sections) {
      const template = section.templates.find(t => t.id === templateId)
      if (template) return template
    }
    return null
  },

  // Get templates by section
  getTemplatesBySection: (sectionId: string) => {
    const { sections } = get()
    const section = sections.find(s => s.id === sectionId)
    return section?.templates ?? []
  },

  // Clear error state
  clearError: () => {
    set({ error: null })
  }
}))