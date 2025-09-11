/**
 * NeuraOps Agents Page
 * Main agents management interface
 */
import { Metadata } from 'next'
import DashboardLayout from '@/components/layout/dashboard-layout'
import AgentsPageClient from '@/components/features/agents/agents-page-client'

export const metadata: Metadata = {
  title: 'Agents',
  description: 'Manage and monitor NeuraOps agents across your infrastructure'
}

export default function AgentsPage() {
  return (
    <DashboardLayout>
      <AgentsPageClient />
    </DashboardLayout>
  )
}