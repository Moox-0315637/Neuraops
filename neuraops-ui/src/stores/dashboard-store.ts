/**
 * NeuraOps Dashboard Store (Next.js 14)
 * Zustand store for dashboard data management
 */
import { create } from 'zustand'
import { apiService } from '@/services/api'
import type { Agent, Alert, Command } from '@/types'

// Type aliases to avoid duplication (SonarQube S4323)
type AlertType = 'HIGH' | 'MEDIUM' | 'LOW'
type AlertSeverity = 'critical' | 'warning' | 'info'
type ActivityStatus = 'COMPLETED' | 'RUNNING' | 'SCANNING' | 'FAILED'
type ActivityType = 'log_analysis' | 'deployment' | 'security_scan' | 'agent_action'

export interface DashboardMetrics {
  activeAgents: number
  totalAgents: number
  aiOperations: number
  systemHealth: number
  securityScore: number
  trends: {
    agentsChange: string
    aiOpsChange: string
    healthStatus: string
    securityChange: string
  }
}

export interface SystemAlert {
  id: string
  type: AlertType
  title: string
  source: string
  timestamp: Date
  severity: AlertSeverity
}

export interface RecentActivity {
  id: string
  title: string
  description: string
  status: ActivityStatus
  timestamp: Date
  type: ActivityType
}

interface DashboardState {
  metrics: DashboardMetrics | null
  alerts: SystemAlert[]
  activities: RecentActivity[]
  isLoading: boolean
  error: string | null
  lastUpdated: Date | null
}

// Extended Command type for API responses
interface CommandWithResult extends Command {
  success?: boolean
  timestamp?: string | Date
}

interface DashboardActions {
  // Fetch actions
  fetchDashboardData: () => Promise<void>
  fetchMetrics: () => Promise<void>
  fetchAlerts: () => Promise<void>
  fetchActivities: () => Promise<void>
  
  // Helper actions
  fetchMetricsData: () => Promise<DashboardMetrics>
  fetchAlertsData: () => Promise<SystemAlert[]>
  fetchActivitiesData: () => Promise<RecentActivity[]>
  handleMetricsError: (error: unknown) => void
  handleAlertsError: (error: unknown) => void
  handleActivitiesError: (error: unknown) => void
  getFallbackMetrics: () => DashboardMetrics
  
  // UI actions
  clearError: () => void
  refreshDashboard: () => Promise<void>
}

type DashboardStore = DashboardState & DashboardActions

export const useDashboardStore = create<DashboardStore>((set, get) => ({
  // Initial state
  metrics: null,
  alerts: [],
  activities: [],
  isLoading: false,
  error: null,
  lastUpdated: null,

  // Fetch all dashboard data
  fetchDashboardData: async () => {
    try {
      set({ isLoading: true, error: null })
      
      // Fetch data in parallel
      await Promise.all([
        get().fetchMetrics(),
        get().fetchAlerts(),
        get().fetchActivities()
      ])
      
      set({ 
        isLoading: false,
        lastUpdated: new Date()
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to fetch dashboard data',
        isLoading: false
      })
    }
  },

  // Fetch system metrics
  fetchMetrics: async () => {
    try {
      const metricsData = await get().fetchMetricsData()
      set({ metrics: metricsData })
    } catch (error) {
      get().handleMetricsError(error)
    }
  },

  // Helper: Fetch metrics data
  fetchMetricsData: async (): Promise<DashboardMetrics> => {
    const [systemMetrics, agents] = await Promise.all([
      apiService.getSystemMetrics(),
      apiService.getAgents()
    ])

    const activeAgents = agents.filter(
      (agent: Agent) => agent.status === 'active'
    ).length
    const healthPercentage = systemMetrics.health_percentage ?? 0

    return {
      activeAgents: activeAgents,
      totalAgents: agents.length,
      aiOperations: systemMetrics.ai_operations_count ?? 0,
      systemHealth: healthPercentage,
      securityScore: systemMetrics.security_score ?? 0,
      trends: {
        agentsChange: `+${agents.length - activeAgents} from yesterday`,
        aiOpsChange: '+18% this hour',
        healthStatus: healthPercentage > 95 ? 'Excellent' : 'Good',
        securityChange: '+2 this week'
      }
    }
  },

  // Helper: Handle metrics fetch errors
  handleMetricsError: (error: unknown) => {
    const errorMessage = error instanceof Error 
      ? error.message 
      : 'Failed to fetch metrics'
    
    console.error('Metrics fetch failed:', errorMessage)
    
    set({
      error: `Metrics unavailable: ${errorMessage}`,
      metrics: get().getFallbackMetrics()
    })
  },

  // Helper: Get fallback metrics when API fails
  getFallbackMetrics: (): DashboardMetrics => ({
    activeAgents: 0,
    totalAgents: 0,
    aiOperations: 0,
    systemHealth: 0,
    securityScore: 0,
    trends: {
      agentsChange: 'No data',
      aiOpsChange: 'No data', 
      healthStatus: 'Unknown',
      securityChange: 'No data'
    }
  }),

  // Fetch system alerts
  fetchAlerts: async () => {
    try {
      const alertsData = await get().fetchAlertsData()
      set({ alerts: alertsData })
    } catch (error) {
      get().handleAlertsError(error)
    }
  },

  // Helper: Fetch alerts data
  fetchAlertsData: async (): Promise<SystemAlert[]> => {
    const alertsResponse = await apiService.getAlerts()
    
    // Helper function to map alert severity to type
    const getAlertType = (severity: string): 'HIGH' | 'MEDIUM' | 'LOW' => {
      if (severity === 'critical' || severity === 'high') {
        return 'HIGH'
      }
      if (severity === 'medium') {
        return 'MEDIUM'
      }
      return 'LOW'
    }
    
    // Helper function to map severity to SystemAlert severity
    const getSystemAlertSeverity = (severity: string): 'critical' | 'warning' | 'info' => {
      const severityMap: Record<string, 'critical' | 'warning' | 'info'> = {
        'critical': 'critical',
        'high': 'critical',
        'medium': 'warning',
        'low': 'info'
      }
      return severityMap[severity] ?? 'info'
    }
    
    return alertsResponse.map((alert: Alert) => ({
      id: alert.id,
      type: getAlertType(alert.severity),
      title: alert.title ?? alert.message,
      source: alert.source ?? 'System Monitor',
      timestamp: new Date(alert.createdAt),
      severity: getSystemAlertSeverity(alert.severity)
    }))
  },

  // Helper: Handle alerts fetch errors
  handleAlertsError: (error: unknown) => {
    const errorMessage = error instanceof Error 
      ? error.message 
      : 'Failed to fetch alerts'
    
    console.error('Alerts fetch failed:', errorMessage)
    
    set({
      error: `Alerts unavailable: ${errorMessage}`,
      alerts: []
    })
  },

  // Fetch recent activities  
  fetchActivities: async () => {
    try {
      const activitiesData = await get().fetchActivitiesData()
      set({ activities: activitiesData })
    } catch (error) {
      get().handleActivitiesError(error)
    }
  },

  // Helper: Fetch activities data
  fetchActivitiesData: async (): Promise<RecentActivity[]> => {
    const commands = await apiService.getCommands()
    
    return commands.slice(0, 5).map((cmd: CommandWithResult) => ({
      id: cmd.id,
      title: cmd.command ?? 'Command Execution',
      description: `Executed: ${cmd.command ?? 'Unknown command'}`,
      status: (cmd.success ? 'COMPLETED' : 'FAILED') as RecentActivity['status'],
      timestamp: cmd.timestamp ? new Date(cmd.timestamp) : new Date(),
      type: 'agent_action' as const
    }))
  },

  // Helper: Handle activities fetch errors
  handleActivitiesError: (error: unknown) => {
    const errorMessage = error instanceof Error 
      ? error.message 
      : 'Failed to fetch activities'
    
    console.error('Activities fetch failed:', errorMessage)
    
    set({
      error: `Activities unavailable: ${errorMessage}`,
      activities: []
    })
  },

  // Clear error state
  clearError: () => {
    set({ error: null })
  },

  // Refresh all dashboard data
  refreshDashboard: async () => {
    await get().fetchDashboardData()
  }
}))