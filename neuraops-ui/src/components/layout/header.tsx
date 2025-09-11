'use client'

import { useState } from 'react'
import { Search, Bell } from 'lucide-react'
import { Button, Input, Badge } from '@/components/ui'
import { cn } from '@/lib/utils'
import UserMenu from './user-menu'

interface HeaderProps {
  readonly title?: string
  readonly subtitle?: string
}

export default function Header({ title, subtitle }: HeaderProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [showNotifications, setShowNotifications] = useState(false)

  // Mock data
  const notifications = [
    { id: 1, title: 'System Alert', message: 'CPU usage high on server-01', time: '2 min ago', unread: true },
    { id: 2, title: 'Workflow Complete', message: 'CI/CD pipeline finished successfully', time: '5 min ago', unread: true },
    { id: 3, title: 'Agent Connected', message: 'New agent registered: prod-agent-04', time: '10 min ago', unread: false },
  ]

  const unreadCount = notifications.filter(n => n.unread).length

  return (
    <header className="sticky top-0 z-30 w-full border-b border-gray-800 bg-dark-secondary">
      <div className="container mx-auto px-6"> {/* Use container with proper padding */}
        <div className="flex h-16 items-center justify-between">
          {/* Title Section */}
          <div className="flex items-center space-x-4">
            {title && (
              <div>
                <h1 className="text-xl font-semibold text-white">{title}</h1>
                {subtitle && (
                  <p className="text-sm text-gray-400">{subtitle}</p>
                )}
              </div>
            )}
          </div>

          {/* Search and Actions */}
          <div className="flex items-center space-x-4">
            {/* Search */}
            <div className="relative hidden md:block">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <Input
                placeholder="Search commands, agents, workflows..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-80 pl-10 pr-4 bg-dark-800 border-gray-700 text-white placeholder-gray-400 focus:border-primary-500 focus:ring-primary-500"
              />
            </div>

            {/* Mobile Search Button */}
            <Button
              variant="ghost"
              size="sm"
              className="md:hidden text-gray-400 hover:text-white hover:bg-gray-800"
            >
              <Search className="h-5 w-5" />
            </Button>

            {/* Notifications */}
            <div className="relative">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative text-gray-400 hover:text-white hover:bg-gray-800"
              >
                <Bell className="h-5 w-5" />
                {unreadCount > 0 && (
                  <Badge
                    variant="destructive"
                    className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 text-xs"
                  >
                    {unreadCount}
                  </Badge>
                )}
              </Button>

              {/* Notifications Dropdown */}
              {showNotifications && (
                <div className="absolute right-0 top-full mt-2 w-80 rounded-lg border border-gray-700 bg-dark-800 p-4 shadow-lg z-50">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-white">Notifications</h3>
                    <Button variant="ghost" size="sm" className="text-xs text-gray-400 hover:text-white">
                      Mark all read
                    </Button>
                  </div>
                  <div className="space-y-3 max-h-64 overflow-y-auto">
                    {notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={cn(
                          'p-3 rounded-lg cursor-pointer transition-colors',
                          notification.unread
                            ? 'bg-primary-500/10 border border-primary-500/20'
                            : 'bg-gray-800/50 hover:bg-gray-800'
                        )}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <p className="font-medium text-white text-sm">{notification.title}</p>
                            <p className="text-gray-400 text-xs mt-1">{notification.message}</p>
                          </div>
                          <span className="text-xs text-gray-500 ml-2">{notification.time}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* User Menu */}
            <UserMenu />
          </div>
        </div>
      </div>
    </header>
  )
}