import * as React from 'react'
import { cn } from '@/lib/utils'

export const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      'rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 sm:p-8',
      className
    )}
    {...props}
  />
))
Card.displayName = 'Card'

export const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h2
    ref={ref}
    className={cn(
      'text-2xl sm:text-3xl font-bold text-[var(--color-text)] mb-3',
      className
    )}
    {...props}
  />
))
CardTitle.displayName = 'CardTitle'

export const CardBody = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('text-lg text-[var(--color-text-muted)]', className)}
    {...props}
  />
))
CardBody.displayName = 'CardBody'
