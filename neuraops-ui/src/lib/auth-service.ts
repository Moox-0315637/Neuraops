/**
 * Authentication Service
 * Handles login and token management for NeuraOps API
 */

import { apiService } from '@/services/api'

interface LoginResponse {
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
}

export class AuthService {
  private static instance: AuthService
  
  private constructor() {}
  
  static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService()
    }
    return AuthService.instance
  }
  
  /**
   * Login to NeuraOps API
   */
  async login(username: string, password: string): Promise<LoginResponse> {
    try {
      // Use apiService to make the login request with proper error handling
      const data = await apiService.login({ username, password })
      
      // The apiService.login already handles token storage and refresh
      return data
    } catch (error) {
      console.error('Login failed:', error)
      throw error
    }
  }
  
  /**
   * Auto-login with default credentials (deprecated - use manual login)
   */
  async autoLogin(): Promise<void> {
    try {
      // Check if we have a token and test if it's actually valid
      if (apiService.isAuthenticated()) {
        console.log('🔍 Found existing token, testing validity...')
        
        try {
          // Test with direct API call to protected endpoint
          await apiService.getSystemMetrics()
          
          console.log('✅ Existing token is valid')
          return
        } catch (tokenError) {
          console.log('❌ Existing token is invalid/expired, clearing...')
          // Clear the invalid token
          apiService.setToken(null)
        }
      }
      
      // No more automatic login - redirect to login page
      console.log('🔐 No valid token, user needs to login manually')
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    } catch (error) {
      console.error('❌ Auth check failed:', error)
      // Clear any potentially bad token
      apiService.setToken(null)
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
    }
  }

  /**
   * Validate current token by calling a protected endpoint
   */
  async validateToken(): Promise<void> {
    if (!this.isAuthenticated()) {
      throw new Error('No token available')
    }
    
    try {
      // Test with a simple protected endpoint
      await apiService.getSystemMetrics()
    } catch (error) {
      // Clear invalid token
      apiService.setToken(null)
      throw error
    }
  }
  
  /**
   * Get stored JWT authentication token (delegates to API service)
   */
  getToken(): string | null {
    return apiService.getCurrentToken()
  }
  
  /**
   * Enhanced logout with proper cleanup
   */
  async logout(): Promise<void> {
    try {
      console.log('🔓 Logging out...')
      // Call API logout endpoint if available
      await apiService.logout()
    } catch (error) {
      console.error('API logout failed:', error)
    } finally {
      // Always clear local token
      apiService.setToken(null)
      
      // Clear any cached data
      if (typeof window !== 'undefined') {
        localStorage.removeItem('neuraops_auth_token')
        localStorage.removeItem('neuraops-auth') // Zustand persist key
        sessionStorage.clear()
      }
      
      console.log('✅ Logout completed')
    }
  }

  /**
   * Get current user info from API
   */
  async getCurrentUser(): Promise<any> {
    try {
      if (!this.isAuthenticated()) return null
      
      return await apiService.getCurrentUser()
    } catch (error) {
      console.error('Failed to get current user:', error)
      return null
    }
  }
  
  /**
   * Check if user is authenticated (delegates to API service)
   */
  isAuthenticated(): boolean {
    return apiService.isAuthenticated()
  }
}

export const authService = AuthService.getInstance()