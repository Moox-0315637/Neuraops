/**
 * Authentication Initializer Component
 * Handles authentication state and redirects for protected routes
 */
'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { authService } from '@/lib/auth-service'

export default function AuthInitializer() {
  const pathname = usePathname()
  const router = useRouter()
  
  useEffect(() => {
    const initAuth = async () => {
      // Skip auth check on login page
      if (pathname === '/login') {
        return
      }
      
      try {
        console.log('🔄 Checking authentication for:', pathname)
        
        // Check if authenticated
        if (!authService.isAuthenticated()) {
          console.log('❌ No valid token, redirecting to login')
          router.push('/login')
          return
        }
        
        // Validate token with API call
        console.log('🔍 Validating existing token...')
        try {
          await authService.validateToken()
          console.log('✅ Authentication validated')
        } catch (error) {
          console.log('❌ Token validation failed, redirecting to login')
          await authService.logout()
          router.push('/login')
        }
        
      } catch (error) {
        console.error('❌ Auth initialization failed:', error)
        router.push('/login')
      }
    }
    
    // Only run auth check after component mounts
    initAuth()
  }, [pathname, router])

  // This component doesn't render anything visible
  return null
}