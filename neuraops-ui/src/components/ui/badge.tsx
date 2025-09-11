import * as React from 'react'
import { cn } from '@/lib/utils'

const badgeVariants = {
  variant: {
    default: 'bg-primary-500 text-white hover:bg-primary-600',
    secondary: 'bg-gray-700 text-white hover:bg-gray-600',
    destructive: 'bg-red-500 text-white hover:bg-red-600',
    success: 'bg-green-500 text-white hover:bg-green-600',
    warning: 'bg-yellow-500 text-black hover:bg-yellow-600',
    outline: 'border border-gray-600 text-gray-300 bg-transparent hover:bg-gray-800',
    status: {
      online: 'bg-green-500 text-white',
      offline: 'bg-gray-500 text-white',
      error: 'bg-red-500 text-white',
      warning: 'bg-yellow-500 text-black',
      maintenance: 'bg-blue-500 text-white',
    },
  },
  size: {
    default: 'px-2.5 py-0.5 text-xs',
    sm: 'px-2 py-0.5 text-xs',
    lg: 'px-3 py-1 text-sm',
  },
}

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement> {
  readonly variant?: keyof typeof badgeVariants.variant | keyof typeof badgeVariants.variant.status
  readonly size?: keyof typeof badgeVariants.size
  readonly dot?: boolean
}

function Badge({ 
  className, 
  variant = 'default', 
  size = 'default',
  dot = false,
  children,
  ...props 
}: BadgeProps) {
  // Handle status variants
  const getVariantClass = () => {
    if (variant in badgeVariants.variant.status) {
      return badgeVariants.variant.status[variant as keyof typeof badgeVariants.variant.status]
    }
    return badgeVariants.variant[variant as keyof typeof badgeVariants.variant]
  }

  return (
    <div
      className={cn(
        'inline-flex items-center rounded-full border font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2',
        getVariantClass(),
        badgeVariants.size[size],
        dot && 'gap-1.5',
        className
      )}
      {...props}
    >
      {dot && (
        <div className={cn(
          'h-1.5 w-1.5 rounded-full',
          variant === 'online' && 'bg-white',
          variant === 'offline' && 'bg-white',
          variant === 'error' && 'bg-white',
          variant === 'warning' && 'bg-black',
          variant === 'maintenance' && 'bg-white',
        )} />
      )}
      {children}
    </div>
  )
}

export { Badge, badgeVariants }