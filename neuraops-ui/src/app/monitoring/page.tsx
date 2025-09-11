/**
 * NeuraOps Monitoring Page
 * System monitoring and metrics dashboard with real-time API data
 */
import { Metadata } from 'next'
import DashboardLayout from '@/components/layout/dashboard-layout'
import MonitoringDashboard from '@/components/monitoring/monitoring-dashboard'

export const metadata: Metadata = {
  title: 'Monitoring',
  description: 'Monitor system health, performance metrics, and infrastructure status'
}

export default function MonitoringPage() {
  return (
    <DashboardLayout>
      <MonitoringDashboard />
    </DashboardLayout>
  )
}