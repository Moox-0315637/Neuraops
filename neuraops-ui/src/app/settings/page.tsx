/**
 * NeuraOps Settings Page
 * Application and user settings configuration with API setup
 */
import { Metadata } from 'next'
import DashboardLayout from '@/components/layout/dashboard-layout'
import SettingsPageClient from '@/components/features/settings/settings-page-client'

export const metadata: Metadata = {
  title: 'Settings',
  description: 'Configure your NeuraOps settings and preferences'
}

export default function SettingsPage() {
  return (
    <DashboardLayout>
      <SettingsPageClient />
    </DashboardLayout>
  )
}