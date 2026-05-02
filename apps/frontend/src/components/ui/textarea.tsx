import * as React from 'react'
import { cn } from '@/lib/utils'

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          'flex min-h-40 w-full rounded-[var(--radius)] border bg-[var(--color-surface)] px-4 py-3 text-lg leading-relaxed text-[var(--color-text)] placeholder:text-[var(--color-text-faint)]',
          'border-[var(--color-border)]',
          'disabled:cursor-not-allowed disabled:opacity-50',
          'resize-y',
          className
        )}
        {...props}
      />
    )
  }
)
Textarea.displayName = 'Textarea'
