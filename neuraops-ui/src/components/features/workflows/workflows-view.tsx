'use client'

import { useEffect, useState } from 'react'
import { 
  CheckCircle, 
  Clock, 
  FileText, 
  BarChart3,
  PlayCircle,
  Zap,
  RefreshCw,
  AlertTriangle,
  Plus,
  Download,
  Edit,
  Trash2,
  X
} from 'lucide-react'
import { useWorkflowStore } from '@/stores/workflow-store'
import { apiService } from '@/services/api'

// Helper functions to reduce complexity
const getExecutionStatusColor = (status: string): string => {
  switch (status) {
    case 'completed': return 'text-green-500'
    case 'running': return 'text-blue-500'
    case 'failed': return 'text-red-500'
    case 'cancelled': return 'text-gray-500'
    default: return 'text-yellow-500'
  }
}

const getExecutionStatusIcon = (status: string) => {
  switch (status) {
    case 'completed': return <CheckCircle className="w-5 h-5" />
    case 'running': return <PlayCircle className="w-5 h-5" />
    case 'failed': return <AlertTriangle className="w-5 h-5" />
    default: return <Clock className="w-5 h-5" />
  }
}

const formatTimeAgo = (date: Date): string => {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

const renderMetricValue = (isLoading: boolean, value: number | undefined): React.ReactNode => {
  if (isLoading) {
    return <span className="inline-block animate-pulse bg-gray-600 h-8 w-8 rounded"></span>
  }
  return value ?? 0
}

const renderExecutionsContent = (isLoading: boolean, executions: any[], workflows: any[]) => {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1,2,3].map(i => (
          <div key={i} className="animate-pulse flex items-center justify-between p-4 bg-dark-700 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gray-600 rounded-full"></div>
              <div className="space-y-2">
                <div className="h-4 bg-gray-600 rounded w-32"></div>
                <div className="h-3 bg-gray-600 rounded w-20"></div>
              </div>
            </div>
            <div className="h-4 bg-gray-600 rounded w-16"></div>
          </div>
        ))}
      </div>
    )
  }
  
  if (executions?.length) {
    return (
      <div className="space-y-4">
        {executions.map((execution) => {
          const workflow = workflows.find(w => w.id === execution.workflowId)
          return (
            <div key={execution.id} className="flex items-center justify-between p-4 bg-dark-700 rounded-lg hover:bg-gray-700/50 transition-colors">
              <div className="flex items-center space-x-3">
                <span className={`w-10 h-10 bg-gray-500/20 rounded-full flex items-center justify-center ${getExecutionStatusColor(execution.status)}`}>
                  {getExecutionStatusIcon(execution.status)}
                </span>
                <div>
                  <p className="text-white font-medium">{workflow?.name ?? 'Unknown Workflow'}</p>
                  <p className="text-sm text-gray-400">{formatTimeAgo(new Date(execution.startedAt))}</p>
                </div>
              </div>
              <span className={`text-sm font-medium capitalize ${getExecutionStatusColor(execution.status)}`}>
                {execution.status}
              </span>
            </div>
          )
        })}
      </div>
    )
  }
  
  return (
    <div className="text-center py-8 text-gray-400">
      <Clock className="w-12 h-12 mx-auto mb-2 text-gray-600" />
      <p>No recent executions</p>
    </div>
  )
}

const renderWorkflowsContent = (isLoading: boolean, workflows: any[]) => {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1,2,3].map(i => (
          <div key={i} className="animate-pulse flex items-center justify-between p-4 bg-dark-700 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gray-600 rounded-full"></div>
              <div className="space-y-2">
                <div className="h-4 bg-gray-600 rounded w-32"></div>
                <div className="h-3 bg-gray-600 rounded w-24"></div>
              </div>
            </div>
            <div className="h-4 bg-gray-600 rounded w-12"></div>
          </div>
        ))}
      </div>
    )
  }
  
  if (workflows?.length) {
    return (
      <div className="space-y-4">
        {workflows.map((workflow) => (
          <div key={workflow.id} className="flex items-center justify-between p-4 bg-dark-700 rounded-lg hover:bg-gray-700/50 transition-colors">
            <div className="flex items-center space-x-3">
              <span className="w-10 h-10 bg-primary-500/20 rounded-full flex items-center justify-center">
                <Zap className="w-5 h-5 text-primary-500" />
              </span>
              <div>
                <p className="text-white font-medium">{workflow.name}</p>
                <p className="text-sm text-gray-400">{workflow.executionCount?.toLocaleString() ?? '0'} executions</p>
              </div>
            </div>
            <button className="text-primary-500 hover:text-primary-400 text-sm font-medium">
              View
            </button>
          </div>
        ))}
      </div>
    )
  }
  
  return (
    <div className="text-center py-8 text-gray-400">
      <Zap className="w-12 h-12 mx-auto mb-2 text-gray-600" />
      <p>No executed workflows yet</p>
    </div>
  )
}

export default function WorkflowsView() {
  const {
    workflows,
    executions,
    isLoading,
    error,
    fetchWorkflows,
    fetchExecutions,
    getWorkflowStats,
    clearError
  } = useWorkflowStore()

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showTemplatesModal, setShowTemplatesModal] = useState(false)
  const [workflowTemplates, setWorkflowTemplates] = useState<any[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null)

  // Create workflow form state
  const [newWorkflow, setNewWorkflow] = useState({
    name: '',
    description: '',
    section: 'general'
  })

  useEffect(() => {
    fetchWorkflows()
    fetchExecutions()
  }, [])

  const handleCreateWorkflow = () => {
    setShowCreateModal(true)
  }

  const handleBrowseTemplates = async () => {
    setShowTemplatesModal(true)
    setTemplatesLoading(true)
    try {
      const templates = await apiService.getWorkflowTemplatesFromFilesystem()
      setWorkflowTemplates(templates)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message ?? 'Failed to load templates' })
    } finally {
      setTemplatesLoading(false)
    }
  }

  const handleCreateFromTemplate = async (template: any) => {
    try {
      // Create a new workflow based on template
      const workflowData = {
        name: `${template.workflow_name} (Copy)`,
        description: template.workflow_description,
        steps: JSON.parse(template.content).steps ?? [],
        template_id: template.file_name
      }

      // Save as new workflow file
      const blob = new Blob([JSON.stringify(workflowData, null, 2)], { type: 'application/json' })
      const file = new File([blob], `${workflowData.name.toLowerCase().replace(/\s+/g, '-')}.json`, { type: 'application/json' })
      
      await apiService.uploadWorkflowTemplate('created', file.name, file)
      setMessage({ type: 'success', text: 'Workflow created from template successfully' })
      setShowTemplatesModal(false)
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message ?? 'Failed to create workflow from template' })
    }
  }

  const handleSubmitNewWorkflow = async () => {
    if (!newWorkflow.name.trim()) {
      setMessage({ type: 'error', text: 'Workflow name is required' })
      return
    }

    try {
      const workflowData = {
        name: newWorkflow.name,
        description: newWorkflow.description ?? 'New workflow created from UI',
        version: '1.0.0',
        created_at: new Date().toISOString(),
        steps: [
          {
            step_id: 'step1',
            name: 'Initial Step',
            type: 'command',
            command: 'echo "Hello from new workflow"',
            timeout: 30
          }
        ]
      }

      const blob = new Blob([JSON.stringify(workflowData, null, 2)], { type: 'application/json' })
      const filename = `${newWorkflow.name.toLowerCase().replace(/\s+/g, '-')}.json`
      const file = new File([blob], filename, { type: 'application/json' })

      await apiService.uploadWorkflowTemplate(newWorkflow.section, filename, file)
      setMessage({ type: 'success', text: 'Workflow created successfully' })
      setShowCreateModal(false)
      setNewWorkflow({ name: '', description: '', section: 'general' })
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message ?? 'Failed to create workflow' })
    }
  }

  const handleRefresh = () => {
    clearError()
    fetchWorkflows()
    fetchExecutions()
  }

  // Get workflow statistics
  const stats = getWorkflowStats()

  // Get recent executions (last 3) - separate sort to avoid mutating original array
  const sortedExecutions = [...executions].sort((a: any, b: any) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
  const recentExecutions = sortedExecutions.slice(0, 3)

  // Get popular workflows (by execution count) - separate sort to avoid mutating original array
  const filteredWorkflows = workflows.filter(w => w.executionCount > 0)
  const sortedWorkflows = [...filteredWorkflows].sort((a: any, b: any) => b.executionCount - a.executionCount)
  const popularWorkflows = sortedWorkflows.slice(0, 3)

  if (error) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Error Loading Workflows</h2>
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
          <h1 className="text-2xl font-bold text-white">Workflows</h1>
          <p className="text-gray-400 mt-1">Automate your DevOps processes with intelligent workflows</p>
        </div>
        
        <div className="flex items-center space-x-3">
          <button
            onClick={handleCreateWorkflow}
            className="flex items-center space-x-2 px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Create Workflow</span>
          </button>
          
          <button
            onClick={handleBrowseTemplates}
            className="flex items-center space-x-2 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg border border-gray-700 transition-colors"
          >
            <FileText className="w-4 h-4" />
            <span>Browse Templates</span>
          </button>
          
          <button
            onClick={handleRefresh}
            disabled={isLoading}
            className="flex items-center space-x-2 px-4 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-lg border border-gray-700 transition-colors"
          >
            <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {/* Active Workflows */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-green-500/20 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-400">Active</p>
            <p className="text-2xl font-bold text-white">
              {renderMetricValue(isLoading, stats.active)}
            </p>
          </div>
        </div>

        {/* Running Executions */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <PlayCircle className="w-6 h-6 text-blue-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-400">Running</p>
            <p className="text-2xl font-bold text-white">
              {renderMetricValue(isLoading, executions.filter(e => e.status === 'running').length)}
            </p>
          </div>
        </div>

        {/* Draft Workflows */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-gray-500/20 rounded-lg">
              <FileText className="w-6 h-6 text-gray-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-400">Draft</p>
            <p className="text-2xl font-bold text-white">
              {renderMetricValue(isLoading, stats.draft)}
            </p>
          </div>
        </div>

        {/* Total Workflows */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between">
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <BarChart3 className="w-6 h-6 text-purple-400" />
            </div>
          </div>
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-400">Total</p>
            <p className="text-2xl font-bold text-white">
              {renderMetricValue(isLoading, stats.total)}
            </p>
          </div>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Executions */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Executions</h2>
            <Clock className="w-5 h-5 text-blue-400" />
          </div>
          
          {renderExecutionsContent(isLoading, recentExecutions, workflows)}
        </div>

        {/* Popular Workflows */}
        <div className="p-6 bg-dark-800 rounded-lg border border-gray-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Popular Workflows</h2>
            <Zap className="w-5 h-5 text-purple-400" />
          </div>
          
          {renderWorkflowsContent(isLoading, popularWorkflows)}
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`p-4 rounded-lg flex items-center mb-4 ${
          message.type === 'success' 
            ? 'bg-green-900/20 text-green-300 border border-green-500/30' 
            : 'bg-red-900/20 text-red-300 border border-red-500/30'
        }`}>
          {message.type === 'success' ? <CheckCircle className="mr-2 h-4 w-4" /> : <AlertTriangle className="mr-2 h-4 w-4" />}
          {message.text}
        </div>
      )}

      {/* Create Workflow Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg shadow-xl w-[500px] border border-gray-700">
            <div className="p-6 border-b border-gray-700 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Create New Workflow</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Workflow Name</label>
                <input
                  type="text"
                  value={newWorkflow.name}
                  onChange={(e) => setNewWorkflow({ ...newWorkflow, name: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white"
                  placeholder="Enter workflow name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
                <textarea
                  value={newWorkflow.description}
                  onChange={(e) => setNewWorkflow({ ...newWorkflow, description: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white h-20"
                  placeholder="Enter workflow description"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Section</label>
                <select
                  value={newWorkflow.section}
                  onChange={(e) => setNewWorkflow({ ...newWorkflow, section: e.target.value })}
                  className="w-full px-3 py-2 bg-dark-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white"
                >
                  <option value="general">General</option>
                  <option value="deployment">Deployment</option>
                  <option value="maintenance">Maintenance</option>
                  <option value="monitoring">Monitoring</option>
                  <option value="created">Created</option>
                </select>
              </div>
            </div>
            
            <div className="p-6 border-t border-gray-700 flex items-center justify-end space-x-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitNewWorkflow}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
              >
                Create Workflow
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Browse Templates Modal */}
      {showTemplatesModal && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg shadow-xl w-[800px] max-h-[80vh] flex flex-col border border-gray-700">
            <div className="p-6 border-b border-gray-700 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Browse Workflow Templates</h3>
              <button
                onClick={() => setShowTemplatesModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="flex-1 p-6 overflow-auto">
              {templatesLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="animate-spin mr-2 text-primary-400" />
                  <span className="text-gray-300">Loading templates...</span>
                </div>
              ) : workflowTemplates.length === 0 ? (
                <div className="text-center py-8 text-gray-400">
                  <FileText className="w-12 h-12 mx-auto mb-2 text-gray-600" />
                  <p>No workflow templates found</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {workflowTemplates.map((template, index) => (
                    <div key={index} className="border border-gray-700 rounded-lg p-4 hover:bg-dark-700 transition-colors">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-medium text-white">{template.workflow_name}</h4>
                          <p className="text-sm text-gray-400 mt-1">{template.workflow_description ?? 'No description'}</p>
                          <div className="flex items-center space-x-4 mt-2">
                            <span className="text-xs text-gray-500">Section: {template.section_id}</span>
                            <span className="text-xs text-gray-500">Steps: {template.steps_count ?? 0}</span>
                            <span className="text-xs text-gray-500">Version: {template.workflow_version}</span>
                          </div>
                        </div>
                        <button
                          onClick={() => handleCreateFromTemplate(template)}
                          className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors flex items-center space-x-2"
                        >
                          <Plus className="w-4 h-4" />
                          <span>Use Template</span>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  )
}