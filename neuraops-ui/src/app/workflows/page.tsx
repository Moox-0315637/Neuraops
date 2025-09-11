/**
 * NeuraOps Workflows Page
 * Workflow automation management interface with real API data
 */
import { Metadata } from 'next'
import DashboardLayout from '@/components/layout/dashboard-layout'
import WorkflowsView from '@/components/features/workflows/workflows-view'

export const metadata: Metadata = {
  title: 'Workflows',
  description: 'Create and manage automated DevOps workflows and processes'
}

export default function WorkflowsPage() {
  return (
    <DashboardLayout>
      <WorkflowsView />
    </DashboardLayout>
  )
}