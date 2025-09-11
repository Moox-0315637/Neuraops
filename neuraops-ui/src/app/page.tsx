import type { Metadata } from 'next'
import DashboardLayout from '@/components/layout/dashboard-layout'
import Dashboard from '@/components/features/dashboard/dashboard'

export const metadata: Metadata = {
  title: 'Dashboard',
  description: 'NeuraOps AI-powered DevOps operations dashboard with real-time monitoring and insights.',
}

export default function DashboardPage() {
  return (
    <DashboardLayout>
      <Dashboard />
    </DashboardLayout>
  )
}