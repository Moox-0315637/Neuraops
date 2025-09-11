import * as React from 'react'
import { cn } from '@/lib/utils'

const inputVariants = {
  variant: {
    default: 'neuraops-input',
    ghost: 'bg-transparent border-transparent focus:bg-dark-tertiary focus:border-gray-700',
    filled: 'bg-dark-800 border-dark-700 focus:border-primary-500',
  },
  size: {
    sm: 'h-8 px-3 text-xs',
    default: 'h-9 px-3 text-sm',
    lg: 'h-10 px-4 text-base',
  },
}

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  variant?: keyof typeof inputVariants.variant
  inputSize?: keyof typeof inputVariants.size
  error?: boolean
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ 
    className, 
    type, 
    variant = 'default',
    inputSize = 'default',
    error = false,
    icon,
    iconPosition = 'left',
    ...props 
  }, ref) => {
    if (icon) {
      return (
        <div className="relative">
          {iconPosition === 'left' && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
              {icon}
            </div>
          )}
          <input
            type={type}
            className={cn(
              inputVariants.variant[variant],
              inputVariants.size[inputSize],
              iconPosition === 'left' && 'pl-10',
              iconPosition === 'right' && 'pr-10',
              error && 'border-red-500 focus:border-red-500 focus:ring-red-500',
              className
            )}
            ref={ref}
            {...props}
          />
          {iconPosition === 'right' && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
              {icon}
            </div>
          )}
        </div>
      )
    }

    return (
      <input
        type={type}
        className={cn(
          inputVariants.variant[variant],
          inputVariants.size[inputSize],
          error && 'border-red-500 focus:border-red-500 focus:ring-red-500',
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'

export { Input, inputVariants }