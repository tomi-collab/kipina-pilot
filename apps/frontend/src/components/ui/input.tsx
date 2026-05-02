import * as React from 'react'
import { cn } from '@/lib/utils'

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type = 'text', ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        className={cn(
          'flex min-h-12 w-full rounded-[var(--radius)] border bg-[var(--color-surface)] px-4 py-3 text-lg text-[var(--color-text)] placeholder:text-[var(--color-text-faint)]',
          'border-[var(--color-border)]',
          'disabled:cursor-not-allowed disabled:opacity-50',
          className
        )}
        {...props}
      />
    )
  }
)
Input.displayName = 'Input'
