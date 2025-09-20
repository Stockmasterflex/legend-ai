import * as React from 'react'
import { cn } from '@/lib/utils'

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'secondary' | 'outline'
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  const classes = cn(
    'inline-flex items-center rounded-full px-3 py-1 text-xs font-medium',
    variant === 'default' && 'bg-green-600 text-white',
    variant === 'secondary' && 'bg-slate-700 text-white',
    variant === 'outline' && 'border border-slate-600 text-slate-300',
    className
  )
  return <span className={classes} {...props} />
}
