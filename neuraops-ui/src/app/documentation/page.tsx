/**
 * NeuraOps Documentation Page
 * Infrastructure as Code templates and DevOps examples with real API data
 */
import { Metadata } from 'next'
import DashboardLayout from '@/components/layout/dashboard-layout'
import DocumentationView from '@/components/features/documentation/documentation-view'

export const metadata: Metadata = {
  title: 'Documentation',
  description: 'Infrastructure as Code templates and DevOps examples'
}

export default function DocumentationPage() {
  return (
    <DashboardLayout>
      <DocumentationView />
    </DashboardLayout>
  )
}
