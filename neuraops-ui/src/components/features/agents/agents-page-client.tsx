/**
 * NeuraOps Agents Page Client Component
 * Client-side component that manages real agent data from API
 */
'use client'

import { useEffect } from 'react'
import { useAgentStore } from '@/stores/agent-store'
import AuthErrorAlert from '@/components/ui/auth-error-alert'
import type { AgentStatus } from '@/types'

/**
 * Get the appropriate CSS class for status indicator dot
 */
function getStatusIndicatorClass(status: AgentStatus): string {
  switch (status) {
    case 'active':
      return 'bg-green-500'
    case 'inactive':
      return 'bg-gray-500'
    case 'disconnected':
      return 'bg-yellow-500'
    case 'error':
    default:
      return 'bg-red-500'
  }
}

/**
 * Get the appropriate CSS class for status badge
 */
function getStatusBadgeClass(status: AgentStatus): string {
  switch (status) {
    case 'active':
      return 'bg-green-900 text-green-300'
    case 'inactive':
      return 'bg-gray-900 text-gray-300'
    case 'disconnected':
      return 'bg-yellow-900 text-yellow-300'
    case 'error':
    default:
      return 'bg-red-900 text-red-300'
  }
}

/**
 * Render the loading skeleton
 */
function renderLoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="animate-pulse flex items-center space-x-4 p-4 bg-gray-800/50 rounded-lg">
          <div className="rounded-full bg-gray-600 h-10 w-10"></div>
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-gray-600 rounded w-1/4"></div>
            <div className="h-3 bg-gray-600 rounded w-1/2"></div>
          </div>
          <div className="h-6 bg-gray-600 rounded w-16"></div>
        </div>
      ))}
    </div>
  )
}

/**
 * Render the empty state
 */
function renderEmptyState() {
  return (
    <div className="text-center py-8">
      <div className="w-16 h-16 bg-gray-700 rounded-full mx-auto mb-4 flex items-center justify-center">
        <svg className="w-8 h-8 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-white mb-2">No agents found</h3>
      <p className="text-gray-400 mb-4">Get started by adding your first agent to the system.</p>
      <button className="bg-primary-500 hover:bg-primary-600 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors">
        Add Your First Agent
      </button>
    </div>
  )
}

export default function AgentsPageClient() {
  const {
    agents,
    isLoading,
    error,
    fetchAgents,
    getAgentStats,
    clearError
  } = useAgentStore()

  const stats = getAgentStats()

  useEffect(() => {
    // Fetch agents on component mount
    fetchAgents()
  }, [fetchAgents])

  const handleRetry = () => {
    clearError()
    fetchAgents()
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white">Agents</h1>
          <p className="text-gray-400 mt-2">
            Manage and monitor your NeuraOps agents across distributed environments
          </p>
        </div>
        
        <AuthErrorAlert 
          error={error} 
          onRetry={handleRetry}
          showSettingsLink={true}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Agents</h1>
        <p className="text-gray-400 mt-2">
          Manage and monitor your NeuraOps agents across distributed environments
        </p>
      </div>

      {/* Quick Stats - Real data from API */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-dark-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-green-500/20 rounded-lg">
              <div className="w-6 h-6 rounded-full bg-green-500"></div>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-400">Online</p>
              <p className="text-2xl font-bold text-white">
                {isLoading ? (
                  <div className="animate-pulse bg-gray-600 h-8 w-8 rounded"></div>
                ) : (
                  stats.active
                )}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-dark-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-gray-500/20 rounded-lg">
              <div className="w-6 h-6 rounded-full bg-gray-500"></div>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-400">Offline</p>
              <p className="text-2xl font-bold text-white">
                {isLoading ? (
                  <div className="animate-pulse bg-gray-600 h-8 w-8 rounded"></div>
                ) : (
                  stats.inactive
                )}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-dark-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-red-500/20 rounded-lg">
              <div className="w-6 h-6 rounded-full bg-red-500"></div>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-400">Error</p>
              <p className="text-2xl font-bold text-white">
                {isLoading ? (
                  <div className="animate-pulse bg-gray-600 h-8 w-8 rounded"></div>
                ) : (
                  stats.error
                )}
              </p>
            </div>
          </div>
        </div>

        <div className="bg-dark-800 rounded-lg p-6 border border-gray-700">
          <div className="flex items-center">
            <div className="p-2 bg-blue-500/20 rounded-lg">
              <div className="w-6 h-6 rounded-full bg-blue-500"></div>
            </div>
            <div className="ml-4">
              <p className="text-sm text-gray-400">Total</p>
              <p className="text-2xl font-bold text-white">
                {isLoading ? (
                  <div className="animate-pulse bg-gray-600 h-8 w-8 rounded"></div>
                ) : (
                  stats.total
                )}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Agents List - Real data from API */}
      <div className="bg-dark-800 rounded-lg border border-gray-700">
        <div className="p-6 border-b border-gray-700">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Agent List</h2>
            <button className="bg-primary-500 hover:bg-primary-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors">
              Add Agent
            </button>
          </div>
        </div>

        <div className="p-6">
          {isLoading && renderLoadingSkeleton()}
          {!isLoading && agents.length === 0 && renderEmptyState()}
          {!isLoading && agents.length > 0 && (
            <div className="space-y-4">
              {agents.map((agent) => (
                <div key={agent.id} className="flex items-center space-x-4 p-4 bg-gray-800/50 rounded-lg hover:bg-gray-800/70 transition-colors">
                  {/* Status indicator */}
                  <div className={`w-3 h-3 rounded-full ${getStatusIndicatorClass(agent.status)}`}></div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-medium text-white truncate">
                        {agent.name}
                      </h3>
                      <span className="text-sm text-gray-400">
                        #{agent.id}
                      </span>
                    </div>
                    <div className="flex items-center space-x-4 mt-1">
                      <p className="text-sm text-gray-400">
                        📍 {agent.hostname}
                      </p>
                      <p className="text-sm text-gray-400">
                        🏷️ {agent.tags.join(', ')}
                      </p>
                      {agent.lastSeen && (
                        <p className="text-sm text-gray-400">
                          Last seen: {new Date(agent.lastSeen).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(agent.status)}`}>
                      {agent.status}
                    </span>
                    
                    <button className="text-gray-400 hover:text-white p-1">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}