/**
 * NeuraOps User Menu Component
 * Dropdown menu with user info and logout functionality
 */
'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { LogOut, Settings, User, Shield } from 'lucide-react'
import { authService } from '@/lib/auth-service'

interface UserInfo {
  username?: string
  email?: string
  role?: string
}

export default function UserMenu() {
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [userInfo, setUserInfo] = useState<UserInfo>({})
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  // Fetch user info on component mount
  useEffect(() => {
    const fetchUserInfo = async () => {
      try {
        const user = await authService.getCurrentUser()
        if (user) {
          setUserInfo({
            username: user.username,
            email: user.email,
            role: user.role
          })
        } else {
          // Fallback to generic user info
          setUserInfo({
            username: 'User',
            email: 'user@neuraops.com',
            role: 'user'
          })
        }
      } catch (error) {
        console.error('Failed to fetch user info:', error)
        // Use fallback values
        setUserInfo({
          username: 'User',
          email: 'user@neuraops.com', 
          role: 'user'
        })
      } finally {
        setIsLoading(false)
      }
    }

    fetchUserInfo()
  }, [])

  const handleLogout = async () => {
    setIsLoggingOut(true)
    try {
      await authService.logout()
      router.push('/login')
    } catch (error) {
      console.error('Logout failed:', error)
      // Force redirect even if logout API call fails
      router.push('/login')
    } finally {
      setIsLoggingOut(false)
    }
  }

  const getUserInitial = () => {
    return userInfo.username?.[0]?.toUpperCase() || 'U'
  }

  const getRoleBadgeColor = () => {
    switch (userInfo.role) {
      case 'admin':
        return 'bg-red-600'
      case 'user':
        return 'bg-blue-600'
      case 'viewer':
        return 'bg-gray-600'
      default:
        return 'bg-primary-600'
    }
  }

  if (isLoading) {
    return (
      <div className="h-8 w-8 rounded-full bg-gray-700 animate-pulse" />
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          className="relative h-8 w-8 rounded-full hover:bg-dark-700"
        >
          <Avatar className="h-8 w-8">
            <AvatarFallback className={`${getRoleBadgeColor()} text-white text-sm font-medium`}>
              {getUserInitial()}
            </AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent 
        className="w-64 bg-dark-800 border-gray-700" 
        align="end"
      >
        {/* User Info Header */}
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1 p-2">
            <div className="flex items-center gap-2">
              <p className="text-sm font-medium leading-none text-white">
                {userInfo.username || 'Unknown User'}
              </p>
              {userInfo.role && (
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium text-white ${getRoleBadgeColor()}`}>
                  {userInfo.role}
                </span>
              )}
            </div>
            <p className="text-xs leading-none text-gray-400">
              {userInfo.email || 'No email'}
            </p>
          </div>
        </DropdownMenuLabel>
        
        <DropdownMenuSeparator className="bg-gray-700" />
        
        {/* Menu Items */}
        <DropdownMenuItem 
          onClick={() => router.push('/settings')}
          className="text-gray-300 hover:bg-dark-700 hover:text-white cursor-pointer"
        >
          <Settings className="mr-2 h-4 w-4" />
          <span>Settings</span>
        </DropdownMenuItem>
        
        <DropdownMenuItem 
          onClick={() => router.push('/profile')}
          className="text-gray-300 hover:bg-dark-700 hover:text-white cursor-pointer"
        >
          <User className="mr-2 h-4 w-4" />
          <span>Profile</span>
        </DropdownMenuItem>
        
        {userInfo.role === 'admin' && (
          <DropdownMenuItem 
            onClick={() => router.push('/admin')}
            className="text-gray-300 hover:bg-dark-700 hover:text-white cursor-pointer"
          >
            <Shield className="mr-2 h-4 w-4" />
            <span>Admin Panel</span>
          </DropdownMenuItem>
        )}
        
        <DropdownMenuSeparator className="bg-gray-700" />
        
        {/* Logout */}
        <DropdownMenuItem 
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="text-red-400 hover:bg-red-950/50 hover:text-red-300 cursor-pointer focus:bg-red-950/50 focus:text-red-300"
        >
          <LogOut className="mr-2 h-4 w-4" />
          <span>{isLoggingOut ? 'Signing out...' : 'Sign Out'}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}