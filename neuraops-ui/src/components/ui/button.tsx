import * as React from 'react'
import { cn } from '@/lib/utils'

// Variant system inspired by ihmn-ui
const buttonVariants = {
  variant: {
    default:
      'bg-primary-500 text-white shadow hover:bg-primary-600 focus:ring-primary-500',
    destructive:
      'bg-red-500 text-white shadow-sm hover:bg-red-600 focus:ring-red-500',
    outline:
      'border border-gray-700 bg-transparent text-white shadow-sm hover:bg-gray-800 hover:text-white focus:ring-gray-700',
    secondary:
      'bg-gray-700 text-white shadow-sm hover:bg-gray-600 focus:ring-gray-700',
    ghost: 
      'text-gray-300 hover:bg-gray-800 hover:text-white focus:ring-gray-700',
    link: 
      'text-primary-400 underline-offset-4 hover:underline focus:ring-primary-400',
  },
  size: {
    default: 'h-9 px-4 py-2 text-sm',
    sm: 'h-8 px-3 py-1 text-xs',
    lg: 'h-10 px-6 py-2 text-base',
    xl: 'h-12 px-8 py-3 text-lg',
    icon: 'h-9 w-9 p-0',
  },
}

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: keyof typeof buttonVariants.variant
  size?: keyof typeof buttonVariants.size
  loading?: boolean
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
  fullWidth?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ 
    className, 
    variant = 'default', 
    size = 'default',
    loading = false,
    disabled,
    icon,
    iconPosition = 'left',
    fullWidth = false,
    children,
    ...props 
  }, ref) => {
    const isDisabled = Boolean(disabled ?? false) || Boolean(loading ?? false)
    
    return (
      <button
        className={cn(
          // Base styles
          'neuraops-button-base',
          // Variant styles
          buttonVariants.variant[variant],
          // Size styles
          buttonVariants.size[size],
          // Full width
          fullWidth && 'w-full',
          // Custom className
          className
        )}
        ref={ref}
        disabled={isDisabled}
        {...props}
      >
        {loading && (
          <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        
        {!loading && icon && iconPosition === 'left' && (
          <span className={cn('flex-shrink-0', children && 'mr-2')}>
            {icon}
          </span>
        )}
        
        {children && <span className="truncate">{children}</span>}
        
        {!loading && icon && iconPosition === 'right' && (
          <span className={cn('flex-shrink-0', children && 'ml-2')}>
            {icon}
          </span>
        )}
      </button>
    )
  }
)
Button.displayName = 'Button'

export { Button, buttonVariants }