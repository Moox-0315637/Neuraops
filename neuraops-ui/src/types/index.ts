/**
 * NeuraOps Type Definitions
 * Modern TypeScript interfaces for the application
 */

// Base types
export type Status = 'online' | 'offline' | 'error' | 'maintenance'
export type Severity = 'low' | 'medium' | 'high' | 'critical'
export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected'
export type WorkflowStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

// User & Authentication
export interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'user' | 'viewer'
  permissions: string[]
  avatar?: string
  lastLogin: Date
  isActive: boolean
  createdAt: Date
  updatedAt: Date
}

export interface LoginRequest {
  username: string
  password: string
  rememberMe?: boolean
}

export interface LoginResponse {
  status: string
  message: string
  data: {
    token: string
    expires_in: number
    user: {
      id: string
      username: string
      email: string
      role: string
    }
  }
  error: string | null
  timestamp: string
  execution_time_ms: number | null
  request_id: string | null
}

// Agents - Updated to match NeuraOps Core API
export type AgentStatus = 'active' | 'inactive' | 'disconnected' | 'error'
export type AgentCapability = 'logs' | 'infrastructure' | 'incidents' | 'workflows' | 'health' | 'metrics' | 'commands'

export interface Agent {
  id: string
  name: string
  status: AgentStatus
  hostname: string
  capabilities: AgentCapability[]
  location: string
  version?: string
  lastSeen?: Date
  registeredAt: Date
  tags: string[]
  metadata?: Record<string, unknown>
}

export interface AgentRegistrationRequest {
  agent_name: string
  hostname: string
  capabilities: AgentCapability[]
  api_key: string
  version?: string
  platform?: string
  metadata?: Record<string, unknown>
}

export interface AgentRegistrationResponse {
  agent_id: string
  token: string
  expires_at: Date
  message: string
}

export interface AgentHeartbeat {
  agent_id: string
  status: AgentStatus
  system_info?: Record<string, unknown>
  timestamp: Date
}

export interface AgentMetrics {
  agent_id: string
  timestamp: Date
  system_metrics: {
    cpu_percent: number
    memory_percent: number
    disk_percent: number
    uptime_seconds: number
  }
  performance: {
    commands_executed: number
    success_rate: number
    average_execution_time: number
  }
}

// Workflows
export interface WorkflowStep {
  id: string
  name: string
  type: 'command' | 'script' | 'api' | 'condition'
  config: Record<string, unknown>
  dependsOn?: string[]
  timeout?: number
  retries?: number
}

export interface Workflow {
  id: string
  name: string
  description: string
  status: 'active' | 'draft' | 'paused' | 'archived'
  steps: WorkflowStep[]
  triggers: {
    schedule?: string
    webhook?: string
    manual: boolean
  }
  variables: Record<string, string>
  tags: string[]
  lastRun?: Date
  nextRun?: Date
  runCount: number
  executionCount: number
  successRate: number
  createdBy: string
  createdAt: Date
  updatedAt: Date
}

export interface WorkflowExecution {
  id: string
  workflowId: string
  status: WorkflowStatus
  startedAt: Date
  endTime?: Date
  completedAt?: Date
  duration?: number
  logs: ExecutionLog[]
  result?: unknown
  error?: string
  triggeredBy: string
}

export interface ExecutionLog {
  id: string
  stepId: string
  level: 'debug' | 'info' | 'warn' | 'error'
  message: string
  timestamp: Date
  metadata?: Record<string, unknown>
}

// Commands & CLI
export interface Command {
  id: string
  command: string
  args?: string[]
  env?: Record<string, string>
  cwd?: string
  timeout?: number
  agentId?: string
}

export interface CommandResult {
  id: string
  commandId: string
  exitCode: number
  stdout: string
  stderr: string
  duration: number
  timestamp: Date
}

export interface TerminalSession {
  id: string
  agentId?: string
  isActive: boolean
  history: TerminalEntry[]
  createdAt: Date
}

export interface TerminalEntry {
  id: string
  type: 'input' | 'output' | 'error' | 'system'
  content: string
  timestamp: Date
  metadata?: Record<string, unknown>
}

// System Monitoring
export interface SystemMetrics {
  cpu: {
    usage: number
    cores: number
    load: [number, number, number] // 1m, 5m, 15m
  }
  memory: {
    used: number
    total: number
    percentage: number
  }
  disk: {
    used: number
    total: number
    percentage: number
    iops: {
      read: number
      write: number
    }
  }
  network: {
    bytesIn: number
    bytesOut: number
    packetsIn: number
    packetsOut: number
  }
  timestamp: Date
  // Dashboard specific metrics
  health_percentage?: number
  ai_operations_count?: number
  security_score?: number
}

export interface Alert {
  id: string
  title: string
  message: string
  severity: Severity
  type: 'system' | 'agent' | 'workflow' | 'security'
  source: string
  status: 'open' | 'acknowledged' | 'resolved'
  tags: string[]
  metadata: Record<string, unknown>
  createdAt: Date
  acknowledgedAt?: Date
  acknowledgedBy?: string
  resolvedAt?: Date
  resolvedBy?: string
}

// Log Management
export interface LogEntry {
  id: string
  timestamp: Date
  level: 'debug' | 'info' | 'warn' | 'error' | 'fatal'
  source: string
  message: string
  agentId?: string
  workflowId?: string
  metadata?: Record<string, unknown>
}

export interface LogFilter {
  level?: string[]
  source?: string[]
  timeRange?: {
    start: Date
    end: Date
  }
  search?: string
  agentId?: string
  workflowId?: string
  limit?: number
  offset?: number
}

// API Responses
export interface ApiResponse<T = unknown> {
  success: boolean
  status?: string
  message?: string
  data?: T
  error?: {
    code: string
    message: string
    details?: unknown
  }
  pagination?: {
    page: number
    limit: number
    total: number
    totalPages: number
  }
  meta?: Record<string, unknown>
}

// Agent list response from API
export interface AgentListApiResponse {
  agents: Agent[]
  total_count: number
  active_count: number
}

export interface PaginatedResponse<T> {
  items: T[]
  pagination: {
    page: number
    limit: number
    total: number
    totalPages: number
    hasNext: boolean
    hasPrev: boolean
  }
}

// UI Component Types
export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
  icon?: React.ReactNode
}

export interface TableColumn<T = unknown> {
  key: keyof T | string
  title: string
  width?: string | number
  render?: (value: unknown, record: T, index: number) => React.ReactNode
  sortable?: boolean
  filterable?: boolean
}

export interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

// Settings & Configuration
export interface UserSettings {
  theme: 'light' | 'dark' | 'system'
  language: string
  timezone: string
  notifications: {
    email: boolean
    browser: boolean
    desktop: boolean
  }
  dashboard: {
    defaultView: string
    refreshInterval: number
  }
  terminal: {
    fontSize: number
    fontFamily: string
    theme: string
  }
}

export interface SystemSettings {
  organization: {
    name: string
    logo?: string
    domain: string
  }
  security: {
    sessionTimeout: number
    passwordPolicy: {
      minLength: number
      requireUppercase: boolean
      requireNumbers: boolean
      requireSymbols: boolean
    }
    twoFactorAuth: boolean
  }
  integrations: {
    slack?: {
      webhookUrl: string
      channel: string
    }
    email?: {
      smtp: {
        host: string
        port: number
        secure: boolean
        auth: {
          user: string
          pass: string
        }
      }
    }
  }
  ai: {
    model: string
    apiKey: string
    temperature: number
    maxTokens: number
  }
}

// Documentation & Templates
export type TemplateType = 'docker' | 'kubernetes' | 'terraform' | 'ansible' | 'compose' | 'helm' | 'vagrant'

export interface DocTemplate {
  id: string
  name: string
  type: TemplateType
  description: string
  code: string
  language: string
  category: string
  tags: string[]
  metadata: {
    created: Date
    updated: Date
    author: string
    version: string
  }
  deployment_instructions: string[]
  security_notes: string[]
  recommendations: string[]
}

export interface DocSection {
  id: string
  title: string
  description: string
  templates: DocTemplate[]
  order: number
}

export interface DocQuickLink {
  id: string
  title: string
  description: string
  url: string
  icon: string
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>

export type OptionalFields<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>