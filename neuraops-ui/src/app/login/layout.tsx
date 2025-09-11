/**
 * Login Layout - Simple layout without dashboard components
 * Prevents sidebar and header from showing on login page
 */
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Login | NeuraOps',
  description: 'Sign in to your NeuraOps AI-powered DevOps platform',
}

interface LoginLayoutProps {
  children: React.ReactNode
}

export default function LoginLayout({ children }: LoginLayoutProps) {
  // Return children directly without DashboardLayout wrapper
  // This ensures clean login page without sidebar/header
  return children
}