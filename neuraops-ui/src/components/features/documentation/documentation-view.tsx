'use client'

import React, { useEffect, useState } from 'react'
import { useDocumentationStore } from '@/stores/documentation-store'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui'
import { 
  AlertTriangle,
  RefreshCw,
  Copy,
  CheckCircle,
  ExternalLink,
  FileCode,
  BookOpen
} from 'lucide-react'
import { TemplateManager } from './template-manager'

// Helper functions to reduce complexity
const getTemplateTypeIcon = (type: string): string => {
  switch (type) {
    case 'docker': return '🐳'
    case 'kubernetes': return '☸️'
    case 'terraform': return '🏗️'
    case 'ansible': return '📋'
    case 'compose': return '🐙'
    case 'helm': return '⚓'
    default: return '📄'
  }
}

const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch (err) {
    console.error('Failed to copy:', err)
    return false
  }
}

const formatDate = (dateValue: any): string => {
  try {
    if (!dateValue) return 'Unknown'
    
    // Si c'est déjà une date
    if (dateValue instanceof Date) {
      return dateValue.toLocaleDateString()
    }
    
    // Si c'est une chaîne, on essaie de la convertir
    if (typeof dateValue === 'string') {
      const date = new Date(dateValue)
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString()
      }
    }
    
    // Fallback: retourner la valeur telle quelle si c'est une string
    return typeof dateValue === 'string' ? dateValue : 'Unknown'
  } catch (err) {
    console.error('Date formatting error:', err)
    return 'Unknown'
  }
}

const renderLoadingSkeleton = () => (
  <div className="bg-dark-800 rounded-lg border border-gray-700 overflow-hidden animate-pulse">
    <div className="px-6 py-4 border-b border-gray-700">
      <div className="flex items-center justify-between">
        <div>
          <div className="h-6 bg-gray-600 rounded w-32 mb-2"></div>
          <div className="h-4 bg-gray-600 rounded w-48"></div>
        </div>
        <div className="h-6 bg-gray-600 rounded w-16"></div>
      </div>
    </div>
    <div className="p-6">
      <div className="space-y-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-4 bg-gray-700 rounded"></div>
        ))}
      </div>
    </div>
  </div>
)

const renderSidebarLoading = () => (
  <div className="space-y-6">
    {[1, 2].map((i) => (
      <div key={i} className="animate-pulse">
        <div className="h-4 bg-gray-600 rounded w-24 mb-3"></div>
        <div className="space-y-2">
          {[1, 2, 3].map((j) => (
            <div key={j} className="h-8 bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    ))}
  </div>
)

const renderEmptyTemplate = () => (
  <div className="bg-dark-800 rounded-lg border border-gray-700 p-8">
    <div className="text-center text-gray-400">
      <BookOpen className="w-16 h-16 mx-auto mb-4 text-gray-600" />
      <h3 className="text-lg font-medium text-white mb-2">Select a Template</h3>
      <p>Choose a template from the sidebar to view its content and documentation.</p>
    </div>
  </div>
)

const renderNavigationContent = (isLoading: boolean, sections: any[], activeTemplate: string | null, handleTemplateSelect: (sectionId: string, templateId: string) => void) => {
  if (isLoading) {
    return renderSidebarLoading()
  }
  
  if (sections.length === 0) {
    return (
      <div className="text-center py-8 text-gray-400">
        <BookOpen className="w-12 h-12 mx-auto mb-2 text-gray-600" />
        <p>No documentation available</p>
      </div>
    )
  }
  
  return [...sections].sort((a, b) => a.order - b.order)
    .map((section) => (
      <div key={section.id}>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
          {section.title}
        </h3>
        <div className="space-y-2">
          {section.templates.map((template: any) => (
            <button
              key={template.id}
              onClick={() => handleTemplateSelect(section.id, template.id)}
              className={cn(
                'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors flex items-center space-x-2',
                activeTemplate === template.id
                  ? 'bg-primary-500 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )}
            >
              <span className="text-base">
                {getTemplateTypeIcon(template.type)}
              </span>
              <span>{template.name}</span>
            </button>
          ))}
        </div>
      </div>
    ))
}

const renderMainContent = (isLoading: boolean, currentTemplate: any, copySuccess: string | null, handleCopyCode: (code: string, templateId: string) => void) => {
  if (isLoading) {
    return renderLoadingSkeleton()
  }
  
  if (!currentTemplate) {
    return renderEmptyTemplate()
  }
  
  return (
    <div className="bg-dark-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">
              {getTemplateTypeIcon(currentTemplate.type)}
            </span>
            <div>
              <h2 className="text-xl font-semibold text-white">{currentTemplate.name}</h2>
              <p className="text-gray-400 text-sm mt-1">{currentTemplate.description}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="outline" className="bg-primary-500/20 text-primary-400 border-primary-500/30">
              {currentTemplate.language.toUpperCase()}
            </Badge>
            <Badge variant="outline" className="bg-gray-500/20 text-gray-400 border-gray-500/30">
              v{currentTemplate.metadata.version}
            </Badge>
          </div>
        </div>
      </div>

      {/* Code Block */}
      <div className="relative">
        <div className="absolute top-4 right-4 z-10">
          <button
            onClick={() => handleCopyCode(currentTemplate.code, currentTemplate.id)}
            className="flex items-center space-x-2 bg-gray-700 hover:bg-gray-600 text-white px-3 py-1 rounded text-xs transition-colors"
          >
            {copySuccess === currentTemplate.id ? (
              <>
                <CheckCircle className="w-3 h-3" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3 h-3" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
        <pre className="p-6 bg-black text-green-400 text-sm overflow-x-auto font-mono leading-relaxed">
          <code>{currentTemplate.code}</code>
        </pre>
      </div>

      {/* Template Information */}
      <div className="border-t border-gray-700">
        <div className="px-6 py-4">
          <div className="space-y-6">
            {/* Deployment Instructions */}
            {currentTemplate.deployment_instructions.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-white mb-3 flex items-center">
                  <FileCode className="w-4 h-4 mr-2" />
                  Deployment Instructions
                </h3>
                <ul className="space-y-1 text-sm text-gray-300">
                  {currentTemplate.deployment_instructions.map((instruction: string, index: number) => (
                    <li key={`deployment-${index}-${instruction.slice(0, 20)}`} className="flex items-start space-x-2">
                      <span className="text-primary-400 mt-0.5">•</span>
                      <span>{instruction}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Security Notes */}
            {currentTemplate.security_notes.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-yellow-400 mb-3">
                  🔒 Security Notes
                </h3>
                <ul className="space-y-1 text-sm text-gray-300">
                  {currentTemplate.security_notes.map((note: string, index: number) => (
                    <li key={`security-${index}-${note.slice(0, 20)}`} className="flex items-start space-x-2">
                      <span className="text-yellow-400 mt-0.5">⚠️</span>
                      <span>{note}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Recommendations */}
            {currentTemplate.recommendations.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-green-400 mb-3">
                  💡 Recommendations
                </h3>
                <ul className="space-y-1 text-sm text-gray-300">
                  {currentTemplate.recommendations.map((recommendation: string, index: number) => (
                    <li key={`recommendation-${index}-${recommendation.slice(0, 20)}`} className="flex items-start space-x-2">
                      <span className="text-green-400 mt-0.5">✓</span>
                      <span>{recommendation}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer Information */}
      <div className="px-6 py-4 bg-dark-900/50 border-t border-gray-700">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <div className="flex items-center space-x-4">
            <span>🛡️ Security validated</span>
            <span>•</span>
            <span>🚀 Production ready</span>
            <span>•</span>
            <span>📅 Updated {formatDate(currentTemplate.metadata.updated)}</span>
          </div>
          <div className="flex items-center space-x-1">
            <span>by</span>
            <span className="text-primary-400">{currentTemplate.metadata.author}</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function DocumentationView() {
  const [copySuccess, setCopySuccess] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'documentation' | 'templates'>('documentation')
  
  const {
    sections,
    activeSection,
    activeTemplate,
    quickLinks,
    isLoading,
    error,
    fetchDocumentation,
    setActiveSection,
    setActiveTemplate,
    getTemplateById,
    clearError
  } = useDocumentationStore()

  // Debug logging
  React.useEffect(() => {
    console.log('Documentation Debug:', {
      sections: sections,
      sectionsLength: sections.length,
      activeSection,
      activeTemplate,
      quickLinks: quickLinks.length,
      currentTemplate: activeTemplate ? getTemplateById(activeTemplate) : null
    })
  }, [sections, activeSection, activeTemplate, quickLinks, getTemplateById])

  useEffect(() => {
    if (activeTab === 'documentation') {
      fetchDocumentation()
    }
  }, [fetchDocumentation, activeTab])

  // Get current template
  const currentTemplate = activeTemplate ? getTemplateById(activeTemplate) : null

  const handleRefresh = () => {
    clearError()
    fetchDocumentation()
  }

  const handleCopyCode = async (code: string, templateId: string) => {
    const success = await copyToClipboard(code)
    if (success) {
      setCopySuccess(templateId)
      setTimeout(() => setCopySuccess(null), 2000)
    }
  }

  const handleTemplateSelect = (sectionId: string, templateId: string) => {
    if (sectionId !== activeSection) {
      setActiveSection(sectionId)
    }
    setActiveTemplate(templateId)
  }

  if (error && activeTab === 'documentation') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Documentation</h1>
            <p className="text-gray-400 mt-2">
              Infrastructure as Code templates and DevOps examples
            </p>
          </div>
        </div>
        
        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-6">
          <div className="flex items-center">
            <AlertTriangle className="w-6 h-6 text-red-500 mr-3" />
            <div>
              <h3 className="text-lg font-medium text-red-400">Failed to load documentation</h3>
              <p className="text-red-300 mt-1">{error}</p>
              <button 
                onClick={handleRefresh}
                className="mt-3 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
              >
                Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header with tabs */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Documentation</h1>
          <p className="text-gray-400 mt-2">
            Infrastructure as Code templates and DevOps examples
          </p>
        </div>
        
        <div className="flex bg-dark-800 rounded-lg p-1 border border-gray-700">
          <button
            onClick={() => setActiveTab('documentation')}
            className={cn(
              'px-4 py-2 rounded-md text-sm font-medium transition-colors',
              activeTab === 'documentation'
                ? 'bg-primary-500 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            )}
          >
            <BookOpen className="w-4 h-4 mr-2 inline" />
            Templates
          </button>
          <button
            onClick={() => setActiveTab('templates')}
            className={cn(
              'px-4 py-2 rounded-md text-sm font-medium transition-colors',
              activeTab === 'templates'
                ? 'bg-primary-500 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-700'
            )}
          >
            <FileCode className="w-4 h-4 mr-2 inline" />
            Manage
          </button>
        </div>
      </div>

      {activeTab === 'templates' ? (
        <TemplateManager />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar Navigation */}
          <div className="lg:col-span-1">
            <div className="bg-dark-800 rounded-lg border border-gray-700 p-4 sticky top-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-white">Documentation</h3>
                <button
                  onClick={handleRefresh}
                  disabled={isLoading}
                  className="p-1 text-gray-400 hover:text-white transition-colors disabled:opacity-50"
                  title="Refresh documentation"
                >
                  <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
              </div>

              <nav className="space-y-6">
                {renderNavigationContent(isLoading, sections, activeTemplate, handleTemplateSelect)}
              </nav>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            {renderMainContent(isLoading, currentTemplate, copySuccess, handleCopyCode)}

            {/* Quick Links */}
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              {quickLinks.map((link) => (
                <div key={link.id} className="bg-dark-800 rounded-lg border border-gray-700 p-4 hover:border-gray-600 transition-colors">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-sm font-semibold text-white mb-2">{link.title}</h3>
                      <p className="text-xs text-gray-400 mb-3">{link.description}</p>
                      <button className="text-primary-400 hover:text-primary-300 text-xs font-medium flex items-center space-x-1">
                        <span>Learn More</span>
                        <ExternalLink className="w-3 h-3" />
                      </button>
                    </div>
                    <div className="text-xl">
                      {link.icon === 'rocket' ? '🚀' : '📚'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}