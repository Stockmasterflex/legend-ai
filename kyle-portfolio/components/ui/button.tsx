import * as React from "react"
import { cn } from "@/lib/utils"

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'secondary'
  size?: 'default' | 'sm' | 'lg'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    const variantClass =
      variant === 'outline'
        ? 'border border-slate-600 bg-transparent hover:bg-slate-800'
        : variant === 'secondary'
        ? 'bg-slate-700 text-white hover:bg-slate-600'
        : 'bg-green-600 text-white hover:bg-green-700'
    const sizeClass =
      size === 'sm' ? 'h-8 px-3 text-sm' : size === 'lg' ? 'h-11 px-8' : 'h-10 px-4 py-2'
    return (
      <button
        className={cn(
          'inline-flex items-center justify-center rounded-md font-medium transition-colors disabled:pointer-events-none disabled:opacity-50',
          variantClass,
          sizeClass,
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = 'Button'

export { Button }
