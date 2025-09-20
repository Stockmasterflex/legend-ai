import * as React from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        'flex h-10 w-full rounded-md border border-slate-600 bg-slate-900 px-3 py-2 text-sm text-white',
        'placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-cyan-400',
        className
      )}
      {...props}
    />
  )
)
Input.displayName = 'Input'
