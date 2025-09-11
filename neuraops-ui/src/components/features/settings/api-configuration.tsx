/**
 * API Configuration Component
 * Shows current API connection status with automatic authentication
 */
'use client'

import React, { useState, useEffect } from 'react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { 
  Check, 
  AlertTriangle, 
  Loader2,
  ExternalLink,
  Shield,
  Info
} from 'lucide-react'
import { apiService } from '@/services/api'
import { authService } from '@/lib/auth-service'

// Helper functions to reduce complexity
const getBadgeVariant = (connectionStatus: string) => {
  if (connectionStatus === 'success') return 'default'
  if (connectionStatus === 'error') return 'destructive'
  return 'secondary'
}

const getBadgeClassName = (connectionStatus: string) => {
  if (connectionStatus === 'success') return 'bg-green-500 text-white'
  if (connectionStatus === 'error') return 'bg-red-500 text-white'
  return 'bg-gray-500 text-white'
}

const getConnectionStatusText = (connectionStatus: string) => {
  if (connectionStatus === 'success') return 'Connected'
  if (connectionStatus === 'error') return 'Error'
  return 'Not Tested'
}

export default function ApiConfiguration() {
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    // Check initial authentication status
    setIsAuthenticated(authService.isAuthenticated())
  }, [])

  const handleTestConnection = async () => {
    setIsTestingConnection(true)
    setConnectionStatus('idle')
    setErrorMessage('')

    try {
      // Test connection with health check
      await apiService.healthCheck()
      setConnectionStatus('success')
      setIsAuthenticated(authService.isAuthenticated())
    } catch (error) {
      setConnectionStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Failed to connect to API')
    } finally {
      setIsTestingConnection(false)
    }
  }

  const handleReconnect = async () => {
    setIsTestingConnection(true)
    setErrorMessage('')
    
    try {
      // Force re-authentication
      await authService.autoLogin()
      await apiService.healthCheck()
      setConnectionStatus('success')
      setIsAuthenticated(true)
    } catch (error) {
      setConnectionStatus('error')
      setErrorMessage(error instanceof Error ? error.message : 'Failed to reconnect to API')
    } finally {
      setIsTestingConnection(false)
    }
  }

  const getCurrentApiUrl = () => {
    return process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold text-white mb-2">API Configuration</h2>
        <p className="text-gray-400">
          NeuraOps automatically authenticates with the API using secure credentials
        </p>
      </div>

      {/* Current API Status */}
      <Card className="p-6 bg-dark-secondary border-gray-700">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-white">Connection Status</h3>
          <Badge 
            variant={getBadgeVariant(connectionStatus)}
            className={getBadgeClassName(connectionStatus)}
          >
            {connectionStatus === 'success' && <Check className="w-3 h-3 mr-1" />}
            {connectionStatus === 'error' && <AlertTriangle className="w-3 h-3 mr-1" />}
            {getConnectionStatusText(connectionStatus)}
          </Badge>
        </div>
        
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-gray-400">API Endpoint:</span>
            <div className="flex items-center space-x-2">
              <code className="text-green-400 bg-black px-2 py-1 rounded text-xs">
                {getCurrentApiUrl()}
              </code>
              <ExternalLink className="w-4 h-4 text-gray-400" />
            </div>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-400">Authentication:</span>
            <span className={isAuthenticated ? 'text-green-400' : 'text-orange-400'}>
              {isAuthenticated ? 'JWT Token Active' : 'Not Authenticated'}
            </span>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-gray-400">Auto-Login:</span>
            <span className="text-blue-400">
              admin@neuraops.com
            </span>
          </div>
        </div>

        {errorMessage && (
          <div className="mt-4 p-3 bg-red-900/20 border border-red-500/50 rounded-lg">
            <p className="text-red-300 text-sm">{errorMessage}</p>
          </div>
        )}

        <div className="flex items-center space-x-3 mt-6">
          <Button
            onClick={handleTestConnection}
            disabled={isTestingConnection}
            variant="outline"
            className="border-gray-600 text-white hover:bg-gray-700"
          >
            {isTestingConnection ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              'Test Connection'
            )}
          </Button>

          <Button
            onClick={handleReconnect}
            disabled={isTestingConnection}
            className="bg-primary-500 hover:bg-primary-600 text-white"
          >
            {isTestingConnection ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Reconnecting...
              </>
            ) : (
              'Reconnect'
            )}
          </Button>
        </div>
      </Card>

      {/* Authentication Information */}
      <Card className="p-6 bg-dark-secondary border-gray-700">
        <div className="flex items-center space-x-2 mb-4">
          <Shield className="w-5 h-5 text-green-400" />
          <h3 className="text-lg font-medium text-white">Automatic Authentication</h3>
        </div>
        
        <div className="space-y-3 text-sm text-gray-300">
          <p>NeuraOps uses automatic authentication with the following features:</p>
          
          <ul className="list-disc list-inside space-y-1 ml-4">
            <li>Secure JWT token-based authentication</li>
            <li>Automatic login with admin credentials</li>
            <li>Token refresh and validation</li>
            <li>Secure storage in browser localStorage</li>
          </ul>
          
          <div className="mt-4 p-3 bg-blue-900/20 border border-blue-500/50 rounded-lg">
            <div className="flex items-start space-x-2">
              <Info className="w-4 h-4 text-blue-400 mt-0.5" />
              <div>
                <p className="text-blue-300 text-xs font-medium">Automatic Setup</p>
                <p className="text-blue-300 text-xs mt-1">
                  No manual configuration required. The app automatically connects 
                  to the NeuraOps API using secure credentials.
                </p>
              </div>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}