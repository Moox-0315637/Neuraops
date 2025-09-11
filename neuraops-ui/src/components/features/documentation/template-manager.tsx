'use client'

import React, { useState, useEffect } from 'react'
import { apiService } from '@/services/api'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui'
import { 
  Upload,
  Trash2,
  File,
  FolderOpen,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Edit,
  Download
} from 'lucide-react'

interface Template {
  file_name: string
  file_path: string
  section_id: string
  content: string
  size: number
  created: string
  modified: string
  extension: string
}

interface TemplateManagerProps {
  className?: string
}

export function TemplateManager({ className }: TemplateManagerProps) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedSection, setSelectedSection] = useState<string>('')
  const [customFilename, setCustomFilename] = useState<string>('')
  const [uploadMessage, setUploadMessage] = useState<{ type: 'success' | 'error', message: string } | null>(null)
  const [selectedTemplate, setSelectedTemplate] = useState<Template | null>(null)
  const [editContent, setEditContent] = useState<string>('')
  const [showEditModal, setShowEditModal] = useState(false)

  const sections = ['containers', 'kubernetes', 'terraform', 'ansible']

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    try {
      setLoading(true)
      const data = await apiService.getFilesystemTemplates()
      setTemplates(data)
      setError(null)
    } catch (err) {
      setError('Failed to load templates')
      console.error('Template loading error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      // Auto-detect section from file name or set default
      const fileName = file.name.toLowerCase()
      if (fileName.includes('docker')) {
        setSelectedSection('containers')
      } else if (fileName.includes('k8s') || fileName.includes('kubernetes')) {
        setSelectedSection('kubernetes')
      } else if (fileName.includes('terraform') || fileName.includes('tf')) {
        setSelectedSection('terraform')
      } else if (fileName.includes('ansible') || fileName.includes('yml')) {
        setSelectedSection('ansible')
      }
      setCustomFilename(file.name)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile || !selectedSection) {
      setUploadMessage({ type: 'error', message: 'Please select a file and section' })
      return
    }

    try {
      setUploading(true)
      const filename = customFilename ?? selectedFile.name
      await apiService.uploadTemplate(selectedSection, filename, selectedFile)
      
      setUploadMessage({ type: 'success', message: `Template ${filename} uploaded successfully` })
      setSelectedFile(null)
      setCustomFilename('')
      setSelectedSection('')
      
      // Reset file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''
      
      // Reload templates
      await loadTemplates()
      
      // Clear message after 3 seconds
      setTimeout(() => setUploadMessage(null), 3000)
    } catch (err: any) {
      setUploadMessage({ type: 'error', message: err.message ?? 'Upload failed' })
      setTimeout(() => setUploadMessage(null), 5000)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (template: Template) => {
    if (!confirm(`Are you sure you want to delete ${template.file_name}?`)) {
      return
    }

    try {
      await apiService.deleteTemplate(template.section_id, template.file_name)
      setUploadMessage({ type: 'success', message: `Template ${template.file_name} deleted successfully` })
      await loadTemplates()
      setTimeout(() => setUploadMessage(null), 3000)
    } catch (err: any) {
      setUploadMessage({ type: 'error', message: err.message ?? 'Delete failed' })
      setTimeout(() => setUploadMessage(null), 5000)
    }
  }

  const handleEdit = async (template: Template) => {
    try {
      const content = await apiService.getTemplateContent(template.section_id, template.file_name)
      setSelectedTemplate(template)
      setEditContent(content.content)
      setShowEditModal(true)
    } catch (err: any) {
      console.error('Failed to load template content:', err)
      setUploadMessage({ type: 'error', message: 'Failed to load template content' })
      setTimeout(() => setUploadMessage(null), 5000)
    }
  }

  const handleSaveEdit = async () => {
    if (!selectedTemplate) return

    try {
      await apiService.updateTemplateContent(selectedTemplate.section_id, selectedTemplate.file_name, editContent)
      setUploadMessage({ type: 'success', message: 'Template updated successfully' })
      setShowEditModal(false)
      setSelectedTemplate(null)
      setEditContent('')
      await loadTemplates()
      setTimeout(() => setUploadMessage(null), 3000)
    } catch (err: any) {
      setUploadMessage({ type: 'error', message: err.message ?? 'Update failed' })
      setTimeout(() => setUploadMessage(null), 5000)
    }
  }

  const handleDownload = (template: Template) => {
    const blob = new Blob([template.content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = template.file_name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const getFileIcon = (extension: string) => {
    const ext = extension.toLowerCase()
    if (['.yml', '.yaml'].includes(ext)) return '📋'
    if (['.tf', '.hcl'].includes(ext)) return '🏗️'
    if (['.dockerfile', '.dockerignore'].includes(ext)) return '🐳'
    if (['.json', '.js', '.ts'].includes(ext)) return '📄'
    if (['.sh', '.bash'].includes(ext)) return '⚡'
    return '📄'
  }

  if (loading) {
    return (
      <div className={cn("flex items-center justify-center p-8", className)}>
        <RefreshCw className="animate-spin mr-2 text-primary-400" />
        <span className="text-gray-300">Loading templates...</span>
      </div>
    )
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Upload Section */}
      <div className="bg-dark-800 p-6 rounded-lg border border-gray-700">
        <h3 className="text-lg font-semibold mb-4 flex items-center text-white">
          <Upload className="mr-2" />
          Upload New Template
        </h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          <div>
            <label htmlFor="file-input" className="block text-sm font-medium mb-2 text-gray-300">Select File</label>
            <input
              id="file-input"
              type="file"
              onChange={handleFileSelect}
              className="w-full px-3 py-2 bg-dark-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white"
              accept=".yml,.yaml,.tf,.dockerfile,.json,.sh,.bash,.txt,.md"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2 text-gray-300">Section</label>
            <select
              value={selectedSection}
              onChange={(e) => setSelectedSection(e.target.value)}
              className="w-full px-3 py-2 bg-dark-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white"
            >
              <option value="">Select section...</option>
              {sections.map(section => (
                <option key={section} value={section}>{section}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2 text-gray-300">Filename (optional)</label>
            <input
              type="text"
              value={customFilename}
              onChange={(e) => setCustomFilename(e.target.value)}
              placeholder="Leave empty to use original name"
              className="w-full px-3 py-2 bg-dark-700 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-white placeholder-gray-400"
            />
          </div>
          
          <div className="flex items-end">
            <button
              onClick={handleUpload}
              disabled={!selectedFile || !selectedSection || uploading}
              className="w-full px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            >
              {uploading ? (
                <>
                  <RefreshCw className="animate-spin mr-2 h-4 w-4" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Upload
                </>
              )}
            </button>
          </div>
        </div>

        {selectedFile && (
          <div className="bg-dark-700 p-3 rounded-md border border-gray-600">
            <p className="text-sm text-gray-300">
              Selected: <span className="font-medium text-white">{selectedFile.name}</span> ({formatFileSize(selectedFile.size)})
            </p>
          </div>
        )}
      </div>

      {/* Messages */}
      {uploadMessage && (
        <div className={cn(
          "p-4 rounded-md flex items-center",
          uploadMessage.type === 'success' ? "bg-green-900/20 text-green-300 border border-green-500/30" : "bg-red-900/20 text-red-300 border border-red-500/30"
        )}>
          {uploadMessage.type === 'success' ? (
            <CheckCircle className="mr-2 h-4 w-4" />
          ) : (
            <AlertCircle className="mr-2 h-4 w-4" />
          )}
          {uploadMessage.message}
        </div>
      )}

      {/* Templates List */}
      <div className="bg-dark-800 rounded-lg border border-gray-700">
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center text-white">
            <FolderOpen className="mr-2" />
            Templates ({templates.length})
          </h3>
          <button
            onClick={loadTemplates}
            className="px-3 py-1 bg-dark-700 hover:bg-dark-600 rounded-md flex items-center text-sm text-gray-300 hover:text-white border border-gray-600"
          >
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </button>
        </div>

        {error ? (
          <div className="p-4 text-red-400 flex items-center">
            <AlertCircle className="mr-2" />
            {error}
          </div>
        ) : templates.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <File className="mx-auto mb-2 h-8 w-8" />
            <p>No templates found. Upload your first template above.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-700">
            {templates.map((template, index) => (
              <div key={index} className="p-4 hover:bg-dark-700 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span className="text-2xl">{getFileIcon(template.extension)}</span>
                    <div>
                      <h4 className="font-medium text-white">{template.file_name}</h4>
                      <p className="text-sm text-gray-400">{template.file_path}</p>
                      <div className="flex items-center space-x-4 mt-1">
                        <Badge variant="outline" className="bg-primary-500/20 text-primary-400 border-primary-500/30">{template.section_id}</Badge>
                        <span className="text-xs text-gray-500">{formatFileSize(template.size)}</span>
                        <span className="text-xs text-gray-500">Modified: {formatDate(template.modified)}</span>
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => handleDownload(template)}
                      className="p-2 text-gray-400 hover:text-blue-400 hover:bg-blue-500/20 rounded-md transition-colors"
                      title="Download"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleEdit(template)}
                      className="p-2 text-gray-400 hover:text-green-400 hover:bg-green-500/20 rounded-md transition-colors"
                      title="Edit"
                    >
                      <Edit className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(template)}
                      className="p-2 text-gray-400 hover:text-red-400 hover:bg-red-500/20 rounded-md transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {showEditModal && selectedTemplate && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
          <div className="bg-dark-800 rounded-lg shadow-xl w-[95vw] h-[95vh] flex flex-col border border-gray-700">
            <div className="p-4 border-b border-gray-700 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">Edit Template: {selectedTemplate.file_name}</h3>
              <button
                onClick={() => setShowEditModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                ✕
              </button>
            </div>
            
            <div className="flex-1 p-4 overflow-hidden">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-full resize-none bg-dark-700 border border-gray-600 rounded-md p-3 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-gray-300"
                placeholder="Template content..."
              />
            </div>
            
            <div className="p-4 border-t border-gray-700 flex items-center justify-end space-x-3">
              <button
                onClick={() => setShowEditModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}