/**
 * NeuraOps Workflow Store (Next.js 14)
 * Zustand store for workflow management
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Workflow, WorkflowStep, WorkflowExecution, WorkflowStatus } from '@/types'
import { apiService } from '@/services/api'

interface WorkflowState {
  workflows: Workflow[]
  executions: WorkflowExecution[]
  selectedWorkflow: Workflow | null
  selectedExecution: WorkflowExecution | null
  isLoading: boolean
  error: string | null
}

interface WorkflowActions {
  // Workflow CRUD
  fetchWorkflows: () => Promise<void>
  fetchWorkflow: (id: string) => Promise<void>
  createWorkflow: (data: Partial<Workflow>) => Promise<void>
  updateWorkflow: (id: string, data: Partial<Workflow>) => Promise<void>
  deleteWorkflow: (id: string) => Promise<void>
  
  // Workflow execution
  executeWorkflow: (id: string, inputs?: Record<string, unknown>) => Promise<void>
  stopExecution: (executionId: string) => Promise<void>
  fetchExecutions: (workflowId?: string) => Promise<void>
  fetchExecution: (executionId: string) => Promise<void>
  
  // UI state management
  selectWorkflow: (workflow: Workflow | null) => void
  selectExecution: (execution: WorkflowExecution | null) => void
  clearError: () => void
  
  // Workflow building helpers
  addStep: (workflowId: string, step: Partial<WorkflowStep>) => Promise<void>
  updateStep: (workflowId: string, stepId: string, data: Partial<WorkflowStep>) => Promise<void>
  removeStep: (workflowId: string, stepId: string) => Promise<void>
  reorderSteps: (workflowId: string, stepIds: string[]) => Promise<void>
  
  // Statistics
  getWorkflowStats: () => {
    total: number
    active: number
    draft: number
    executed: number
  }
}

type WorkflowStore = WorkflowState & WorkflowActions

export const useWorkflowStore = create<WorkflowStore>()(
  persist(
    (set, get) => ({
      // State
      workflows: [],
      executions: [],
      selectedWorkflow: null,
      selectedExecution: null,
      isLoading: false,
      error: null,

      // Workflow CRUD
      fetchWorkflows: async () => {
        try {
          set({ isLoading: true, error: null })
          const workflows = await apiService.getWorkflows()
          set({ workflows, isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch workflows',
            isLoading: false
          })
        }
      },

      fetchWorkflow: async (id: string) => {
        try {
          set({ isLoading: true, error: null })
          const workflow = await apiService.getWorkflow(id)
          set({
            selectedWorkflow: workflow,
            isLoading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch workflow',
            isLoading: false
          })
        }
      },

      createWorkflow: async (data: Partial<Workflow>) => {
        try {
          set({ isLoading: true, error: null })
          const newWorkflow = await apiService.createWorkflow(data)
          set(state => ({
            workflows: [...state.workflows, newWorkflow],
            isLoading: false
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to create workflow',
            isLoading: false
          })
          throw error
        }
      },

      updateWorkflow: async (id: string, data: Partial<Workflow>) => {
        try {
          set({ isLoading: true, error: null })
          const updatedWorkflow = await apiService.updateWorkflow(id, data)
          set(state => ({
            workflows: state.workflows.map(w => w.id === id ? updatedWorkflow : w),
            selectedWorkflow: state.selectedWorkflow?.id === id ? updatedWorkflow : state.selectedWorkflow,
            isLoading: false
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to update workflow',
            isLoading: false
          })
          throw error
        }
      },

      deleteWorkflow: async (id: string) => {
        try {
          set({ isLoading: true, error: null })
          await apiService.deleteWorkflow(id)
          set(state => ({
            workflows: state.workflows.filter(w => w.id !== id),
            selectedWorkflow: state.selectedWorkflow?.id === id ? null : state.selectedWorkflow,
            isLoading: false
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to delete workflow',
            isLoading: false
          })
          throw error
        }
      },

      // Workflow execution
      executeWorkflow: async (id: string, inputs = {}) => {
        try {
          set({ isLoading: true, error: null })
          const execution = await apiService.executeWorkflow(id, inputs)
          set(state => ({
            executions: [execution, ...state.executions],
            selectedExecution: execution,
            isLoading: false
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to execute workflow',
            isLoading: false
          })
          throw error
        }
      },

      stopExecution: async (executionId: string) => {
        try {
          await apiService.stopWorkflowExecution(executionId)
          set(state => ({
            executions: state.executions.map(ex =>
              ex.id === executionId 
                ? { ...ex, status: 'cancelled' as WorkflowStatus, endTime: new Date() }
                : ex
            )
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to stop execution'
          })
          throw error
        }
      },

      fetchExecutions: async (workflowId?: string) => {
        try {
          set({ isLoading: true, error: null })
          const executions = await apiService.getWorkflowExecutions(workflowId)
          set({ executions, isLoading: false })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch executions',
            isLoading: false
          })
        }
      },

      fetchExecution: async (executionId: string) => {
        try {
          set({ isLoading: true, error: null })
          const execution = await apiService.getWorkflowExecution(executionId)
          set({
            selectedExecution: execution,
            isLoading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to fetch execution',
            isLoading: false
          })
        }
      },

      // UI state management
      selectWorkflow: (workflow: Workflow | null) => {
        set({ selectedWorkflow: workflow })
      },

      selectExecution: (execution: WorkflowExecution | null) => {
        set({ selectedExecution: execution })
      },

      clearError: () => {
        set({ error: null })
      },

      // Workflow building helpers
      addStep: async (workflowId: string, step: Partial<WorkflowStep>) => {
        try {
          const updatedWorkflow = await apiService.addWorkflowStep(workflowId, step)
          set(state => ({
            workflows: state.workflows.map(w => w.id === workflowId ? updatedWorkflow : w),
            selectedWorkflow: state.selectedWorkflow?.id === workflowId ? updatedWorkflow : state.selectedWorkflow
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to add step'
          })
          throw error
        }
      },

      updateStep: async (workflowId: string, stepId: string, data: Partial<WorkflowStep>) => {
        try {
          const updatedWorkflow = await apiService.updateWorkflowStep(workflowId, stepId, data)
          set(state => ({
            workflows: state.workflows.map(w => w.id === workflowId ? updatedWorkflow : w),
            selectedWorkflow: state.selectedWorkflow?.id === workflowId ? updatedWorkflow : state.selectedWorkflow
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to update step'
          })
          throw error
        }
      },

      removeStep: async (workflowId: string, stepId: string) => {
        try {
          const updatedWorkflow = await apiService.removeWorkflowStep(workflowId, stepId)
          set(state => ({
            workflows: state.workflows.map(w => w.id === workflowId ? updatedWorkflow : w),
            selectedWorkflow: state.selectedWorkflow?.id === workflowId ? updatedWorkflow : state.selectedWorkflow
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to remove step'
          })
          throw error
        }
      },

      reorderSteps: async (workflowId: string, stepIds: string[]) => {
        try {
          const updatedWorkflow = await apiService.reorderWorkflowSteps(workflowId, stepIds)
          set(state => ({
            workflows: state.workflows.map(w => w.id === workflowId ? updatedWorkflow : w),
            selectedWorkflow: state.selectedWorkflow?.id === workflowId ? updatedWorkflow : state.selectedWorkflow
          }))
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to reorder steps'
          })
          throw error
        }
      },

      // Statistics
      getWorkflowStats: () => {
        const workflows = get().workflows ?? []
        return {
          total: workflows.length,
          active: workflows.filter(w => w.status === 'active').length,
          draft: workflows.filter(w => w.status === 'draft').length,
          executed: workflows.filter(w => w.executionCount > 0).length
        }
      }
    }),
    {
      name: 'neuraops-workflows',
      partialize: (state) => ({
        selectedWorkflow: state.selectedWorkflow,
        selectedExecution: state.selectedExecution
      })
    }
  )
)