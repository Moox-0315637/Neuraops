import React from 'react'
import { cn } from '@/lib/utils'

interface AvatarProps {
  className?: string
  children: React.ReactNode
}

interface AvatarFallbackProps {
  className?: string
  children: React.ReactNode
}

interface AvatarImageProps {
  src: string
  alt: string
  className?: string
}

export function Avatar({ className, children }: AvatarProps) {
  return (
    <div
      className={cn(
        'relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full',
        className
      )}
    >
      {children}
    </div>
  )
}

export function AvatarImage({ src, alt, className }: AvatarImageProps) {
  return (
    <img
      className={cn('aspect-square h-full w-full', className)}
      src={src}
      alt={alt}
    />
  )
}

export function AvatarFallback({ className, children }: AvatarFallbackProps) {
  return (
    <div
      className={cn(
        'flex h-full w-full items-center justify-center rounded-full bg-slate-100 text-slate-900',
        className
      )}
    >
      {children}
    </div>
  )
}