/**
 * NeuraOps API Service (Next.js 14)
 * Centralized API client for all backend communications
 * Modern implementation with proper error handling and types
 */
import type { 
  Agent, 
  Workflow, 
  WorkflowStep,
  WorkflowExecution,
  Command, 
  LogEntry, 
  SystemMetrics, 
  Alert,
  User,
  LoginRequest,
  LoginResponse,
  DocSection,
  DocTemplate,
  DocQuickLink
} from '@/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

/**
 * API Error class for better error handling
 */
class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * Main API Service Class
 */
class ApiService {
  private readonly baseUrl: string
  private token: string | null = null

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl
    this.initializeAuth()
  }

  /**
   * Initialize authentication tokens (JWT only)
   */
  private initializeAuth() {
    // Try localStorage first, then fall back to cookies
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('neuraops_auth_token') ?? this.getCookieValue('neuraops_auth_token')
    }
    // No API key needed - we only use JWT authentication
  }

  /**
   * Get cookie value by name
   */
  private getCookieValue(name: string): string | null {
    if (typeof window === 'undefined') return null
    const value = `; ${document.cookie}`
    const parts = value.split(`; ${name}=`)
    if (parts.length === 2) {
      const cookieValue = parts.pop()?.split(';').shift()
      return cookieValue || null
    }
    return null
  }

  /**
   * Re-initialize authentication (useful after token updates)
   */
  public refreshAuth() {
    this.initializeAuth()
  }

  /**
   * Generic HTTP request method with proper error handling
   */
  public async request<T>(
    endpoint: string, 
    options: RequestInit = {},
    timeoutMs?: number
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>)
    }

    // Add JWT authentication header
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`
    }

    try {
      // Create abort controller for timeout
      const controller = new AbortController()
      let timeoutId: NodeJS.Timeout | undefined
      
      if (timeoutMs) {
        timeoutId = setTimeout(() => controller.abort(), timeoutMs)
      }

      const response = await fetch(url, {
        ...options,
        headers,
        signal: controller.signal
      })
      
      if (timeoutId) {
        clearTimeout(timeoutId)
      }

      // Handle non-JSON responses
      const contentType = response.headers.get('content-type')
      const isJson = contentType?.includes('application/json')

      if (!response.ok) {
        let errorMessage = response.statusText
        let errorCode: string | undefined

        if (isJson) {
          try {
            const errorData = await response.json()
            errorMessage = errorData.message ?? response.statusText
            errorCode = errorData.code
          } catch {
            // If JSON parsing fails, use statusText
            errorMessage = response.statusText
          }
        }

        // Handle authentication errors specifically
        if (response.status === 401) {
          errorMessage = 'Authentication required. Please check your API token.'
        } else if (response.status === 403) {
          errorMessage = 'Access forbidden. Please verify your API token has the required permissions.'
        }

        throw new ApiError(
          errorMessage,
          response.status,
          errorCode
        )
      }

      // Handle empty responses
      if (response.status === 204) {
        return {} as T
      }

      return isJson ? await response.json() : response.text() as T
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }
      
      // Handle abort errors (timeout)
      if (error instanceof Error && error.name === 'AbortError') {
        throw new ApiError(
          `Request timed out after ${timeoutMs ? timeoutMs / 1000 : '?'} seconds`,
          408
        )
      }
      
      // Network errors, CORS issues, etc.
      throw new ApiError(
        error instanceof Error ? error.message : 'Network error',
        0
      )
    }
  }

  /**
   * Set JWT authentication token in both localStorage and cookie
   */
  setToken(token: string | null) {
    this.token = token
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('neuraops_auth_token', token)
        // Also set as httpOnly-like cookie for middleware access
        document.cookie = `neuraops_auth_token=${token}; path=/; max-age=86400; SameSite=Lax`
      } else {
        localStorage.removeItem('neuraops_auth_token')
        // Also clean up any old token keys
        localStorage.removeItem('neuraops_token')
        localStorage.removeItem('neuraops_api_key')
        // Clear the auth cookie
        document.cookie = 'neuraops_auth_token=; path=/; max-age=0; SameSite=Lax'
      }
    }
  }

  /**
   * Get current token (for debugging/status checks)
   */
  getCurrentToken(): string | null {
    return this.token
  }

  /**
   * Check if API is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.token
  }

  // Authentication API
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials)
    })
    
    // Handle the nested token structure from NeuraOps API
    if (response.data?.token) {
      this.setToken(response.data.token)
    }
    
    return response
  }

  async logout(): Promise<void> {
    await this.request('/api/auth/logout', { method: 'POST' })
    this.setToken(null)
  }

  async getCurrentUser(): Promise<User> {
    return this.request<User>('/api/auth/me')
  }

  async refreshToken(): Promise<LoginResponse> {
    const response = await this.request<LoginResponse>('/api/auth/refresh', {
      method: 'POST'
    })
    
    // Handle the nested token structure from NeuraOps API
    if (response.data?.token) {
      this.setToken(response.data.token)
    }
    
    return response
  }

  // Agents API
  async getAgents(): Promise<Agent[]> {
    const response = await this.request<{ status: string; data: any[] }>('/api/agents/')
    
    // Transform API response to match UI Agent interface
    return response.data.map((agent: any) => ({
      id: agent.agent_id,
      name: agent.agent_name,
      status: agent.status,
      hostname: agent.hostname,
      capabilities: agent.capabilities || [],
      location: agent.location || '',
      version: agent.version,
      lastSeen: agent.last_seen ? new Date(agent.last_seen) : undefined,
      registeredAt: new Date(agent.registered_at || Date.now()),
      tags: agent.capabilities || [], // Map capabilities to tags for UI compatibility
      metadata: agent.metadata || {}
    }))
  }

  async getAgent(id: string): Promise<Agent> {
    const agent = await this.request<any>(`/api/agents/${id}`)
    
    // Transform API response to match UI Agent interface
    return {
      id: agent.agent_id,
      name: agent.agent_name,
      status: agent.status,
      hostname: agent.hostname,
      capabilities: agent.capabilities || [],
      location: agent.location || '',
      version: agent.version,
      lastSeen: agent.last_seen ? new Date(agent.last_seen) : undefined,
      registeredAt: new Date(agent.registered_at || Date.now()),
      tags: agent.capabilities || [], // Map capabilities to tags for UI compatibility
      metadata: agent.metadata || {}
    }
  }

  async createAgent(data: Partial<Agent>): Promise<Agent> {
    return this.request<Agent>('/api/agents', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  async updateAgent(id: string, data: Partial<Agent>): Promise<Agent> {
    return this.request<Agent>(`/api/agents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    })
  }

  async deleteAgent(id: string): Promise<void> {
    return this.request<void>(`/api/agents/${id}`, {
      method: 'DELETE'
    })
  }

  async startAgent(id: string): Promise<void> {
    return this.request<void>(`/api/agents/${id}/start`, {
      method: 'POST'
    })
  }

  async stopAgent(id: string): Promise<void> {
    return this.request<void>(`/api/agents/${id}/stop`, {
      method: 'POST'
    })
  }

  async restartAgent(id: string): Promise<void> {
    return this.request<void>(`/api/agents/${id}/restart`, {
      method: 'POST'
    })
  }

  async getAgentLogs(id: string, limit = 100): Promise<LogEntry[]> {
    return this.request<LogEntry[]>(`/api/agents/${id}/logs?limit=${limit}`)
  }

  async getAgentMetrics(id: string): Promise<SystemMetrics> {
    return this.request<SystemMetrics>(`/api/agents/${id}/metrics`)
  }

  // Workflows API
  async getWorkflows(): Promise<Workflow[]> {
    const response = await this.request<{ status: string; data: { workflows: Workflow[] } }>('/api/workflows')
    return response.data.workflows
  }

  async getWorkflow(id: string): Promise<Workflow> {
    return this.request<Workflow>(`/workflows/${id}`)
  }

  async createWorkflow(data: Partial<Workflow>): Promise<Workflow> {
    return this.request<Workflow>('/api/workflows', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  async updateWorkflow(id: string, data: Partial<Workflow>): Promise<Workflow> {
    return this.request<Workflow>(`/workflows/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    })
  }

  async deleteWorkflow(id: string): Promise<void> {
    return this.request<void>(`/workflows/${id}`, {
      method: 'DELETE'
    })
  }

  async executeWorkflow(id: string, inputs: Record<string, unknown> = {}): Promise<WorkflowExecution> {
    return this.request<WorkflowExecution>(`/workflows/${id}/execute`, {
      method: 'POST',
      body: JSON.stringify({ inputs })
    })
  }

  // Workflow Steps API
  async addWorkflowStep(workflowId: string, step: Partial<WorkflowStep>): Promise<Workflow> {
    return this.request<Workflow>(`/workflows/${workflowId}/steps`, {
      method: 'POST',
      body: JSON.stringify(step)
    })
  }

  async updateWorkflowStep(workflowId: string, stepId: string, data: Partial<WorkflowStep>): Promise<Workflow> {
    return this.request<Workflow>(`/workflows/${workflowId}/steps/${stepId}`, {
      method: 'PUT',
      body: JSON.stringify(data)
    })
  }

  async removeWorkflowStep(workflowId: string, stepId: string): Promise<Workflow> {
    return this.request<Workflow>(`/workflows/${workflowId}/steps/${stepId}`, {
      method: 'DELETE'
    })
  }

  async reorderWorkflowSteps(workflowId: string, stepIds: string[]): Promise<Workflow> {
    return this.request<Workflow>(`/workflows/${workflowId}/steps/reorder`, {
      method: 'POST',
      body: JSON.stringify({ stepIds })
    })
  }

  // Workflow Executions API
  async getWorkflowExecutions(workflowId?: string): Promise<WorkflowExecution[]> {
    const url = workflowId ? `/api/workflows/executions?workflow_id=${workflowId}` : '/api/workflows/executions'
    const response = await this.request<{ status: string; data: WorkflowExecution[] }>(url)
    return response.data
  }

  async getWorkflowExecution(executionId: string): Promise<WorkflowExecution> {
    const response = await this.request<{ status: string; data: WorkflowExecution }>(`/api/workflows/executions/${executionId}`)
    return response.data
  }

  async stopWorkflowExecution(executionId: string): Promise<void> {
    await this.request<void>(`/api/workflows/executions/${executionId}/stop`, {
      method: 'POST'
    })
  }

  // Commands API
  async executeCommand(agentId: string, command: string): Promise<Command> {
    return this.request<Command>('/api/commands', {
      method: 'POST',
      body: JSON.stringify({ agentId, command })
    })
  }

  async getCommand(id: string): Promise<Command> {
    return this.request<Command>(`/api/commands/${id}`)
  }

  async getCommands(agentId?: string, limit = 50): Promise<Command[]> {
    const url = agentId ? `/api/commands?agentId=${agentId}&limit=${limit}` : `/api/commands?limit=${limit}`
    const response = await this.request<{ status: string; data: Command[] }>(url)
    return response.data
  }

  // System API
  async getSystemMetrics(): Promise<SystemMetrics> {
    return this.request<SystemMetrics>('/api/system/metrics')
  }

  async getAlerts(severity?: string): Promise<Alert[]> {
    const url = severity ? `/api/alerts?severity=${severity}` : '/api/alerts'
    const response = await this.request<{ status: string; data: Alert[] }>(url)
    return response.data
  }

  // Documentation API (without auth for now)

  async acknowledgeAlert(id: string): Promise<void> {
    return this.request<void>(`/api/alerts/${id}/acknowledge`, {
      method: 'POST'
    })
  }

  async getLogs(level?: string, limit = 100): Promise<LogEntry[]> {
    const url = level ? `/api/logs?level=${level}&limit=${limit}` : `/api/logs?limit=${limit}`
    return this.request<LogEntry[]>(url)
  }

  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    const response = await this.request<{ status: string; data: any }>('/api/health')
    return { 
      status: response.data.status ?? response.status, 
      timestamp: response.data.timestamp 
    }
  }

  // CLI command execution
  async executeCLICommand(command: string, args: string[] = [], timeout: number = 300): Promise<any> {
    return this.request<any>('/api/cli/execute', {
      method: 'POST',
      body: JSON.stringify({
        command,
        args,
        timeout
      })
    })
  }

  // Documentation & Templates API
  async getDocumentationSections(): Promise<DocSection[]> {
    try {
      const response = await this.request<{ data: DocSection[] }>('/api/documentation/sections')
      return response.data
    } catch (error) {
      // Fallback: return empty array if endpoints not yet deployed
      console.warn('Documentation endpoints not yet available on production API:', error)
      return []
    }
  }

  async getDocumentationTemplate(templateId: string): Promise<DocTemplate | null> {
    try {
      const sections = await this.getDocumentationSections()
      for (const section of sections) {
        const template = section.templates.find(t => t.id === templateId)
        if (template) return template
      }
      return null
    } catch (error) {
      console.warn('Documentation template not available:', error)
      return null
    }
  }

  async getQuickLinks(): Promise<DocQuickLink[]> {
    try {
      const response = await this.request<{ data: DocQuickLink[] }>('/api/documentation/quick-links')
      return response.data
    } catch (error) {
      // Fallback: return empty array if endpoints not yet deployed
      console.warn('Quick links endpoints not yet available on production API:', error)
      return []
    }
  }

  // Template Management API
  async getFilesystemTemplates(): Promise<any[]> {
    try {
      const response = await this.request<{ data: any[] }>('/api/documentation/templates/filesystem')
      return response.data
    } catch (error) {
      console.warn('Filesystem templates endpoint not available:', error)
      return []
    }
  }

  async getAllTemplates(): Promise<{ configured_templates: any[], filesystem_templates: any[] }> {
    try {
      const response = await this.request<{ 
        data: { 
          configured_templates: any[], 
          filesystem_templates: any[] 
        } 
      }>('/api/documentation/templates/all')
      return response.data
    } catch (error) {
      console.warn('All templates endpoint not available:', error)
      return { configured_templates: [], filesystem_templates: [] }
    }
  }

  async uploadTemplate(sectionId: string, filename: string, file: File): Promise<any> {
    try {
      const formData = new FormData()
      formData.append('section_id', sectionId)
      formData.append('filename', filename)
      formData.append('file', file)

      const response = await fetch(`${this.baseUrl}/api/documentation/templates/upload`, {
        method: 'POST',
        headers: {
          ...(this.token && { Authorization: `Bearer ${this.token}` })
        },
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new ApiError(error.detail ?? 'Upload failed', response.status)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Upload failed', 500)
    }
  }

  async deleteTemplate(sectionId: string, filename: string): Promise<any> {
    try {
      return await this.request<any>(`/api/documentation/templates/${sectionId}/${filename}`, {
        method: 'DELETE'
      })
    } catch (error) {
      console.error('Delete template error:', error)
      throw error
    }
  }

  async getTemplateContent(sectionId: string, filename: string): Promise<{ content: string }> {
    try {
      const response = await this.request<{ data: { content: string } }>(`/api/documentation/templates/${sectionId}/${filename}/content`)
      return response.data
    } catch (error) {
      console.error('Get template content error:', error)
      throw error
    }
  }

  async updateTemplateContent(sectionId: string, filename: string, content: string): Promise<any> {
    try {
      return await this.request<any>(`/api/documentation/templates/${sectionId}/${filename}/content`, {
        method: 'PUT',
        body: JSON.stringify({ content })
      })
    } catch (error) {
      console.error('Update template content error:', error)
      throw error
    }
  }

  async updateTemplate(sectionId: string, filename: string, file: File): Promise<any> {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${this.baseUrl}/api/documentation/templates/${sectionId}/${filename}`, {
        method: 'PUT',
        headers: {
          ...(this.token && { Authorization: `Bearer ${this.token}` })
        },
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new ApiError(error.detail ?? 'Update failed', response.status)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Update failed', 500)
    }
  }

  // ===== WORKFLOW TEMPLATES MANAGEMENT =====

  async getWorkflowTemplatesFromFilesystem(): Promise<any[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/workflows/templates/filesystem`, {
        headers: {
          ...(this.token && { Authorization: `Bearer ${this.token}` })
        }
      })

      if (!response.ok) {
        const error = await response.json()
        throw new ApiError(error.detail ?? 'Failed to fetch workflow templates', response.status)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Failed to fetch workflow templates', 500)
    }
  }

  async uploadWorkflowTemplate(sectionId: string, filename: string, file: File): Promise<any> {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch(`${this.baseUrl}/api/workflows/templates/upload?section_id=${encodeURIComponent(sectionId)}&filename=${encodeURIComponent(filename)}`, {
        method: 'POST',
        headers: {
          ...(this.token && { Authorization: `Bearer ${this.token}` })
        },
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new ApiError(error.detail ?? 'Upload failed', response.status)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Upload failed', 500)
    }
  }

  async deleteWorkflowTemplate(sectionId: string, filename: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/workflows/templates/${encodeURIComponent(sectionId)}/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
        headers: {
          ...(this.token && { Authorization: `Bearer ${this.token}` })
        }
      })

      if (!response.ok) {
        const error = await response.json()
        throw new ApiError(error.detail ?? 'Delete failed', response.status)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Delete failed', 500)
    }
  }

  async getWorkflowTemplateContent(sectionId: string, filename: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/workflows/templates/${encodeURIComponent(sectionId)}/${encodeURIComponent(filename)}/content`, {
        headers: {
          ...(this.token && { Authorization: `Bearer ${this.token}` })
        }
      })

      if (!response.ok) {
        const error = await response.json()
        throw new ApiError(error.detail ?? 'Failed to get template content', response.status)
      }

      const result = await response.json()
      return result.data
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Failed to get template content', 500)
    }
  }

  async updateWorkflowTemplateContent(sectionId: string, filename: string, content: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/workflows/templates/${encodeURIComponent(sectionId)}/${encodeURIComponent(filename)}/content`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(this.token && { Authorization: `Bearer ${this.token}` })
        },
        body: JSON.stringify({ content })
      })

      if (!response.ok) {
        const error = await response.json()
        throw new ApiError(error.detail ?? 'Update failed', response.status)
      }

      return await response.json()
    } catch (error) {
      if (error instanceof ApiError) throw error
      throw new ApiError('Update failed', 500)
    }
  }

  // Dashboard specific endpoints
  async getDashboardMetrics(): Promise<{
    activeAgents: number;
    totalAgents: number;
    systemHealth: number;
    aiOperations: number;
    securityScore: number;
  }> {
    try {
      // Try to get comprehensive system metrics
      const [systemMetrics, agents] = await Promise.all([
        this.getSystemMetrics(),
        this.getAgents()
      ])
      
      // Calculate active agents from the array
      const activeAgents = agents.filter(agent => agent.status === 'active').length
      
      return {
        activeAgents: activeAgents,
        totalAgents: agents.length,
        systemHealth: systemMetrics.health_percentage ?? 0,
        aiOperations: systemMetrics.ai_operations_count ?? 0,
        securityScore: systemMetrics.security_score ?? 85
      }
    } catch (error) {
      // If it's an authentication error, rethrow it so autoLogin can detect invalid tokens
      if (error instanceof ApiError && (error.status === 401 || error.status === 403)) {
        throw error
      }
      
      // For other errors (network, etc.), return fallback metrics
      console.warn('Failed to fetch dashboard metrics, using fallback:', error)
      return {
        activeAgents: 0,
        totalAgents: 0,
        systemHealth: 0,
        aiOperations: 0,
        securityScore: 0
      }
    }
  }
}

// Export singleton instance
export const apiService = new ApiService()

// Export class for testing or multiple instances
export { ApiService, ApiError }