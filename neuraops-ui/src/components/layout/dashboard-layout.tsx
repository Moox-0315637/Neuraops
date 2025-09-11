/**
 * NeuraOps Dashboard Layout
 * Reusable layout component with sidebar and header
 * Fixed positioning with proper content spacing
 */
'use client'

import { ReactNode } from 'react'
import Sidebar from './sidebar'
import Header from './header'

interface DashboardLayoutProps {
  readonly children: ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-dark-900">
      {/* Fixed Sidebar */}
      <Sidebar />
      
      {/* Main Content Area - with left padding to accommodate fixed sidebar */}
      <div className="pl-64"> {/* pl-64 matches w-64 of sidebar */}
        {/* Header - sticky within the main content area */}
        <Header />
        
        {/* Page Content Container */}
        <main className="p-6 max-w-none">
          <div className="mx-auto"> {/* Use mx-auto for better centering */}
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}