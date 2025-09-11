'use client'

import { useState, useEffect } from 'react'
import { 
  Server, 
  Activity, 
  Shield, 
  TrendingUp,
  AlertTriangle, 
  CheckCircle, 
  Clock,
  RefreshCw,
  Zap
} from 'lucide-react'
import { useDashboardStore, type SystemAlert } from '@/stores/dashboard-store'

// Helper functions to reduce complexity
const getCurrentTimeDisplay = (lastUpdated: Date | null, isMounted: boolean, currentTime: Date): string => {
  if (lastUpdated) return lastUpdated.toLocaleTimeString()
  if (isMounted) return currentTime.toLocaleTimeString()
  return '--:--:--'
}

const renderMetricValue = (isLoading: boolean, value: number | undefined): React.ReactNode => {
  if (isLoading) {
    return <span className="inline-block animate-pulse bg-gray-600 h-8 w-12 rounded"></span>
  }
  return value ?? 0
}

const renderWideMetricValue = (isLoading: boolean, value: number | string | undefined): React.ReactNode => {
  if (isLoading) {
    return <span className="inline-block animate-pulse bg-gray-600 h-8 w-16 rounded"></span>
  }
  return value ?? 0
}

const renderAlertsContent = (isLoading: boolean, alerts: SystemAlert[] | undefined, getAlertColor: (severity: string) => string) => {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1,2,3].map(i => (
          <div key={i} className="animate-pulse">
            <div className="flex items-center space-x-3">
              <div className="h-3 w-3 bg-gray-600 rounded-full"></div>
              <div className="h-4 bg-gray-600 rounded flex-1"></div>
              <div className="h-3 w-16 bg-gray-600 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }
  
  if (alerts?.length) {
    return (
      <div className="space-y-3 max-h-64 overflow-y-auto">
        {alerts.slice(0, 5).map((alert) => (
          <div key={alert.id} className="flex items-start space-x-3 p-3 bg-dark-700 rounded border border-gray-600">
            <AlertTriangle className={`w-4 h-4 mt-0.5 ${getAlertColor(alert.severity)}`} />
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium">{alert.title}</p>
              <p className="text-gray-400 text-sm truncate">{alert.source}</p>
            </div>
            <span className={`text-xs ${getAlertColor(alert.severity)}`}>
              {alert.severity}
            </span>
          </div>
        ))}
      </div>
    )
  }
  
  return (
    <div className="text-center py-8">
      <CheckCircle className="w-8 h-8 text-green-400 mx-auto mb-2" />
      <p className="text-gray-400">No alerts</p>
    </div>
  )
}

const renderActivitiesContent = (isLoading: boolean, activities: any[], getStatusColor: (status: string) => string) => {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {[1,2,3].map(i => (
          <div key={i} className="animate-pulse">
            <div className="flex items-center space-x-3">
              <div className="h-3 w-3 bg-gray-600 rounded-full"></div>
              <div className="h-4 bg-gray-600 rounded flex-1"></div>
              <div className="h-3 w-16 bg-gray-600 rounded"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }
  
  if (activities?.length) {
    return (
      <div className="space-y-3 max-h-64 overflow-y-auto">
        {activities.slice(0, 5).map((activity) => (
          <div key={activity.id} className="flex items-start space-x-3 p-3 bg-dark-700 rounded border border-gray-600">
            <div className={`w-3 h-3 rounded-full mt-1 ${getStatusColor(activity.status)}`} />
            <div className="flex-1 min-w-0">
              <p className="text-white text-sm font-medium">{activity.type ?? activity.title}</p>
              <p className="text-gray-400 text-sm truncate">{activity.description}</p>
            </div>
            <div className="text-right">
              <Clock className="w-4 h-4 text-gray-500 mx-auto" />
              <span className="text-xs text-gray-400 block mt-1">
                {new Date(activity.timestamp).toLocaleTimeString()}
              </span>
            </div>
          </div>
        ))}
      </div>
    )
  }
  
  return (
    <div className="text-center py-8">
      <Activity className="w-8 h-8 text-gray-500 mx-auto mb-2" />
      <p className="text-gray-400">No recent activities</p>
    </div>
  )
}

export default function Dashboard() {
  const [isMounted, setIsMounted] = useState(false)
  const [currentTime, setCurrentTime] = useState(new Date())
  
  const {
    metrics,
    alerts,
    activities,
    isLoading,
    error,
    lastUpdated,
    fetchDashboardData,
    refreshDashboard,
    clearError
  } = useDashboardStore()

  useEffect(() => {
    setIsMounted(true)
    fetchDashboardData()
    
    const interval = setInterval(() => setCurrentTime(new Date()), 60000)
    const refreshInterval = setInterval(() => {
      if (!isLoading) refreshDashboard()
    }, 300000) // 5 min

    return () => {
      clearInterval(interval)
      clearInterval(refreshInterval)
    }
  }, [])

  const handleRefresh = () => {
    clearError()
    refreshDashboard()
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'text-green-400'
      case 'inactive': return 'text-red-400'  
      case 'warning': return 'text-yellow-400'
      default: return 'text-gray-400'
    }
  }

  const getAlertColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-400'
      case 'error': return 'text-red-400'
      case 'warning': return 'text-yellow-400'
      case 'medium': return 'text-orange-400'
      default: return 'text-blue-400'
    }
  }

  if (error) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Error Loading Dashboard</h2>
          <p className="text-gray-400 mb-4">{error}</p>
          <button 
            onClick={handleRefresh}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">NeuraOps Dashboard</h1>
          <p className="text-gray-400 mt-1">Monitor your AI-powered DevOps operations</p>
        </div>
        
        <div className="flex items-center space-x-4">
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg border border-gray-700 transition-colors"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          
          <div className="text-right">
            <div className="text-sm text-gray-400">
              {lastUpdated ? 'Last updated' : 'Current time'}
            </div>
            <div className="text-white font-mono text-sm">
              {getCurrentTimeDisplay(lastUpdated, isMounted, currentTime)}
            </div>
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Active Agents */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-green-500/20 rounded-lg">
              <Server className="w-6 h-6 text-green-400" />
            </div>
            <TrendingUp className="w-5 h-5 text-green-400" />
          </div>
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-400">Active Agents</p>
            <p className="text-2xl font-bold text-white">
              {renderMetricValue(isLoading, metrics?.activeAgents)}
            </p>
          </div>
        </div>

        {/* Total Agents */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <Server className="w-6 h-6 text-blue-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-400">Total Agents</p>
            <p className="text-2xl font-bold text-white">
              {renderWideMetricValue(isLoading, metrics?.totalAgents)}
            </p>
          </div>
        </div>

        {/* System Health */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-emerald-500/20 rounded-lg">
              <Shield className="w-6 h-6 text-emerald-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-400">System Health</p>
            <p className="text-2xl font-bold text-white">
              {renderWideMetricValue(isLoading, `${metrics?.systemHealth ?? 0}%`)}
            </p>
          </div>
        </div>

        {/* AI Operations */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <Zap className="w-6 h-6 text-purple-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-400">AI Operations</p>
            <p className="text-2xl font-bold text-white">
              {renderWideMetricValue(isLoading, metrics?.aiOperations)}
            </p>
          </div>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Alerts</h2>
            <AlertTriangle className="w-5 h-5 text-yellow-400" />
          </div>
          
          {renderAlertsContent(isLoading, alerts, getAlertColor)}
        </div>

        {/* Recent Activities */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Activities</h2>
            <Activity className="w-5 h-5 text-blue-400" />
          </div>
          
          {renderActivitiesContent(isLoading, activities, getStatusColor)}
        </div>
      </div>
    </div>
  )
}