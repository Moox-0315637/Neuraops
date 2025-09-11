/* eslint-disable react/no-unescaped-entities */
/**
 * NeuraOps CLI Page
 * Interactive command-line interface for DevOps operations
 */
import { Metadata } from 'next'
import DashboardLayout from '@/components/layout/dashboard-layout'
import DynamicCLITerminal from '@/components/features/cli/dynamic-cli-terminal'
import GeneratedFiles from '@/components/features/cli/generated-files'

export const metadata: Metadata = {
  title: 'CLI',
  description: 'Interactive command-line interface for DevOps operations'
}

export default function CLIPage() {
  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-white">NeuraOps CLI</h1>
          <p className="text-gray-400 mt-2">
            Interactive command-line interface for DevOps operations
          </p>
        </div>

        {/* Enlarged CLI Terminal */}
        <div className="bg-dark-800 rounded-lg border border-gray-700 overflow-hidden">
          <DynamicCLITerminal />
        </div>

        {/* Generated Files Section */}
        <div className="bg-dark-800 rounded-lg border border-gray-700 p-4">
          <GeneratedFiles />
        </div>
      </div>
    </DashboardLayout>
  )
}
