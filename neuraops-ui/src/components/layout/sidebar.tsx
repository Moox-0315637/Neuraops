'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui'
import { apiService } from '@/services/api'
import {
  Home,
  Users,
  Workflow,
  Terminal,
  Book,
  BarChart3,
  Settings,
  Wifi,
  WifiOff
} from 'lucide-react'

interface NavigationItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  badgeKey?: 'agents' | 'monitoring'
}

const navigationItems: NavigationItem[] = [
  {
    name: 'Dashboard',
    href: '/',
    icon: Home,
  },
  {
    name: 'Agents',
    href: '/agents',
    icon: Users,
    badgeKey: 'agents',
  },
  {
    name: 'Workflows',
    href: '/workflows',
    icon: Workflow,
  },
  {
    name: 'CLI',
    href: '/cli',
    icon: Terminal,
  },
  {
    name: 'Documentation',
    href: '/documentation',
    icon: Book,
  },
  {
    name: 'Monitoring',
    href: '/monitoring',
    icon: BarChart3,
    badgeKey: 'monitoring',
  },
  {
    name: 'Settings',
    href: '/settings',
    icon: Settings,
  },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [badgeCounts, setBadgeCounts] = useState<Record<string, string>>({})

  // Mock connection status - in real app this would come from a store
  const isConnected = true

  useEffect(() => {
    const fetchBadgeCounts = async () => {
      try {
        // Fetch agents count
        const agents = await apiService.getAgents()
        const agentsCount = agents.length

        // Fetch alerts for monitoring count
        const alerts = await apiService.getAlerts()
        const activeAlerts = alerts.filter(alert => alert.status === 'open').length

        setBadgeCounts({
          agents: agentsCount.toString(),
          ...(activeAlerts > 0 && { monitoring: activeAlerts.toString() })
        })
      } catch (error) {
        console.error('Failed to fetch badge counts:', error)
        // Set fallback values on error
        setBadgeCounts({
          agents: '0'
        })
      }
    }

    fetchBadgeCounts()
    
    // Refresh badge counts every 5 minutes
    const interval = setInterval(fetchBadgeCounts, 300000)
    return () => clearInterval(interval)
  }, [])

  return (
    <aside className="fixed inset-y-0 left-0 z-40 w-64 bg-dark-secondary border-r border-gray-800 flex flex-col">
      {/* Logo Section - Fixed height */}
      <div className="flex h-16 items-center justify-between px-6 border-b border-gray-800">
        <div className="flex items-center space-x-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary-400 to-primary-600">
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5 text-white"
              fill="currentColor"
            >
              <path d="M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8Z" />
            </svg>
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">NeuraOps</h2>
            <p className="text-xs text-gray-400">v2.0.0</p>
          </div>
        </div>
      </div>

      {/* Navigation - Scrollable area */}
      <nav className="flex-1 overflow-y-auto py-6">
        <div className="px-3 space-y-1">
          {navigationItems.map((item) => {
            const isActive = pathname === item.href
            const Icon = item.icon
            const badgeValue = item.badgeKey ? badgeCounts[item.badgeKey] : undefined
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center justify-between rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-500 text-white shadow-sm'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )}
              >
                <div className="flex items-center space-x-3">
                  <Icon className="h-5 w-5 flex-shrink-0" />
                  <span>{item.name}</span>
                </div>
                {badgeValue && (
                  <Badge
                    variant={isActive ? 'secondary' : 'outline'}
                    className={cn(
                      'ml-auto text-xs',
                      isActive
                        ? 'bg-white/20 text-white border-white/20'
                        : 'bg-gray-800 text-gray-300 border-gray-600'
                    )}
                  >
                    {badgeValue}
                  </Badge>
                )}
              </Link>
            )
          })}
        </div>
      </nav>

      {/* Connection Status - Fixed at bottom */}
      <div className="border-t border-gray-800 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {isConnected ? (
              <>
                <Wifi className="h-4 w-4 text-green-400" />
                <span className="text-sm text-green-400">Connected</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-red-400" />
                <span className="text-sm text-red-400">Disconnected</span>
              </>
            )}
          </div>
          <div className="text-xs text-gray-500">
            All systems
          </div>
        </div>
        <div className="mt-2 text-xs text-gray-400">
          {isConnected ? (
            <span className="flex items-center space-x-1">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span>Dev Mode</span>
            </span>
          ) : (
            'Attempting to reconnect...'
          )}
        </div>
      </div>
    </aside>
  )
}