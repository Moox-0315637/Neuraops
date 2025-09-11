/**
 * NeuraOps Login Page
 * Secure authentication with form validation and error handling
 */
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { AlertCircle, Eye, EyeOff, Loader2 } from 'lucide-react'
import { authService } from '@/lib/auth-service'

interface FormErrors {
  username?: string
  password?: string
  general?: string
}

export default function LoginPage() {
  const [credentials, setCredentials] = useState({
    username: '',
    password: ''
  })
  const [isLoading, setIsLoading] = useState(false)
  const [errors, setErrors] = useState<FormErrors>({})
  const [showPassword, setShowPassword] = useState(false)
  const [isCheckingAuth, setIsCheckingAuth] = useState(true)
  const router = useRouter()

  // Check if user is already authenticated
  useEffect(() => {
    const checkAuth = async () => {
      try {
        if (authService.isAuthenticated()) {
          // Validate current token
          await authService.validateToken()
          router.push('/')
          return
        }
      } catch (error) {
        // Token invalid, stay on login page
        console.log('No valid authentication, showing login')
      } finally {
        setIsCheckingAuth(false)
      }
    }

    checkAuth()
  }, [router])

  const validateForm = (): boolean => {
    const newErrors: FormErrors = {}

    if (!credentials.username.trim()) {
      newErrors.username = 'Username is required'
    } else if (credentials.username.length < 2) {
      newErrors.username = 'Username must be at least 2 characters'
    }

    if (!credentials.password) {
      newErrors.password = 'Password is required'
    } else if (credentials.password.length < 3) {
      newErrors.password = 'Password must be at least 3 characters'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateForm()) {
      return
    }

    setIsLoading(true)
    setErrors({})

    try {
      console.log('🔐 Attempting login...')
      await authService.login(credentials.username, credentials.password)
      console.log('✅ Login successful, redirecting...')
      router.push('/')
    } catch (error) {
      console.error('❌ Login failed:', error)
      
      let errorMessage = 'Login failed. Please try again.'
      
      if (error instanceof Error) {
        if (error.message.includes('401') || error.message.includes('Unauthorized')) {
          errorMessage = 'Invalid username or password'
        } else if (error.message.includes('Network')) {
          errorMessage = 'Network error. Please check your connection.'
        } else {
          errorMessage = error.message
        }
      }
      
      setErrors({ general: errorMessage })
    } finally {
      setIsLoading(false)
    }
  }

  // Show loading spinner while checking auth
  if (isCheckingAuth) {
    return (
      <div className="min-h-screen bg-dark-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500 mx-auto mb-4" />
          <p className="text-gray-400">Checking authentication...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <Card className="shadow-xl bg-dark-800 border border-gray-700">
          <CardHeader className="text-center pb-6">
            <div className="mx-auto mb-6 h-12 w-12 rounded-lg bg-primary-600 flex items-center justify-center">
              <span className="text-xl font-bold text-white">N</span>
            </div>
            <CardTitle className="text-2xl font-bold text-white mb-2">NeuraOps</CardTitle>
            <CardDescription className="text-gray-400">
              AI-Powered DevOps Platform
            </CardDescription>
          </CardHeader>
        
          <CardContent className="px-6 pb-6">
            <form onSubmit={handleSubmit} className="space-y-5">
              {errors.general && (
                <div className="flex items-center gap-2 p-3 text-sm text-red-400 bg-red-950/50 border border-red-800 rounded-lg">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{errors.general}</span>
                </div>
              )}
            
              <div className="space-y-2">
                <label htmlFor="username" className="block text-sm font-medium text-gray-300">
                  Username
                </label>
                <Input
                id="username"
                type="text"
                placeholder="Enter your username"
                value={credentials.username}
                onChange={(e) => {
                  setCredentials({...credentials, username: e.target.value})
                  if (errors.username) {
                    setErrors({...errors, username: undefined})
                  }
                }}
                className={`bg-dark-800 border-gray-700 text-white placeholder-gray-500 ${
                  errors.username ? 'border-red-500 focus:border-red-500' : 'focus:border-primary-500'
                }`}
                required
                disabled={isLoading}
                autoComplete="username"
              />
              {errors.username && (
                <p className="text-sm text-red-400">{errors.username}</p>
              )}
              </div>
              
              <div className="space-y-2">
                <label htmlFor="password" className="block text-sm font-medium text-gray-300">
                  Password
                </label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  value={credentials.password}
                  onChange={(e) => {
                    setCredentials({...credentials, password: e.target.value})
                    if (errors.password) {
                      setErrors({...errors, password: undefined})
                    }
                  }}
                  className={`bg-dark-800 border-gray-700 text-white placeholder-gray-500 pr-10 ${
                    errors.password ? 'border-red-500 focus:border-red-500' : 'focus:border-primary-500'
                  }`}
                  required
                  disabled={isLoading}
                  autoComplete="current-password"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                >
                  {showPassword ? (
                    <EyeOff className="h-4 w-4 text-gray-400" />
                  ) : (
                    <Eye className="h-4 w-4 text-gray-400" />
                  )}
                </Button>
              </div>
                {errors.password && (
                  <p className="text-sm text-red-400">{errors.password}</p>
                )}
              </div>
              
              <Button 
                type="submit" 
                className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2.5 mt-6"
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Signing in...
                  </div>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>
            
            {/* Development environment only - remove in production */}
            {process.env.NODE_ENV === 'development' && (
              <div className="mt-6 pt-4 border-t border-gray-700 text-center">
                <p className="text-sm text-gray-500">
                  Development Mode - Check your .env file for credentials
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}