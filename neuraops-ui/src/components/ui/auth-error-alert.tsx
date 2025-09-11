/**
 * Authentication Error Alert Component
 * Displays authentication-related errors with helpful actions
 */
'use client'

import React from 'react'
import { AlertTriangle, Settings, RefreshCw } from 'lucide-react'
import Link from 'next/link'

interface AuthErrorAlertProps {
  error: string
  onRetry?: () => void
  showSettingsLink?: boolean
}

export default function AuthErrorAlert({ 
  error, 
  onRetry, 
  showSettingsLink = true 
}: AuthErrorAlertProps) {
  const isAuthError = error.includes('Authentication required') || 
                      error.includes('Access forbidden') ||
                      error.includes('401') ||
                      error.includes('403')

  if (!isAuthError) {
    // Standard error display for non-auth errors
    return (
      <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-6">
        <div className="flex items-center">
          <AlertTriangle className="w-6 h-6 text-red-500 mr-3" />
          <div className="flex-1">
            <h3 className="text-lg font-medium text-red-400">Error</h3>
            <p className="text-red-300 mt-1">{error}</p>
            {onRetry && (
              <button 
                onClick={onRetry}
                className="mt-3 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
              >
                Retry
              </button>
            )}
          </div>
        </div>
      </div>
    )
  }

  // Enhanced auth error display
  return (
    <div className="bg-orange-900/20 border border-orange-500/50 rounded-lg p-6">
      <div className="flex items-start">
        <AlertTriangle className="w-6 h-6 text-orange-500 mr-3 mt-0.5" />
        <div className="flex-1">
          <h3 className="text-lg font-medium text-orange-400">Authentication Required</h3>
          <p className="text-orange-300 mt-1">{error}</p>
          
          <div className="mt-4 space-y-2">
            <p className="text-sm text-orange-200">
              To access NeuraOps data, you need to configure your API authentication token.
            </p>
            
            <div className="flex items-center space-x-3 mt-4">
              {showSettingsLink && (
                <Link
                  href="/settings"
                  className="inline-flex items-center space-x-2 bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
                >
                  <Settings className="w-4 h-4" />
                  <span>Configure API Token</span>
                </Link>
              )}
              
              {onRetry && (
                <button 
                  onClick={onRetry}
                  className="inline-flex items-center space-x-2 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg text-sm transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  <span>Retry</span>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}