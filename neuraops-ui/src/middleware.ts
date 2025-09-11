/**
 * NeuraOps Route Protection Middleware
 * Next.js 15 middleware for authentication-based routing
 * Protects sensitive pages and redirects unauthenticated users
 */
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Routes that don't require authentication
const publicRoutes = [
  '/login',
]

// Routes that require authentication
const protectedRoutes = [
  '/',
  '/agents',
  '/workflows', 
  '/monitoring',
  '/settings',
  '/documentation',
  '/cli'
]

// API routes that should not be intercepted
const apiRoutes = [
  '/api',
  '/_next',
  '/favicon.ico'
]

/**
 * Check if a path matches any of the route patterns
 */
function matchesRoute(pathname: string, routes: string[]): boolean {
  return routes.some(route => {
    if (route === pathname) return true
    if (pathname.startsWith(route + '/')) return true
    return false
  })
}

/**
 * Get authentication token from request
 */
function getAuthToken(request: NextRequest): string | null {
  // Try to get token from cookie first (more secure)
  const cookieToken = request.cookies.get('neuraops_auth_token')?.value
  if (cookieToken) return cookieToken

  // Fallback to Authorization header
  const authHeader = request.headers.get('authorization')
  if (authHeader?.startsWith('Bearer ')) {
    return authHeader.replace('Bearer ', '')
  }

  return null
}

/**
 * Main middleware function
 */
export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  
  // Skip middleware for API routes, static files, and Next.js internals
  if (matchesRoute(pathname, apiRoutes)) {
    return NextResponse.next()
  }
  
  const token = getAuthToken(request)
  const isProtectedRoute = matchesRoute(pathname, protectedRoutes)
  const isPublicRoute = matchesRoute(pathname, publicRoutes)
  
  // Redirect to login if accessing protected route without token
  if (isProtectedRoute && !token) {
    console.log(`🔒 Redirecting to login - no token for protected route: ${pathname}`)
    const loginUrl = new URL('/login', request.url)
    // Add return URL for post-login redirect
    loginUrl.searchParams.set('returnUrl', pathname)
    return NextResponse.redirect(loginUrl)
  }
  
  // Redirect authenticated users away from login page
  if (isPublicRoute && pathname === '/login' && token) {
    console.log(`🔓 Redirecting authenticated user away from login`)
    const returnUrl = request.nextUrl.searchParams.get('returnUrl') || '/'
    const redirectUrl = new URL(returnUrl, request.url)
    return NextResponse.redirect(redirectUrl)
  }

  // Allow the request to proceed
  return NextResponse.next()
}

/**
 * Configure which paths the middleware should run on
 * Excludes API routes, static files, and Next.js internal routes
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}