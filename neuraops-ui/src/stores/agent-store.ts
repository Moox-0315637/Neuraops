/**
 * NeuraOps Agent Store (Next.js 14)
 * Zustand store for agent management
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Agent, AgentStatus } from '@/types'
import { apiService } from '@/services/api'

interface AgentState {
  agents: Agent[]
  selectedAgent: Agent | null
  isLoading: boolean
  error: string | null
  searchQuery: string
  statusFilter: AgentStatus | 'all'
}

interface AgentActions {
  // Fetch actions
  fetchAgents: () => Promise<void>
  fetchAgent: (id: string) => Promise<void>
  
  // Agent management
  createAgent: (data: Partial<Agent>) => Promise<void>
  updateAgent: (id: string, data: Partial<Agent>) => Promise<void>
  deleteAgent: (id: string) => Promise<void>
  
  // Agent controls
  startAgent: (id: string) => Promise<void>
  stopAgent: (id: string) => Promise<void>
  restartAgent: (id: string) => Promise<void>
  
  // UI state
  selectAgent: (agent: Agent | null) => void
  setSearchQuery: (query: string) => void
  setStatusFilter: (status: AgentStatus | 'all') => void
  clearError: () => void
  
  // Computed getters
  getFilteredAgents: () => Agent[]
  getAgentStats: () => {
    total: number
    active: number
    inactive: number
    disconnected: number
    error: number
  }
}

type AgentStore = AgentState & AgentActions

export const useAgentStore = create<AgentStore>()(
  persist(
    (set, get) => ({
      // State
      agents: [],
      selectedAgent: null,
      isLoading: false,
      error: null,
      searchQuery: '',
      statusFilter: 'all',

      // Fetch actions
      fetchAgents: async () => {
        try {
          set({ isLoading: true, error: null })
          const agents = await apiService.getAgents()
          set({ agents, isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch agents',
            isLoading: false
          })
        }
      },

      fetchAgent: async (id: string) => {
        try {
          set({ isLoading: true, error: null })
          const agent = await apiService.getAgent(id)
          set({ 
            selectedAgent: agent,
            isLoading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch agent',
            isLoading: false
          })
        }
      },

      // Agent management
      createAgent: async (data: Partial<Agent>) => {
        try {
          set({ isLoading: true, error: null })
          const newAgent = await apiService.createAgent(data)
          set(state => ({
            agents: [...state.agents, newAgent],
            isLoading: false
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to create agent',
            isLoading: false
          })
          throw error
        }
      },

      updateAgent: async (id: string, data: Partial<Agent>) => {
        try {
          set({ isLoading: true, error: null })
          const updatedAgent = await apiService.updateAgent(id, data)
          set(state => ({
            agents: state.agents.map(agent => 
              agent.id === id ? updatedAgent : agent
            ),
            selectedAgent: state.selectedAgent?.id === id ? updatedAgent : state.selectedAgent,
            isLoading: false
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to update agent',
            isLoading: false
          })
          throw error
        }
      },

      deleteAgent: async (id: string) => {
        try {
          set({ isLoading: true, error: null })
          await apiService.deleteAgent(id)
          set(state => ({
            agents: state.agents.filter(agent => agent.id !== id),
            selectedAgent: state.selectedAgent?.id === id ? null : state.selectedAgent,
            isLoading: false
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to delete agent',
            isLoading: false
          })
          throw error
        }
      },

      // Agent controls
      startAgent: async (id: string) => {
        try {
          await apiService.startAgent(id)
          const state = get()
          state.updateAgent(id, { status: 'active' as AgentStatus })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to start agent'
          })
          throw error
        }
      },

      stopAgent: async (id: string) => {
        try {
          await apiService.stopAgent(id)
          const state = get()
          state.updateAgent(id, { status: 'inactive' as AgentStatus })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to stop agent'
          })
          throw error
        }
      },

      restartAgent: async (id: string) => {
        try {
          await apiService.restartAgent(id)
          const state = get()
          state.fetchAgent(id) // Refresh agent data
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to restart agent'
          })
          throw error
        }
      },

      // UI state
      selectAgent: (agent: Agent | null) => {
        set({ selectedAgent: agent })
      },

      setSearchQuery: (query: string) => {
        set({ searchQuery: query })
      },

      setStatusFilter: (status: AgentStatus | 'all') => {
        set({ statusFilter: status })
      },

      clearError: () => {
        set({ error: null })
      },

      // Computed getters
      getFilteredAgents: () => {
        const state = get()
        let filtered = state.agents

        // Filter by search query
        if (state.searchQuery) {
          const query = state.searchQuery.toLowerCase()
          filtered = filtered.filter(agent => {
            const searchFields = [
              agent.name.toLowerCase(),
              agent.hostname.toLowerCase(),
              ...agent.tags.map(tag => tag.toLowerCase())
            ]
            return searchFields.some(field => field.includes(query))
          })
        }

        // Filter by status
        if (state.statusFilter !== 'all') {
          filtered = filtered.filter(agent => agent.status === state.statusFilter)
        }

        return filtered
      },

      getAgentStats: () => {
        const agents = get().agents
        return {
          total: agents.length,
          active: agents.filter(a => a.status === 'active').length,
          inactive: agents.filter(a => a.status === 'inactive').length,
          disconnected: agents.filter(a => a.status === 'disconnected').length,
          error: agents.filter(a => a.status === 'error').length
        }
      }
    }),
    {
      name: 'neuraops-agents',
      partialize: (state) => ({
        selectedAgent: state.selectedAgent,
        searchQuery: state.searchQuery,
        statusFilter: state.statusFilter
      })
    }
  )
)