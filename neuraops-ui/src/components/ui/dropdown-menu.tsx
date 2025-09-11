'use client'

import React, { useState, useRef, useEffect } from 'react'

interface DropdownMenuProps {
  children: React.ReactNode
}

interface DropdownMenuTriggerProps {
  asChild?: boolean
  children: React.ReactNode
}

interface DropdownMenuContentProps {
  className?: string
  align?: 'start' | 'center' | 'end'
  forceMount?: boolean
  children: React.ReactNode
}

interface DropdownMenuItemProps {
  className?: string
  onClick?: () => void
  disabled?: boolean
  children: React.ReactNode
}

interface DropdownMenuLabelProps {
  className?: string
  children: React.ReactNode
}

interface DropdownMenuSeparatorProps {
  className?: string
}

const DropdownMenuContext = React.createContext<{
  open: boolean
  setOpen: (open: boolean) => void
}>({
  open: false,
  setOpen: () => {}
})

export function DropdownMenu({ children }: DropdownMenuProps) {
  const [open, setOpen] = useState(false)
  
  return (
    <DropdownMenuContext.Provider value={{ open, setOpen }}>
      <div className="relative">{children}</div>
    </DropdownMenuContext.Provider>
  )
}

export function DropdownMenuTrigger({ asChild, children }: DropdownMenuTriggerProps) {
  const { open, setOpen } = React.useContext(DropdownMenuContext)
  
  const handleClick = () => {
    setOpen(!open)
  }

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      onClick: handleClick,
      'aria-expanded': open,
      'aria-haspopup': 'menu'
    })
  }

  return (
    <button
      onClick={handleClick}
      aria-expanded={open}
      aria-haspopup="menu"
    >
      {children}
    </button>
  )
}

export function DropdownMenuContent({ 
  className = '', 
  align = 'end', 
  forceMount, 
  children 
}: DropdownMenuContentProps) {
  const { open, setOpen } = React.useContext(DropdownMenuContext)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open, setOpen])

  if (!open && !forceMount) return null

  const alignmentClass = align === 'start' ? 'left-0' : align === 'center' ? 'left-1/2 -translate-x-1/2' : 'right-0'

  return (
    <div
      ref={ref}
      className={`absolute top-full mt-2 z-50 min-w-[8rem] overflow-hidden rounded-md border border-gray-700 bg-dark-800 p-1 text-white shadow-md ${alignmentClass} ${className}`}
    >
      {children}
    </div>
  )
}

export function DropdownMenuItem({ 
  className = '', 
  onClick, 
  disabled, 
  children 
}: DropdownMenuItemProps) {
  const { setOpen } = React.useContext(DropdownMenuContext)
  
  const handleClick = () => {
    if (!disabled && onClick) {
      onClick()
      setOpen(false)
    }
  }

  return (
    <div
      onClick={handleClick}
      className={`relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-gray-700 focus:bg-gray-700 text-gray-300 hover:text-white ${disabled ? 'pointer-events-none opacity-50' : ''} ${className}`}
    >
      {children}
    </div>
  )
}

export function DropdownMenuLabel({ className = '', children }: DropdownMenuLabelProps) {
  return (
    <div className={`px-2 py-1.5 text-sm font-semibold ${className}`}>
      {children}
    </div>
  )
}

export function DropdownMenuSeparator({ className = '' }: DropdownMenuSeparatorProps) {
  return <div className={`-mx-1 my-1 h-px bg-gray-700 ${className}`} />
}